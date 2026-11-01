# git_cgallagher.isc.bind9

Installs **ISC BIND 9** as an authoritative DNS server from the distro's packages. In this collection its main job is to take Kea's dynamic DNS updates ([`kea_dhcp`](../kea_dhcp/README.md) with `kea_dhcp_dns_integration: rfc2136` or `bind9-gss-tsig`), but it serves any zones.

What it does:

1. Installs BIND, its checking tools, `dig` and `nsupdate`.
2. Generates an rndc key when there's none, and listens for rndc on 127.0.0.1.
3. Writes the TSIG keys (`tsig-keys.conf`, mode 0640) and, for GSS-TSIG, copies the DNS service keytab and sets `tkey-gssapi-keytab`.
4. **Seeds** each primary zone file (SOA, NS and any initial records) **only when it doesn't exist**. After that, BIND owns the file: dynamic updates and their journals change it, and the role never rewrites it. To change a zone's data, use `nsupdate` (or edit it with `rndc freeze`/`thaw`).
5. Writes `named.conf`: options, the rndc `controls`, statistics channels and every zone.
6. Checks everything before it's installed: `named-checkzone` for seeded zones, `named-checkconf` for `named.conf`, then `named-checkconf -z` for the whole server. BIND is reloaded only after those pass.

It never guesses the network: `bind9_listen_on` is required and there are no default zones. Recursion is off. Turning it on needs `bind9_allow_recursion`, so an open resolver can't happen by default.

## Requirements

