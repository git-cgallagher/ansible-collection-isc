# kea_dhcp_msdns_windows: Kea against a real Windows domain controller

Molecule boots a Windows Server 2022 VM under QEMU/KVM and promotes it to the first DC of a new forest (`kealab.test`) with AD-integrated **Microsoft DNS**. Then:
- `kea_dhcp_msdns` prepares AD with its **Windows backend**: the service account, UPN, SPN, DnsUpdateProxy, reverse zone, and the `ktpass` keytab.
- `kea_dhcp` deploys Kea with `kea_dhcp_dns_integration: ms-dns` in an Amazon Linux 2023 x86-64 container.

CI runs it **on demand only**, in [`.github/workflows/windows-dc.yml`](../../../.github/workflows/windows-dc.yml); it takes about 15 minutes. It isn't a required check. It last passed on 2026-10-28 (PR #12). Re-run it after changing `kea_dhcp_msdns`, the `ms-dns` preset or the DDNS templates.

The VM boot (`create.yml`, `destroy.yml`) comes from `git_cgallagher.gpo`'s `domain_lab` scenario: the same pinned [`jborean93/WindowsServer2022`](https://portal.cloud.hashicorp.com/vagrant/discover/jborean93/WindowsServer2022) 1.2.0 evaluation box, the same first-boot wait, and the same PSRP/NTLM connection as `vagrant`.

## What it proves

| Step | Asserted |
|---|---|
| prepare | The VM is renamed `dc01`, promoted with DNS, and its clock is set from the controller (Kerberos allows 5 minutes of skew). |
| converge | Both roles apply. |
| idempotence | A second run changes nothing. In particular, the keytab isn't regenerated, because `ktpass` would bump the key version. |
| verify, DC | The account's UPN equals Kea's client principal, the SPN and DnsUpdateProxy membership are set, and both zones are `Secure`. |
| verify, Kea | `kinit` works with the deployed keytab and `krb5.conf`. |
| verify, DNS | `lease4-add` plus `lease4-resend-ddns` produce GSS-TSIG signed updates. The **A and PTR records are read back from Microsoft DNS** with `Get-DnsServerResourceRecord`. A second address for the same client moves the A record. No `GSS_TSIG_VERIFY_FAILED` appears in the log. |

## Networking

QEMU's user-mode network forwards ports on the runner's `127.0.0.1` to the DC:

| Runner port | DC port | Used by |
|---|---|---|
| 5985 | 5985 | Ansible (WinRM/PSRP) |
| 15353 | 53 (TCP and UDP) | DNS |
| 18088 | 88 (TCP and UDP) | Kerberos |

The Kea container uses `--network host`, so its config points at `127.0.0.1:15353` (`kea_dhcp_dns.servers[].port`) and `127.0.0.1:18088` (`kea_dhcp_dns.kdcs`). The server principal stays `DNS/dc01.kealab.test@KEALAB.TEST`.

## Running it

You need Linux x86-64 with `/dev/kvm`, `qemu-system-x86_64` and `qemu-img`, Docker, about 20 GB free in `$KEA_LAB_DIR` (default `~/.cache/kea-domain-lab`), and ports 5985, 15353 and 18088 free on `127.0.0.1`. **It can't run on macOS or Apple Silicon.**

```bash
pip install ansible-core molecule pypsrp
ansible-galaxy collection install -r extensions/molecule/kea_dhcp_msdns_windows/requirements.yml
mkdir -p .molecule-collections/ansible_collections/git_cgallagher
ln -sfn ../../.. .molecule-collections/ansible_collections/git_cgallagher/isc
KEA_LAB_DIR=/path/with/space molecule test -s kea_dhcp_msdns_windows
```

To run it in CI: `gh workflow run windows-dc.yml --repo git-cgallagher/ansible-collection-isc --ref <branch>`.

## What it found (2026-10-28)

The first runs against a real DC turned up three problems that the Samba stand-in couldn't show. All three are fixed in 1.6.1:
- Microsoft DNS's error responses fail Kea's GSS-TSIG verification. The `ms-dns` preset therefore uses `no-check-with-dhcid`.
- The Windows tasks weren't idempotent: `win_powershell` defaults to `changed`.
- `no_log` hid why the service-account task failed. The cause was domain password complexity, which rejects a password containing the account name.

The passwords in `molecule.yml` are throwaway `Example-not-secret-*` values for a VM that's reachable only on the runner's loopback. The keytab is written to Molecule's ephemeral directory, never into the checkout.
