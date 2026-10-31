# git_cgallagher.isc.kea_dhcp

Part of the [`git_cgallagher.isc`](../../README.md) collection. This role
was previously the standalone Galaxy role `git-cgallagher.kea_dhcp`; see
[Migrating from the standalone role](#migrating-from-the-standalone-role).

Installs and configures [ISC Kea](https://www.isc.org/kea/) DHCPv4, DHCPv6 and DDNS, in one of three ways:

- **Packages**: installs Kea on **Amazon Linux 2023** (the primary, most-tested platform, minimal image included), the RHEL family/Fedora, Debian/Ubuntu or Alpine (OpenRC), from ISC's repositories, your own mirrors, or the distro's packages.
- **Containers on a host**: runs ISC's Kea images under systemd with Podman or Docker, on any systemd host.
- **Kubernetes**: applies Kea to Talos, EKS or any conformant cluster from the controller, or only renders the manifests for GitOps.

Both paths build the Kea configuration the same way. The role computes the parts that depend on the deployment (control sockets, hooks, HA peers, database hook libraries, loggers). It then deep-merges your own Kea settings on top, so **any Kea key can be set without a role change**.

| | |
|---|---|
| Kea series | **3.0** (LTS, default) · **3.2** (current stable) · **2.6** (EOL, existing estates only) |
| Clustering | HA `hot-standby` · `load-balancing` · `passive-backup` · **hub-and-spoke** (multiple relationships) · backup peers · shared MySQL/PostgreSQL lease DB · configuration backend (`server-tag`) |
| Kubernetes | `ha_peers` (one pinned Deployment per peer) · `shared_db` (N replicas / DaemonSet) × `host` network (broadcast) or `service` network (relayed, behind a LoadBalancer) |

## Requirements

- ansible-core ≥ 2.16
- Collections (installed with this one; see [Installation](#installation)):
  - `community.general`: for `apk` on Alpine.
  - `kubernetes.core`: for Kubernetes mode, plus the `kubernetes` Python package on the controller.
- Package mode needs Python on the target. On minimal images, set `kea_dhcp_bootstrap_python: true` and `gather_facts: false`. RHEL-family hosts need `dnf`; `-minimal` images ship only `microdnf`, and the bootstrap installs `dnf` for you.
- EL hosts (RHEL, Rocky, Alma and similar) need **EPEL**, because Kea's RPMs, ISC's and the distro's alike, depend on `log4cplus`. The role installs `epel-release` (or the release RPM on RHEL). Turn this off with `kea_dhcp_epel_manage: false` if you mirror EPEL yourself.
- **Amazon Linux 2023** has no Kea packages of its own, and ISC's `amzn/2023` repositories are empty. The role therefore installs **ISC's EL9 RPMs**, which run there, and takes `log4cplus` from a repo file for EPEL 9 restricted to that one package (`includepkgs=log4cplus*`). Neither ISC nor Amazon supports this combination; it's the role's most-tested path (see [Supported platforms](#supported-platforms)), on x86-64. ISC's EL9 builds also exist for arm64 (Graviton); a hand run of the 3-node scenario passed there, but CI doesn't cover it.

### Supported platforms

| Deployment | Platforms |
|---|---|
| Packages | **Amazon Linux 2023**, including minimal (primary) · RHEL/Rocky/Alma 8–10 · Fedora · Debian 12/13 · Ubuntu 22.04/24.04 (systemd) · Alpine 3.20+ (OpenRC) |
| Kubernetes | Talos · Amazon EKS · any conformant cluster (k3s, kubeadm, RKE2…) on **amd64** nodes (ISC images are amd64-only) |

**Amazon Linux 2023 is tested most:** CI installs packages on AL2023 standard and minimal, and runs the 3-node HA scenario (including a real failover) and the container-mode scenario on AL2023 nodes. Those AL2023 jobs are required to pass before anything merges. All of it runs on **x86-64**, the expected deployment architecture. CI also tests package installs on Debian 12, Ubuntu 24.04, Rocky 9 and Alpine 3.20/3.22. The other listed versions use the same package names and repositories but aren't tested.

## Installation

This role ships in the `git_cgallagher.isc` collection:

```bash
ansible-galaxy collection install git_cgallagher.isc community.general kubernetes.core
```

Or in a `requirements.yml`:

```yaml
collections:
  - name: git_cgallagher.isc
  - name: community.general
  - name: kubernetes.core   # Kubernetes deployments only
```

### Migrating from the standalone role

The standalone role `git-cgallagher.kea_dhcp` is retired. Variables and
behaviour are unchanged; only the name moves:

```yaml
# before
- role: git-cgallagher.kea_dhcp
# after
- role: git_cgallagher.isc.kea_dhcp
```

## Role Variables

Every variable is listed with its type, choices and a description in [`meta/argument_specs.yml`](meta/argument_specs.yml), which Ansible enforces when the role starts. Defaults, with comments, are in [`defaults/main.yml`](defaults/main.yml). To read the spec from the command line:

```bash
ansible-doc -t role git_cgallagher.isc.kea_dhcp
```

All variables are prefixed `kea_dhcp_`. The ones you will touch most:

| Variable | Default | Purpose |
|---|---|---|
| `kea_dhcp_deployment` | `package` | `package` or `kubernetes` |
| `kea_dhcp_version_series` | `"3.0"` | Repo, config dialect, image tag |
| `kea_dhcp_dhcp4_enabled` / `_dhcp6_` / `_ddns_` | `true` / `false` / `false` | Daemons to run |
| `kea_dhcp_interfaces` | `[]` (required) | NICs to serve; `["*"]` = all |
| `kea_dhcp_dhcp4_settings` / `_dhcp6_` / `_ddns_` | `{}` | Kea keys merged last |
| `kea_dhcp_lease_database` | memfile | Kea `lease-database` object |
| `kea_dhcp_ha_enabled`, `_ha_peers`, `_ha_relationships`, `_ha_defaults` | | HA |
| `kea_dhcp_api_http_enabled`, `_api_tls`, `_api_auth_clients` | off | HTTP(S) API + basic auth |
| `kea_dhcp_files` | `[]` | TLS certs/keys, password files (host or pod) |
| `kea_dhcp_package_source` | `isc` | `isc` · `distro` · `none` |
| `kea_dhcp_k8s_platform` / `_topology` / `_network_mode` | `generic` / `ha_peers` / by platform | Kubernetes shape |

## Dependencies

No role dependencies. Collections are listed under [Requirements](#requirements).

## Example Playbook

On Amazon Linux 2023 (minimal or standard):

```yaml
- hosts: dhcp
  become: true
  gather_facts: false   # AL2023 minimal has no Python yet; the role installs it first
  roles:
    - role: git_cgallagher.isc.kea_dhcp
      vars:
        kea_dhcp_bootstrap_python: true
        kea_dhcp_interfaces: [ens5]   # AL2023's NIC name on EC2 Nitro; check `ip -br link` on your VMs
        kea_dhcp_dhcp4_settings:
          subnet4:
            - id: 1
              subnet: 192.0.2.0/24
              pools: [{pool: 192.0.2.100 - 192.0.2.200}]
              option-data: [{name: routers, data: 192.0.2.1}]
```

The role makes no default assumptions about the network. It **fails** if no interface is set and adds no subnets of its own. Ready-to-adapt inventories are in the collection's
[`examples/kea_dhcp/`](../../examples/kea_dhcp/):

- [`vm-ha3`](../../examples/kea_dhcp/vm-ha3/): three Amazon Linux 2023 VMs, primary + standby + backup.
- [`package-ha`](../../examples/kea_dhcp/package-ha/): HA pair of Amazon Linux 2023 VMs (any supported OS works).
- [`talos-ha`](../../examples/kea_dhcp/talos-ha/): HA pair on Talos with host networking.
- [`eks-relay`](../../examples/kea_dhcp/eks-relay/): relayed DHCP on EKS with an RDS lease database.

## How the configuration is built

For each daemon (`dhcp4`, `dhcp6`, `ddns`, and `ctrl_agent` on 2.6), the role builds the config in this order:

1. **Computed**: `interfaces-config`, `lease-database`, `hosts-databases`, `config-control`/`server-tag`, the control socket(s), `dhcp-ddns`, and `loggers`.
2. **Your settings**: `kea_dhcp_dhcp4_settings`, `kea_dhcp_dhcp6_settings`, `kea_dhcp_ddns_settings` and `kea_dhcp_ctrl_agent_settings` are deep-merged on top, so they win.
3. **Hooks**: the libraries the role needs come first:
   - `libdhcp_mysql.so` / `libdhcp_pgsql.so` on 3.x whenever an SQL backend is used.
   - `libdhcp_mysql_cb.so` / `libdhcp_pgsql_cb.so` for the config backend on 2.6.
   - `libdhcp_lease_cmds.so` and `libdhcp_ha.so` for HA.

   Then `kea_dhcp_<family>_hooks_libraries` and any `hooks-libraries` from your settings. Give bare library names. On 3.x they stay bare, because Kea refuses paths outside its hooks directory. On 2.6 the role prefixes the hooks directory, which it reads from `kea-dhcp4 -W`.

Each config file is validated with `kea-<daemon> -t` before it is installed (`kea_dhcp_validate_config`).

### Version dialects handled for you

| | 3.x | 2.6 |
|---|---|---|
| HTTP API | per-daemon `control-sockets` (http/https, basic auth, TLS) | `kea-ctrl-agent` (auto-enabled when needed) |
| Unix sockets | bare `socket-name` | absolute path in `/var/run/kea` |
| Hook libraries | bare file name | absolute path |
| SQL lease/host backends | `libdhcp_mysql.so` / `libdhcp_pgsql.so` loaded automatically | built in |

## High availability

The simple form describes one relationship:

```yaml
kea_dhcp_ha_enabled: true
kea_dhcp_ha_mode: hot-standby        # load-balancing | passive-backup
kea_dhcp_ha_peers:
  - {name: kea1, role: primary}
  - {name: kea2, role: standby, auto-failover: true}
  - {name: kea3, role: backup}
```

Hub-and-spoke uses several relationships. Each host renders only the relationships it belongs to:

```yaml
kea_dhcp_ha_relationships:
  - mode: hot-standby
    peers: [{name: branch1, role: primary}, {name: hub, role: standby}]
  - mode: hot-standby
    peers: [{name: branch2, role: primary}, {name: hub, role: standby}]
```

How the HA config is assembled:

- **Peer keys**: a peer item takes any Kea peer key (`url`, `auto-failover`, `basic-auth-user`, `basic-auth-password-file`, `trust-anchor`, …) plus three role-only helpers:
  - `host`: the inventory host to take the address from.
  - `address` / `port`: used to build the `url`.
- **Generated URL**: without a `url`, the role builds `http(s)://<address>:<port>/`. The address comes from that peer's `kea_dhcp_ha_address` (default: `ansible_host`). Kea needs an **IP address** in peer URLs, not a DNS name.
- **Shared settings**: `kea_dhcp_ha_defaults` is merged into every relationship. Use it for heartbeat timers, `delayed-updates-limit`, TLS (`trust-anchor`/`cert-file`/`key-file`/`require-client-certs`), `restrict-commands`, and so on.
- **Partial runs**: each peer needs to know its partners' IPs. With `--limit`, a peer outside the play resolves from its inventory (`kea_dhcp_ha_address`, `ansible_host`, or `kea_dhcp_k8s_ha_cluster_ip`). If none of those is an IP, the role **fails** rather than render a URL Kea can't use.
- **Listener**: the default is multi-threaded HA with a **dedicated listener**, on port 8001 for v4 and 8011 for v6. If you disable it, HA traffic goes through the daemon's own HTTP API (3.x) or the control agent (2.6), and the role enables whichever is needed. It also:
  - turns off the server's own `multi-threading`, because Kea's HA stays in `WAITING` when the two disagree;
  - when API auth is on, gives every peer `basic-auth-user` / `basic-auth-password-file` (as `kea_dhcp_ha_api_auth_user`), because peers otherwise get `Unauthorized`.

### Other clustering patterns

- **Shared lease database**: give several servers the same `kea_dhcp_lease_database` (`mysql`/`postgresql`) and no HA hook. Every server can answer any client. `kea_dhcp_db_schema_manage: true` runs `kea-admin db-init` once (and `db-upgrade` with `kea_dhcp_db_schema_upgrade`).
- **Configuration backend**: use `kea_dhcp_config_backend` (`enabled`, `server_tag`, `config_databases`) so subnets live in SQL and each server pulls its own `server-tag`. `libdhcp_cb_cmds.so` remains an ISC subscriber hook. Add it with `kea_dhcp_dhcp4_hooks_libraries` if you have it.

## DNS integration (dynamic DNS)

`kea_dhcp_dns_integration` picks the DNS service Kea updates. The role loads a preset for it (`vars/dns/<integration>.yml`): the DHCP-side DDNS policy, the signing method, and provider-specific defaults. It then merges your `kea_dhcp_dns` over the preset, so anything you set wins. Choosing anything but `none` enables `kea-dhcp-ddns`.

| `kea_dhcp_dns_integration` | DNS service | Updates signed with | Tested |
|---|---|---|---|
| `none` (default) | — | — | — |
| `ms-dns` | Microsoft DNS on Active Directory DCs | GSS-TSIG (Kerberos) | Kerberos and GSS-TSIG key exchange against a Samba AD DC; signed updates against BIND (see below) |
| `bind9-gss-tsig` | BIND 9, FreeIPA / IdM | GSS-TSIG (Kerberos) | End to end against an MIT KDC + BIND 9 |
| `rfc2136` | BIND 9, PowerDNS, Knot… | TSIG shared key | End to end against BIND 9 |

Settings shared by every provider:

```yaml
kea_dhcp_dns_integration: ms-dns
kea_dhcp_dns:
  domain: corp.example.com                   # forward zone corp.example.com. by default
  servers:                                   # name = the DNS host's short name
    - {name: dc1, ip: 10.0.0.10}
    - {name: dc2, ip: 10.0.0.11}
  reverse_zones: [0.0.10.in-addr.arpa]       # must already exist on the DNS server
  keytab_src: "{{ playbook_dir }}/secrets/kea.keytab"   # GSS-TSIG; vault-encrypt it
  dhcp_ddns_params: {}                       # override the preset's DHCP DDNS policy
```

Optional keys: `forward_zones`, `realm` (default: the domain upper-cased), `client_principal` (default `DHCP/kea.<domain>@<REALM>`), `kdcs` (default: the servers' IPs), `keytab_path`, `krb5_conf_path`, `gss` (GSS-TSIG hook parameter overrides), `install_krb5_tools` (adds `kinit`/`klist`), and `tsig_key` for `rfc2136`. `kea_dhcp_ddns_settings` is still merged last, for anything not covered here.

### What the role sets up

- **DDNS daemon zones:** the forward and reverse zones point at every server in `servers`, with the TSIG key name added for `rfc2136`.
- **DHCP-side policy:** `ddns-send-updates`, `ddns-override-client-update`, `ddns-replace-client-name`, `ddns-conflict-resolution-mode`, and `ddns-qualifying-suffix` (the domain). `kea_dhcp_dhcp4_settings` / `kea_dhcp_dhcp6_settings` still override them.
- **GSS-TSIG (`ms-dns`, `bind9-gss-tsig`):**
  - **Hook:** ISC's `libddns_gss_tsig.so`, with one server entry per DNS server. Each entry's server principal is `DNS/<name>.<domain>@<REALM>`.
  - **Package:** `isc-kea-gss-tsig`.
  - **Files:** the keytab (copied from `keytab_src`, binary-safe; a vault-encrypted file is decrypted on the way) and a Kea-only `krb5.conf` in `/etc/kea`.
  - **Environment:** `kea-dhcp-ddns` gets `KRB5_CONFIG` through a systemd drop-in (package mode), `-e` (container mode) or the pod spec (Kubernetes, where the keytab goes into the Secret's binary `data`). The host's own `/etc/krb5.conf`, for example an SSSD domain join, is never touched. If you run Kea's services yourself (`kea_dhcp_manage_service: false`), start `kea-dhcp-ddns` with `KRB5_CONFIG=/etc/kea/krb5.conf`.

### Requirements by provider

**`none`:** nothing. Kea hands out addresses and hostnames and never touches DNS.

**`ms-dns` (Microsoft DNS / Active Directory):**
- **Kea version and packages:** Kea 3.0 or newer from ISC's packages. ISC publishes no GSS-TSIG hook for 2.6, and distro packages don't ship it.
- **AD service account with a keytab:**
  - The account's **UPN must equal Kea's client principal** (`DHCP/kea.<domain>@<REALM>`). AD only issues tickets to a UPN, not to an SPN alone, and Windows' `ktpass -mapuser` sets it that way.
  - It needs the SPN `DHCP/kea.<domain>`.
  - [`kea_dhcp_msdns`](../kea_dhcp_msdns/README.md) does all of this, plus the keytab.
- **Update rights:** membership in **DnsUpdateProxy**, or an explicit zone ACL. Without it, updates to records clients registered themselves are refused.
- **Zones:** forward and reverse zones exist in AD, set to *Secure only* dynamic updates. Updating a reverse zone that doesn't exist fails with a misleading "Packet was replayed in wrong direction".
- **`servers[].name`** is each DC's real host name. The DNS service principal is `DNS/<dc>.<domain>@<REALM>`.
- **Time sync:** Kerberos tolerates 5 minutes of skew, so point Kea hosts and DCs at the same NTP source.
- **Windows clients register their own A records.** The preset sets `ddns-override-client-update: true` so Kea owns them.
- **No update prerequisites.** The preset sets `ddns-conflict-resolution-mode: no-check-with-dhcid`. Kea can't verify the GSS-TSIG signature on Microsoft DNS's error responses (`GSS_TSIG_VERIFY_FAILED … Packet was replayed in wrong direction`). Every `check-*` mode sends prerequisites, so it fails as soon as a name already exists. Kea still writes DHCID records. Self-registered Windows records carry none, so `check-with-dhcid` would refuse to replace them anyway.
- **Preset flags:** `gss-replay-flag: false` (ISC reports anti-replay problems with Microsoft DNS) and `tkey-protocol: TCP`.
- **What the tests cover:** Kerberos and the GSS-TSIG key exchange are verified against a Samba AD DC, and signed record updates are verified against BIND. Microsoft DNS Server's own signature check hasn't been exercised by this role's tests; ISC documents it as supported. Samba's built-in DNS server isn't a usable stand-in: it rejects Kea's signed updates, and even BIND's `nsupdate -g` can't verify its responses.

**`bind9-gss-tsig` (BIND 9, FreeIPA / IdM):**
- Kea 3.0 or newer from ISC's packages.
- A Kerberos principal for Kea (default `DHCP/kea.<domain>@<REALM>`) and its keytab.
- On the DNS server:
  - BIND has `tkey-gssapi-keytab` pointing at the keytab for `DNS/<ns>.<domain>@<REALM>`.
  - Each zone has an `update-policy` that grants Kea's principal, for example `grant "DHCP/kea.example.com@EXAMPLE.COM" wildcard * ANY;`. Quote the principal; BIND rejects an unquoted `/`.
  - FreeIPA: add Kea's principal to the zone's update policy (`ipa dnszone-mod --update-policy`).
- The preset keeps ISC's GSS defaults (`gss-replay-flag: true`).

**`rfc2136` (TSIG):**
- **Key:** a shared key, `kea_dhcp_dns.tsig_key: {name, secret, algorithm}` (default algorithm `HMAC-SHA256`). Keep the secret in Ansible Vault.
- **DNS server:** the server knows the same key and allows it to update each zone. For example, BIND: `update-policy { grant kea-key wildcard * ANY; };`.
- Works with any Kea version and package source.

## Containers on a host

`kea_dhcp_deployment: container` runs ISC's Kea images on the inventory host with Podman or Docker, one systemd unit per daemon (`kea-dhcp4-container`, `kea-dhcp6-container`, `kea-dhcp-ddns-container`, and `kea-ctrl-agent-container` on 2.6). Use it on any systemd host where packages aren't an option, or to keep Kea's version independent of the OS.

- **Runtime:** `kea_dhcp_container_runtime: auto` picks Podman if it's installed, otherwise Docker. The role doesn't install a runtime. On Amazon Linux 2023 (the tested host), run `dnf install docker && systemctl enable --now docker` first.
- **Networking:** containers use `--network host`, so raw DHCP sockets, relays and HA listeners behave as with packages. Set `kea_dhcp_interfaces` to the host's NICs.
- **Configs:** rendered on the host into `kea_dhcp_config_dir` and validated with `kea-<daemon> -t` **inside the image** before they're installed. They're bind-mounted read-only at the same paths, together with any directory holding `kea_dhcp_files` or API credentials, so every path in the config still holds.
- **State:** leases live in `kea_dhcp_data_dir` on the host (mounted as `/var/lib/kea`). On 2.6, `kea_dhcp_container_run_dir` is shared as `/var/run/kea` between Kea and the control agent. `KEA_PIDFILE_DIR=/tmp` keeps stale PID files from blocking restarts.
- **Images:** the same variables as Kubernetes mode: `kea_dhcp_k8s_images`, `kea_dhcp_k8s_image_tag` and `kea_dhcp_k8s_capabilities` (all others dropped). Images are pulled on every run, and units restart only when an image ID, config or unit actually changes.
- **Architecture:** ISC's images are **linux/amd64 only**. On arm64 hosts, build your own images, or set `kea_dhcp_container_platform: linux/amd64` with emulation installed. For Graviton, package mode (EL9 RPMs on Amazon Linux 2023) runs natively instead.
- **SELinux** (Podman on EL): set `kea_dhcp_container_volume_options: ",z"` so the bind mounts are relabelled.

## Kubernetes

Inventory hosts are **logical Kea instances**, set to `ansible_connection: local`. Every API call runs on the controller through `kubernetes.core`, with the cluster chosen by `kea_dhcp_k8s_kubeconfig` / `kea_dhcp_k8s_context`. Each instance gets these objects:

- a Secret with its configs, files and API passwords;
- a Deployment or DaemonSet;
- optionally a PVC;
- in service mode, a UDP Service for DHCP and a per-peer ClusterIP Service for HA.

A config checksum annotation rolls the pod whenever the configuration changes.

| `kea_dhcp_k8s_platform` | Default network mode | Default storage | Notes |
|---|---|---|---|
| `talos` | `host` | `hostPath` (`/var/lib/kea-dhcp/<instance>`) | Talos enforces PSA `baseline`. The role labels the namespace `privileged` because hostNetwork/hostPath need it. NIC names come from `talosctl get links`. |
| `eks` | `service` | `pvc` (default StorageClass) | **Relayed DHCP only**: a VPC never delivers DHCP broadcasts to pods. Kea switches to `dhcp-socket-type: udp` and `interfaces: ["*"]`. See below. |
| `generic` | `host` | `hostPath` | Anything else (k3s, kubeadm, RKE2…). |

**Topologies**

- `ha_peers` (default): one Deployment per inventory host, with `replicas: 1` and the `Recreate` strategy.
  - Host mode: pinned to `kea_dhcp_k8s_node_name`. The peer address is the node's InternalIP, looked up automatically.
  - Service mode: this peer binds `0.0.0.0` and its partner dials a per-peer ClusterIP Service. The ClusterIP is read back after the Service is created, or set it with `kea_dhcp_k8s_ha_cluster_ip` for GitOps renders.
- `shared_db`: identical replicas against one SQL lease database, with no HA hook. Host mode makes a DaemonSet on the selected nodes. Service mode makes a Deployment with `kea_dhcp_k8s_replicas` replicas and soft anti-affinity.

**Removal:** `kea_dhcp_k8s_state: absent` deletes an instance's Deployment or DaemonSet, Services and Secret. It keeps the lease PVC unless you set `kea_dhcp_k8s_absent_delete_pvc: true`.

**Stork sidecar:** to monitor these pods with
[`git_cgallagher.isc.stork_agent`](../stork_agent/README.md), set
`kea_dhcp_k8s_share_process_namespace: true` and pass the agent role's
`stork_agent_k8s_containers` and `stork_agent_k8s_volumes` to
`kea_dhcp_k8s_extra_containers` and `kea_dhcp_k8s_extra_volumes`. The sidecar
needs Pod Security `privileged`. Two things help it:

- `kea_dhcp_k8s_extra_containers_mount_config` (on by default when the
  process namespace is shared) gives every extra container Kea's config, API
  credential and `kea_dhcp_files` mounts, at the same paths. The agent opens
  all of them.
- In service network mode with HA, each peer's `<instance>-ha` Service also
  carries the extra containers' TCP ports. That gives a sidecar a stable
  address, which a pod IP is not.

See [docs/stork-kubernetes.md](../../docs/stork-kubernetes.md).

**GitOps:** set `kea_dhcp_k8s_apply: false` and `kea_dhcp_k8s_manifest_dir: ./rendered`. The role then writes one multi-document YAML file per instance. The Secret is in clear text, so encrypt it (SOPS or Sealed Secrets) before committing.

### EKS specifics

- **Where requests come from**: point relays (`ip helper-address`) at an **internal NLB** over Direct Connect or VPN.
  - With the AWS Load Balancer Controller, use `aws-load-balancer-type: external` and `nlb-target-type: ip`, and set `preserve_client_ip.enabled=true` so Kea sees the relay address.
  - Kea replies from the pod IP straight to the relay. Check that your relay accepts that address and that security groups allow UDP 67 both ways.
- **Health checks**: an NLB can't health-check UDP. Enable `kea_dhcp_api_http_enabled` on `0.0.0.0` and point `aws-load-balancer-healthcheck-port` at TCP 8000 (see [`examples/kea_dhcp/eks-relay`](../../examples/kea_dhcp/eks-relay/)).
- **Image architecture**: ISC images are **linux/amd64 only**, so the default `kea_dhcp_k8s_node_selector` keeps Kea off Graviton (and arm Talos) nodes. For arm64 nodes, build your own image and set `kea_dhcp_k8s_images`.
- **Database and credentials**: RDS PostgreSQL/MySQL fits `shared_db`. Use `kea_dhcp_k8s_service_account_annotations` for IRSA, and `kea_dhcp_k8s_extra_volumes` for External Secrets/CSI mounts.

## Repositories

- **ISC (default)**: the role adds `https://dl.cloudsmith.io/public/isc/kea-<series>` with its signing key.
  - On Alpine, apk only trusts a key whose **file name** matches the signer, so key IDs per series are kept in `kea_dhcp_isc_repo_alpine_key_ids`.
  - Set `kea_dhcp_isc_repo_token` for ISC subscriber (`-prv`) repos.
- **Your own mirrors**: list them in `kea_dhcp_extra_repositories`:

  ```yaml
  kea_dhcp_extra_repositories:
    - {type: apt, name: internal-kea, repo: "deb [signed-by=/usr/share/keyrings/internal.asc] https://mirror/kea bookworm main",
       key_url: https://mirror/key.asc, key_path: /usr/share/keyrings/internal.asc}
    - {type: yum, name: internal-kea, baseurl: https://mirror/kea/el/9/$basearch, gpgkey: https://mirror/key.asc}
    - {type: apk, url: https://mirror/kea/alpine/v3.20/main, key_url: https://mirror/key.rsa.pub, key_name: mirror@example.rsa.pub}
  ```

- **Disable ISC**: set `kea_dhcp_isc_repo_manage: false`. To skip package management entirely, use `kea_dhcp_package_source: none`.

## Testing

The collection's CI runs lint, the render checks and Molecule (one job per distro) on every push, on every pull request, and weekly. A green merge to `main` releases the collection to Galaxy. To run the same checks locally from the collection root, you need the following installed:

- **`tests/kea_dhcp/run.sh`**: `ansible-core`, `kubernetes.core`, PyYAML, `openssl` and Docker. On Apple silicon, Docker also needs amd64 emulation.
- **Molecule**: `molecule`, `molecule-plugins[docker]`, the `docker` Python SDK and the `community.docker` collection.

```bash
tests/kea_dhcp/run.sh
```

`tests/kea_dhcp/run.sh` renders 8 deployment shapes (14 instances) without a cluster and runs every generated config through `kea-<daemon> -t` in the ISC 2.6.5, 3.0.4 and 3.2.1 images. The `-t` check loads hook libraries, so it catches wrong HA keys or library paths.

```bash
cd roles/kea_dhcp    # in a checkout of the collection
molecule test -s default
```

`molecule test -s default` installs from packages on Debian 12, Ubuntu 24.04, Rocky 9, Amazon Linux 2023 (standard and minimal), Alpine 3.20 (ISC) and Alpine 3.22 (distro) in containers. It then checks idempotence and re-validates the configs on each host. There's no init system in the containers, so starting services isn't covered by this test.

```bash
molecule test -s ha3
```

```bash
molecule test -s container
```

`molecule test -s container` runs container mode on two test nodes that each have systemd and their own Docker engine: Kea 3.0, and Kea 2.6 with its control agent. It checks that the units are running, that Kea answers `status-get` over its HTTP API (on 2.6 through the control agent and the shared socket), and that it answers again after the unit restarts.

`molecule test -s ha3` builds a three-node primary + standby + backup cluster on Debian 12, with Kea 3.0 from ISC's packages. It starts Kea on each node and checks that kea1 and kea2 reach `hot-standby` and kea3 reaches `backup`. It then stops the primary and checks that the standby takes over (`partner-down`) while the backup stays passive.

The Kubernetes path was also applied to a live 3-node kind cluster, in both the Talos-style host-network shape and the EKS-style service shape. Both HA pairs reached `HOT-STANDBY`, re-runs were idempotent, and removal worked. A Kea 2.6 HA pair running over an authenticated control agent was also run live from the role's output and reached `HOT-STANDBY`.

## Known Issues and Gotchas

- **Socket and lease paths are restricted** in Kea 3.x and in 2.6.3+, which got the security backport. Sockets must live in `/var/run/kea`; the literal path `/run/kea` is rejected even though it's the same directory. Lease and log files must sit in Kea's compiled-in directories. The role uses bare names on 3.x for this reason.
- **ISC container images** run as root, but their binaries are owned by `kea:kea` with mode 0754. Dropping all capabilities therefore makes `exec` fail with *Permission denied*. Pods keep `NET_RAW`, `NET_BIND_SERVICE` and `DAC_OVERRIDE` (`kea_dhcp_k8s_capabilities`).
- **ISC images are amd64-only** (see EKS specifics above).
- **EL needs EPEL**: ISC's EL9 RPMs fail to install without it ("nothing provides liblog4cplus-2.0.so.3").
- **Amazon Linux 2023 minimal**: `/usr/bin/dnf` is a symlink to `microdnf`, which has no `-q` option, and Python isn't installed. With `kea_dhcp_bootstrap_python: true`, the role first swaps `microdnf-dnf` for real `dnf`, then installs `python3` and `python3-dnf`.
- **The Kea user without systemd**: EL RPMs create the `kea` user through `systemd-sysusers`, which only runs where systemd is installed. On hosts or containers without it, the role creates the user itself.
- **Kea 3.2 locks down the HTTP API**: it rejects a control socket with neither TLS nor auth (*"Unsecured HTTP control channel"*), and rejects a clear-text `user` in basic auth. The role always writes `<user>.user` and `<user>.password` files and uses `user-file` / `password-file`, which work on 2.6, 3.0 and 3.2. It also fails fast if a 3.2 API would be unsecured.
- **PID file on restarts**: on 2.6 in Kubernetes, `/var/run/kea` is an emptyDir shared with the control agent, so it survives a container restart. Kea then finds its own stale `PID 1` file and refuses to start. Pods set `KEA_PIDFILE_DIR=/tmp`.
- **The control agent** is deprecated in 3.0 and **removed in 3.2**. Asking for it on 3.x fails fast.
- **Unit names differ by package source**. ISC debs use `isc-kea-dhcp4-server`, ISC RPMs and Alpine use `kea-dhcp4`, and Debian's own packages use `kea-dhcp4-server`. The role maps these; override with `kea_dhcp_service_names`.

## License

MIT

## Author Information

Created in 2026 by [Chris Gallagher](https://cgallagher.net). Issues and pull requests are welcome at [git-cgallagher/ansible-collection-isc](https://github.com/git-cgallagher/ansible-collection-isc).