- ansible-core 2.16+.
- Root on the target (`become`).
- **BIND 9.16 or later** (the distro's package). The role writes `type primary`/`secondary` and `primaries`, which BIND 9.11 (EL 8) rejects, so EL 8 isn't supported.
- One of the OS families below. Paths follow each distro's packaging, so AppArmor (Debian/Ubuntu) and SELinux (EL) allow BIND to write its zones and journals:

| OS family | Config | Writable zones | Secondary zones | User | Tested with |
|---|---|---|---|---|---|
| Debian, Ubuntu | `/etc/bind/named.conf` | `/var/lib/bind` | `/var/cache/bind` | `bind` | 9.18 (Debian 12, Ubuntu 24.04) |
| EL, Fedora, Amazon Linux 2023 | `/etc/named.conf` | `/var/named/dynamic` | `/var/named/slaves` | `named` | 9.16 (Rocky 9), 9.18 (AL2023) |
| Alpine | `/etc/bind/named.conf` | `/var/bind/dyn` | `/var/bind/sec` | `named` | 9.20 (Alpine 3.22) |

The role **replaces** the distro's `named.conf`, including Debian's `named.conf.options` / `named.conf.local` includes. Put anything extra in `bind9_options_extra` or `bind9_config_extra`.

## Role Variables

The full list, with types, is in [`meta/argument_specs.yml`](meta/argument_specs.yml); defaults are in [`defaults/main.yml`](defaults/main.yml).

| Variable | Default | Notes |
|---|---|---|
| `bind9_listen_on` | `[]` | **Required.** IPv4 addresses, or `[any]`. |
| `bind9_listen_on_v6` | `[]` | Empty renders `listen-on-v6 { none; }`. |
| `bind9_port` | `53` | |
| `bind9_allow_query` / `bind9_allow_transfer` | `[any]` / `[none]` | Address-match lists, as written (`key kea-key` works). |
| `bind9_recursion` / `bind9_allow_recursion` | `false` / `[]` | Recursion needs an allow list. |
| `bind9_forwarders` / `bind9_forward` | `[]` / `only` | Global forwarding. |
| `bind9_dnssec_validation` | `auto` | |
| `bind9_tsig_keys` | `[]` | `{name, secret, algorithm}`; algorithm defaults to `hmac-sha256`. Vault the secrets; make one with `tsig-keygen -a hmac-sha256 kea-key`. |
| `bind9_gss_tsig_keytab_src` | `""` | Controller path to the `DNS/<fqdn>@<REALM>` keytab. Vault-encrypted files are decrypted on the way. |
| `bind9_zones` | `[]` | See below. |
| `bind9_zone_default_ttl` | `300` | TTL for seeded zone files. |
| `bind9_rndc_enabled` / `bind9_rndc_port` | `true` / `953` | rndc key generated at the distro's default path, so plain `rndc` works. |
| `bind9_statistics_channels` | `[]` | `{address, port (8053), allow}`. Stork's agent reads these. |
| `bind9_options_extra` / `bind9_config_extra` | `""` | Raw text inside `options { }` / at the end of `named.conf`. |
| `bind9_manage_service` | `true` | Enable and start `named`, and reload it on changes. |
| `bind9_validate_config` | `true` | The checks in step 6. |
| `bind9_bootstrap_python` | `false` | Install python3 with `raw` first (minimal images). |
| `bind9_packages_extra` / `bind9_package_state` | `[]` / `present` | |

Each `bind9_zones` item:

| Key | Types | Notes |
|---|---|---|
| `name` | all | **Required.** |
| `type` | — | `primary` (default), `secondary` or `forward`. |
| `file` | primary, secondary | Default `<writable zones>/<name>.db` or `<secondary zones>/<name>.db`. |
| `update_policy` | primary | Rules as written, e.g. `grant kea-key zonesub ANY`. |
| `allow_update` | primary | Address-match list, instead of `update_policy`. |
| `ns` | primary | **Required.** NS names for the seed file; the first is the SOA MNAME. |
| `soa_email`, `ttl`, `records` | primary | Seed file only. `records` are written as given (`ns1 IN A 192.0.2.53`). |
| `primaries` | secondary | **Required.** |
| `forwarders`, `forward` | forward | `forwarders` **required**; `forward` defaults to `only`. |
| `options` | all | Extra zone statements, as written. |

## Dependencies

None.

## Example Playbook

A BIND server for Kea's TSIG updates, next to `kea_dhcp` with `rfc2136`:

```yaml
- name: DNS for Kea
  hosts: ns1
  become: true
  roles:
    - role: git_cgallagher.isc.bind9
      vars:
        bind9_listen_on: [192.0.2.53]
        bind9_allow_transfer: [none]
        bind9_tsig_keys:
          - name: kea-key
            secret: "{{ vault_kea_tsig_secret }}"   # the same secret as kea_dhcp_dns.tsig_key
        bind9_zones:
          - name: corp.example.com
            ns: [ns1.corp.example.com.]
            records: ["ns1 IN A 192.0.2.53"]
            update_policy: ["grant kea-key zonesub ANY"]
          - name: 2.0.192.in-addr.arpa
            ns: [ns1.corp.example.com.]
            update_policy: ["grant kea-key zonesub PTR"]
```

For GSS-TSIG (`kea_dhcp_dns_integration: bind9-gss-tsig`), give BIND its service keytab and grant Kea's principal instead:

```yaml
bind9_gss_tsig_keytab_src: files/ns1.keytab   # DNS/ns1.corp.example.com@CORP.EXAMPLE.COM, vault-encrypted
bind9_zones:
  - name: corp.example.com
    ns: [ns1.corp.example.com.]
    update_policy: ['grant "DHCP/kea.corp.example.com@CORP.EXAMPLE.COM" zonesub ANY']
```

## Testing

`roles/bind9/molecule/default` runs on Amazon Linux 2023, Rocky 9, Debian 12, Ubuntu 24.04 and Alpine 3.22. The containers have no init system, so the role runs with `bind9_manage_service: false` and the verify step starts `named` itself. It checks that the zones answer, that a TSIG-signed update lands, that an unsigned one is refused, and that rndc and the statistics channel respond. Starting `named` through systemd or OpenRC isn't tested in CI; the verify step only checks the unit or init script exists.

```bash
cd roles/bind9 && molecule test -s default --platform-name bind9-al2023
```

## License

MIT

## Author Information

Chris Gallagher ([@git-cgallagher](https://github.com/git-cgallagher)).
