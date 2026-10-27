# ansible-kea-stork

An Ansible role (`roles/kea_stork`) that deploys **ISC Kea DHCP**, optionally
as a **high-availability** pair or trio, and **ISC Stork** for monitoring, in
one of three ways:

| `kea_deploy_mode` | Where | How |
|---|---|---|
| `package` (default) | Amazon Linux 2023, RHEL/Rocky/Alma 8–10, Fedora, Debian 12/13, Ubuntu 22.04/24.04, Alpine 3.21+ | ISC's Cloudsmith packages, run by systemd or OpenRC |
| `container` | Any systemd host with podman/docker, including distros without ISC packages (Fedora CoreOS, Flatcar, …) | Kea image plus a systemd unit per daemon, on host networking |
| `kubernetes` | EKS, Talos, or any conformant cluster | Manifests applied from the control node; `kea_k8s_profile: eks\|talos\|generic` |

It targets **Kea 3.0 LTS** (3.2 via `kea_branch: "3-2"`) and **Stork 2.6**.
It never uses the deprecated Control Agent, which 3.2 removed: each daemon
serves its own HTTP control socket, and Stork talks to that directly.

Read [docs/research.md](docs/research.md) for what was found and verified,
[docs/kubernetes.md](docs/kubernetes.md) for EKS/Talos, and
[docs/testing.md](docs/testing.md) for how the role was tested.

## Quick start (VMs)

```bash
ansible-galaxy collection install -r requirements.yml -p ./collections
```

```bash
ansible-playbook -i examples/inventory/hosts.yml examples/playbooks/site.yml --ask-vault-pass
```

Minimal HA pair (`group_vars/kea.yml`):

```yaml
kea_ha_enabled: true
kea_ha_mode: hot-standby
kea_ha_peers:                 # IP literals — Kea won't resolve hostnames in HA URLs
  - { name: kea1, address: 10.0.0.11, role: primary }
  - { name: kea2, address: 10.0.0.12, role: standby }
kea_dhcp4_subnets:
  - id: 1                     # explicit ids required
    subnet: 10.0.0.0/24
    pools: [{ pool: 10.0.0.100 - 10.0.0.200 }]
stork_server_url: http://10.0.0.20:8080
```

`kea_dhcp4_subnets`, `kea_dhcp4_option_data`, `kea_dhcp4_reservations` and
`kea_dhcp4_extra` use Kea's own JSON schema, written as YAML. The `kea_dhcp6_*`
equivalents work the same way. The role builds the config as a data
structure, so the output is always valid JSON. It validates the config with
`kea-dhcp4 -t` before installing it, and reloads Kea (SIGHUP → config-reload)
rather than restarting it.

## Quick start (Kubernetes)

```bash
pip install kubernetes
```

```bash
ansible-playbook -i examples/inventory/hosts.yml examples/playbooks/kubernetes.yml
```

See `examples/inventory/group_vars/kea_k8s.yml`. Moving between EKS and Talos
is a one-line change (`kea_k8s_profile`).

## What the role does

- **Kea:**
  - Configures the ISC repo for the distro. On AL2023 that means the EL9 repo
    plus EPEL 9 limited to `log4cplus`.
  - Installs the daemons and hooks, with an optional version pin.
  - Renders `/etc/kea/kea-dhcp{4,6}.conf` with unix + HTTP control sockets, the
    HA hooks (`lease_cmds` then `ha`, HA+MT dedicated listener on 8001/8002),
    optional mutual TLS, and memfile/MySQL/PostgreSQL leases.
  - Validates, then reloads.
- **Stork agent:**
  - Installs the agent next to Kea and lets it read Kea's config and logs.
  - Registers it once, unattended when a server token is available. The role
    can read the token from the Stork API when you give `stork_admin_password`.
  - Exposes a Prometheus exporter on :9547.
- **Stork server:**
  - Installs the server.
  - Optionally installs a local PostgreSQL with the role, database and
    `pgcrypto`; otherwise points at external PG such as RDS.
  - Writes `server.env` (0640).
  - Rotates the `admin`/`admin` bootstrap password when you set
    `stork_admin_password`, on VMs and in-cluster.
- **Kubernetes:**
  - One single-replica StatefulSet per HA peer, with a pinned ClusterIP for HA
    traffic and a LoadBalancer for relayed DHCP.
  - A Stork agent sidecar (shared PID namespace).
  - A NetworkPolicy, Pod Security labels, and a per-peer rollout.

## HA semantics worth knowing

- With the default `kea_ha_max_unacked_clients: 5`, a standby **will not**
  take over just because the primary stopped answering heartbeats. It also
  needs to see DHCP clients going unanswered. That guards against split-brain
  when only the HA link breaks. Don't set it to `0` in production unless you
  understand that trade-off.
- Relays must forward to **both** peers.
- In load-balancing mode, both peers serve. Size each one to carry 100% of the
  load on its own.

## Repository layout

```
roles/kea_stork/
  defaults/main.yml        every knob, documented
  vars/                    per-OS-family constants (service names, users, prereqs)
  tasks/                   validate → platform → repo_* → stork_server → kea_* → stork_agent; kubernetes.yml
  templates/               kea-dhcp.conf.j2 (v4+v6), env files, systemd units, k8s/*.yaml.j2
  files/                   Dockerfile.kea / .stork-agent / .stork-server (multi-arch)
examples/                  inventory + playbooks (VM, EKS/Talos)
molecule/default/          4-container HA + Stork integration test
molecule/k8s/              vars for the live k3s test
docs/                      research, kubernetes, testing
```
