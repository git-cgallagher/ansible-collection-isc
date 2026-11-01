# git_cgallagher.isc.kea_dhcp_msdns

Prepares **Active Directory / Microsoft DNS** for ISC Kea's GSS-TSIG dynamic DNS updates. It's the companion to [`kea_dhcp`](../kea_dhcp/README.md) with `kea_dhcp_dns_integration: ms-dns`. Run it against a domain controller. Like every role in this collection, it sets no connection parameters: your inventory decides how Ansible reaches the DC (WinRM, OpenSSH…).

It has two backends:
- **windows:** `microsoft.ad.user` for the account, `ansible.windows.win_dns_zone` for the zones, plus `ktpass`. This is the production target.
- **samba:** `samba-tool` and `ldb-tools` on a Samba AD DC. This is what CI tests.

`kea_dhcp_msdns_backend: auto` picks `windows` for Windows targets and `samba` otherwise.

## What it does

1. **Service account** (`kea` by default). It's created with a password that never expires; an existing account's password is left alone. On Windows, the account is found by sAMAccountName wherever it is, and moved into `kea_dhcp_msdns_service_account_ou` when that is set (the Molecule scenario pre-creates it in Users and checks the move).
2. **UPN set to Kea's client principal** (`DHCP/kea.<domain>@<REALM>`). AD only issues Kerberos tickets to a UPN, not to an SPN alone. Without this, Kea fails with *bad client credentials*. On Windows `ktpass -mapuser` does the same; on Samba the role sets it with `ldbmodify`.
3. **SPN** `DHCP/kea.<domain>` on the account.
4. **DnsUpdateProxy** membership (`kea_dhcp_msdns_dnsupdateproxy`), so Kea can replace records that clients registered themselves.
5. **Zones:** the forward and reverse zones are created if missing (AD-integrated). On Windows, their dynamic-update setting is made `Secure` and their replication scope `kea_dhcp_msdns_zone_replication` (default `Domain`). Both are desired state for existing zones too: a zone in another scope is converted, and a file-backed zone fails, since it can't be converted to AD-integrated.
6. **Keytab:**
   - It's produced on the DC (Windows: `ktpass`; Samba: `samba-tool domain exportkeytab`, checked with `kinit` when available).
   - It's fetched to the **controller** path `kea_dhcp_msdns_keytab_dest` with mode 0600, and the copy on the DC is deleted.
   - It's only produced when that file doesn't exist yet, or when `kea_dhcp_msdns_keytab_rotate: true`. On Windows a new keytab bumps the key version, which invalidates keytabs already deployed.

Hand the keytab to `kea_dhcp` through `kea_dhcp_dns.keytab_src`.

## Requirements

- **Windows DC:** the DnsServer PowerShell module (present on DCs with the DNS role), `ktpass.exe`, and a connection with rights to create users, edit SPNs and group membership, and manage zones. Needs the `ansible.windows` (>= 2.6.0) and `microsoft.ad` (>= 1.6.0) collections, both in the collection's `requirements.yml`; `microsoft.ad.user` talks LDAP and needs no ActiveDirectory PowerShell module.
- **Samba AD DC:** root on the DC, `samba-tool`, and `ldb-tools` (installed by the role). `kea_dhcp_msdns_samba_admin_password` is required for the DNS zone calls.
- **Keytab handling:** `kea_dhcp_msdns_keytab_dest` must be outside any repository. Encrypt the file with `ansible-vault encrypt` if you store it; `kea_dhcp` decrypts it on the way.
- **A settled DC:** for a minute or two after a DC's promotion, its domain zone reports the replication scope `Legacy`, and the zone task fails with *Failed to reset the directory partition*. Run the role once the scope reads `Domain` (`Get-DnsServerZone`).
- **Service account password:** it must satisfy the domain's password policy. With the default complexity rules, it also mustn't contain the account name (`kea`). If it does, AD rejects it, and `microsoft.ad.user` reports that error with the password left out.
- **Password exposure:** `samba-tool` and `ktpass` take the password on their command line. Those tasks are `no_log`, but the value is briefly visible in the DC's process list.

## Example

```yaml
- name: Prepare AD for Kea
  hosts: dc1                      # connection settings come from your inventory
  roles:
    - role: git_cgallagher.isc.kea_dhcp_msdns
      vars:
        kea_dhcp_msdns_domain: corp.example.com
        kea_dhcp_msdns_service_account_password: "{{ vault_kea_ad_password }}"
        kea_dhcp_msdns_reverse_zones: [0.0.10.in-addr.arpa]
        kea_dhcp_msdns_keytab_dest: "{{ playbook_dir }}/../secrets/kea.keytab"

- name: Kea with Microsoft DNS updates
  hosts: kea
  become: true
  roles:
    - role: git_cgallagher.isc.kea_dhcp
      vars:
        kea_dhcp_interfaces: [ens5]
        kea_dhcp_dns_integration: ms-dns
        kea_dhcp_dns:
          domain: corp.example.com
          servers: [{name: dc1, ip: 10.0.0.10}]
          reverse_zones: [0.0.10.in-addr.arpa]
          keytab_src: "{{ playbook_dir }}/../secrets/kea.keytab"
```

A complete inventory, with the DC's PSRP connection and a Stork agent next to each Kea, is in [`examples/kea_dhcp/msdns-stork`](../../examples/kea_dhcp/msdns-stork/).

All variables are in [`meta/argument_specs.yml`](meta/argument_specs.yml), and [`defaults/main.yml`](defaults/main.yml) has comments.

## Testing

`molecule test -s default` (from this role's directory in a checkout of the collection) runs the Samba backend against a fresh Samba AD DC, then deploys Kea with `ms-dns` on Amazon Linux 2023 x86-64. It verifies:
- the account's UPN, SPN and DnsUpdateProxy membership, and the reverse zone;
- `kinit` from the Kea host using the keytab and `krb5.conf` that `kea_dhcp` deployed;
- the DDNS daemon's GSS-TSIG key exchange with the DC.

A second run must change nothing.

`molecule test -s windows` runs the **Windows backend** against a real Windows Server 2022 domain controller. The DC runs Microsoft DNS and is booted under QEMU/KVM. Kea's A and PTR updates are read back out of Microsoft DNS. It needs Linux with KVM, so CI runs it only on demand: `gh workflow run windows-dc.yml`. See [its README](molecule/windows/README.md).

## License

MIT
