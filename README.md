# git_cgallagher.isc

[![ansible-test](https://github.com/git-cgallagher/ansible-collection-isc/actions/workflows/ansible-test.yml/badge.svg)](https://github.com/git-cgallagher/ansible-collection-isc/actions/workflows/ansible-test.yml)
[![Galaxy](https://img.shields.io/badge/galaxy-git__cgallagher.isc-blue.svg)](https://galaxy.ansible.com/ui/repo/published/git_cgallagher/isc/)

Ansible collection for [ISC](https://www.isc.org/) network services:

- **Kea DHCP**: DHCPv4, DHCPv6 and DDNS, with high availability, shared SQL
  lease databases and the configuration backend. Runs on hosts (from ISC's or
  the distro's packages) or on Kubernetes (Talos, EKS, generic).
- **Stork**: the monitoring server, and agents that sit next to Kea on hosts,
  in containers, or as a sidecar in Kea's pods.

This collection replaces the standalone role `git-cgallagher.kea_dhcp` and
the collection `git_cgallagher.stork`, which are retired. See
[Migrating](#migrating).

## Tested with

| | Versions |
|---|---|
| ansible-core | 2.16+ (CI: 2.18, 2.19, 2.20, 2.21) |
| ISC Kea | 3.0 (LTS, default), 3.2, 2.6 (EOL, existing estates only) |
| ISC Stork | 2.6 |
| Platforms | Debian 12/13, Ubuntu 22.04/24.04, RHEL/Rocky/Alma 8–10, Fedora, Amazon Linux 2023 (Stork), Alpine 3.20+ |
| Kubernetes | Talos, EKS, any conformant cluster |

## External requirements

- Kubernetes mode: the `kubernetes.core` collection plus the `kubernetes`
  Python package on the control node.
- Alpine hosts: `community.general`, for the `apk` module.
- Stork server: PostgreSQL ≥ 10 with `pgcrypto`, either installed locally by
  the role or an existing server (RDS, CloudNativePG, …).
- Stork in containers or Kubernetes: Stork images. ISC publishes none; build
  them from [`docker/`](docker/).

## Included content

| Role | Description |
|---|---|
| [`git_cgallagher.isc.kea_dhcp`](roles/kea_dhcp/README.md) | Kea DHCPv4/v6/DDNS from packages or on Kubernetes. HA (hot-standby, load-balancing, passive-backup, hub-and-spoke), shared SQL leases, config backend, HTTP(S) API with auth. |
| [`git_cgallagher.isc.stork_server`](roles/stork_server/README.md) | Stork server: packages + optional local PostgreSQL, or a Kubernetes Deployment. Rotates the `admin`/`admin` bootstrap password. |
| [`git_cgallagher.isc.stork_agent`](roles/stork_agent/README.md) | Stork agent next to Kea: native package, container + systemd, or a Kubernetes sidecar spec for the Kea pod. Unattended registration. |
| [`git_cgallagher.isc.stork_repository`](roles/stork_repository/README.md) | ISC's Cloudsmith Stork package repository (deb/rpm/apk). Used by the Stork roles. |

## Using this collection

### Installing the collection from Ansible Galaxy

```bash
ansible-galaxy collection install git_cgallagher.isc
```

Or in a `requirements.yml`:

```yaml
---
collections:
  - name: git_cgallagher.isc
  - name: community.general   # Alpine hosts
  - name: kubernetes.core     # Kubernetes deployments
```

### Kea HA pair with Stork monitoring, on hosts

```yaml
- name: Kea HA pair
  hosts: kea
  become: true
  roles:
    - role: git_cgallagher.isc.kea_dhcp
      vars:
        kea_dhcp_interfaces: [eth0]
        kea_dhcp_api_http_enabled: true
        # Stork picks the API client whose name starts with "stork".
        kea_dhcp_api_auth_clients: [{ user: stork, password: "{{ vault_kea_api_password }}" }]
        kea_dhcp_ha_enabled: true
        kea_dhcp_ha_peers:
          - { name: kea1, role: primary }
          - { name: kea2, role: standby }
        kea_dhcp_dhcp4_settings:
          subnet4:
            - id: 1
              subnet: 192.0.2.0/24
              pools: [{ pool: 192.0.2.100 - 192.0.2.200 }]

- name: Stork server
  hosts: stork_server
  become: true
  roles:
    - role: git_cgallagher.isc.stork_server
      vars:
        stork_server_db_password: "{{ vault_stork_db_password }}"
        stork_server_admin_password: "{{ vault_stork_admin_password }}"

- name: Stork agents next to Kea
  hosts: kea
  become: true
  roles:
    - role: git_cgallagher.isc.stork_agent
      vars:
        stork_agent_server_url: http://stork.example.internal:8080
        stork_agent_api_password: "{{ vault_stork_admin_password }}"
```

### Kubernetes: Kea pods with a Stork sidecar

```yaml
- hosts: kea   # logical Kea instances, ansible_connection: local
  roles:
    - role: git_cgallagher.isc.stork_agent
      vars:
        stork_agent_deploy_mode: kubernetes
        stork_agent_image: registry.example/stork-agent:2.6.0-kea3.0.4
        stork_agent_server_url: http://stork-server.stork.svc.cluster.local:8080
        stork_agent_server_token: "{{ vault_stork_server_token }}"
        stork_agent_k8s_namespace: kea-dhcp
    - role: git_cgallagher.isc.kea_dhcp
      vars:
        kea_dhcp_deployment: kubernetes
        kea_dhcp_k8s_share_process_namespace: true
        kea_dhcp_k8s_extra_containers: "{{ stork_agent_k8s_containers }}"
        kea_dhcp_k8s_extra_volumes: "{{ stork_agent_k8s_volumes }}"
```

More inventories are in [`examples/kea_dhcp/`](examples/kea_dhcp/). The
Stork sidecar wiring, including how its mounts must mirror Kea's, is in
[docs/stork-kubernetes.md](docs/stork-kubernetes.md).

## Migrating

| Before | After |
|---|---|
| `ansible-galaxy role install git-cgallagher.kea_dhcp` | `ansible-galaxy collection install git_cgallagher.isc` |
| `role: git-cgallagher.kea_dhcp` | `role: git_cgallagher.isc.kea_dhcp` |
| `ansible-galaxy collection install git_cgallagher.stork` | `ansible-galaxy collection install git_cgallagher.isc` |
| `role: git_cgallagher.stork.stork_agent` (and `stork_server`, `stork_repository`) | `role: git_cgallagher.isc.stork_agent` (and the others) |

The variables are unchanged. The only addition is
`kea_dhcp_k8s_share_process_namespace`, which defaults to `false`.

## Release notes

See [CHANGELOG.md](CHANGELOG.md).

## More information

- [Kea role README](roles/kea_dhcp/README.md): configuration model, HA,
  Kubernetes, gotchas.
- [docs/stork-research.md](docs/stork-research.md): verified Stork and Kea
  behaviour the Stork roles depend on, with sources.
- [docs/testing.md](docs/testing.md): what is tested and how.
- [Kea ARM](https://kea.readthedocs.io/) ·
  [Stork documentation](https://stork.readthedocs.io/)

## Licensing

MIT. See [LICENSE](LICENSE).
