# git_cgallagher.stork

[![ansible-test](https://github.com/git-cgallagher/ansible-collection-stork/actions/workflows/ansible-test.yml/badge.svg)](https://github.com/git-cgallagher/ansible-collection-stork/actions/workflows/ansible-test.yml)

Ansible collection for [ISC Stork](https://www.isc.org/stork/), the
monitoring and management dashboard for ISC Kea DHCP. It deploys the Stork
**server** and Stork **agents** on hosts (from ISC's packages), on container
hosts (podman or docker), and on Kubernetes (EKS, Talos or any conformant
cluster).

This collection does **not** install or configure Kea. Use your Kea role of
choice, for example `kea_dhcp`, and point this collection at it. The only
contract between the two is described in
[Working with your Kea deployment](#working-with-your-kea-deployment).

## Tested with

| | Versions |
|---|---|
| ansible-core | 2.16+ (CI: 2.18, 2.19, 2.20, 2.21) |
| ISC Stork | 2.6 (stable) |
| ISC Kea | 3.0 (LTS) and 3.2; no Control Agent needed |
| Platforms | Amazon Linux 2023, RHEL/Rocky/Alma 8–10, Fedora, Debian 12/13, Ubuntu 22.04/24.04, Alpine 3.21+ |

## External requirements

- **Kea** running on the agent's host or pod, with an HTTP(S) control socket
  on each daemon (`control-sockets`, socket type `http` or `https`).
- **PostgreSQL ≥ 10 with `pgcrypto`** for the server. The `stork_server` role
  can install it locally, or you can point it at an existing server such as
  RDS or CloudNativePG.
- Kubernetes mode: the `kubernetes.core` collection and the `kubernetes`
  Python package on the control node.
- Container and Kubernetes modes: Stork images. ISC publishes none, so build
  them from [`docker/`](docker/):
  - `Dockerfile.stork-server`.
  - `Dockerfile.stork-agent`, which bundles the Kea binaries that the agent
    executes to identify daemons.

## Included content

| Role | Description |
|---|---|
| [`git_cgallagher.stork.stork_server`](roles/stork_server/README.md) | Stork server: packages + optional local PostgreSQL, or a Kubernetes Deployment; rotates the `admin`/`admin` bootstrap password |
| [`git_cgallagher.stork.stork_agent`](roles/stork_agent/README.md) | Stork agent next to Kea: native package, container + systemd unit, or a Kubernetes sidecar spec; unattended registration |
| [`git_cgallagher.stork.stork_repository`](roles/stork_repository/README.md) | ISC Cloudsmith Stork package repository (deb/rpm/apk); used by the other two |

## Using this collection

### Installing the collection from Ansible Galaxy

```bash
ansible-galaxy collection install git_cgallagher.stork
```

Or in a `requirements.yml`:

```yaml
---
collections:
  - name: git_cgallagher.stork
```

Then install the optional dependencies for the modes you use:

```bash
ansible-galaxy collection install kubernetes.core community.general
```

### Hosts: a Stork server plus agents next to existing Kea servers

```yaml
- name: Stork server
  hosts: stork_server
  become: true
  roles:
    - role: git_cgallagher.stork.stork_server
      vars:
        stork_server_db_password: "{{ vault_stork_db_password }}"
        stork_server_admin_password: "{{ vault_stork_admin_password }}"

- name: Stork agents (run after your Kea role)
  hosts: kea
  become: true
  roles:
    - role: git_cgallagher.stork.stork_agent
      vars:
        stork_agent_server_url: http://stork.example.internal:8080
        stork_agent_api_password: "{{ vault_stork_admin_password }}"   # fetch the server token
```

Run the server play first. Agents read the server token from its API and
register unattended.

### Kubernetes: Stork server in-cluster, agent as a sidecar in the Kea pods

```yaml
- name: Stork on Kubernetes
  hosts: localhost
  connection: local
  roles:
    - role: git_cgallagher.stork.stork_server
      vars:
        stork_server_deploy_mode: kubernetes
        stork_server_k8s_image: registry.example/stork-server:2.6.0
        stork_server_db_host: stork.abcdefgh.us-east-1.rds.amazonaws.com
        stork_server_db_password: "{{ vault_stork_db_password }}"
    - role: git_cgallagher.stork.stork_agent
      vars:
        stork_agent_deploy_mode: kubernetes
        stork_agent_image: registry.example/stork-agent:2.6.0-kea3.0.4
        stork_agent_server_url: http://stork-server.stork.svc.cluster.local:8080
        stork_agent_server_token: "{{ vault_stork_server_token }}"
        stork_agent_k8s_namespace: kea-dhcp    # where your Kea pods run
  # The agent role sets stork_agent_k8s_containers / stork_agent_k8s_volumes;
  # hand them to your Kea role's pod template (see below).
```

## Working with your Kea deployment

The agent always runs **next to Kea**: on the same host, or in the same pod
with a shared process namespace. It finds Kea by scanning processes, reads
the config file named on Kea's command line, and talks to the HTTP control
socket defined there. In practice:

| Kea must… | Why |
|---|---|
| define an HTTP(S) entry in `control-sockets` | Stork uses it; Kea 3.x needs no Control Agent |
| let the agent read its config, logs and API password files | The role adds `stork-agent` to Kea's group (`_kea` / `kea`, or `stork_agent_kea_group`). Stork reads API credentials **from the Kea config**, preferring a client whose user name starts with `stork`. |
| (containers) mount its config at the same path for the agent | the agent follows the path on Kea's command line (`stork_agent_container_kea_mounts`) |
| (Kubernetes) run with `shareProcessNamespace: true`, plus the agent's sidecar and volumes | the agent must see Kea's process, and mount Kea's config volume at the same paths (`stork_agent_k8s_volume_mounts`) |

With the `kea_dhcp` role, give it an API client named `stork…`. On
Kubernetes, pass the sidecar through:

```yaml
kea_dhcp_api_auth_clients:
  - { user: stork, password: "{{ vault_kea_api_password }}" }
kea_dhcp_k8s_extra_containers: "{{ stork_agent_k8s_containers }}"
kea_dhcp_k8s_extra_volumes: "{{ stork_agent_k8s_volumes }}"
```

> `kea_dhcp` doesn't expose `shareProcessNamespace` yet. Until it does, the
> sidecar can't see Kea's process. See [docs/kubernetes.md](docs/kubernetes.md).

## Release notes

See [CHANGELOG.md](CHANGELOG.md).

## More information

- [docs/research.md](docs/research.md): verified Stork and Kea behaviour this
  collection depends on, with sources.
- [docs/kubernetes.md](docs/kubernetes.md): sidecar wiring, Pod Security,
  EKS/Talos notes.
- [docs/testing.md](docs/testing.md): what is tested and how.
- [Stork documentation](https://stork.readthedocs.io/) ·
  [Kea ARM](https://kea.readthedocs.io/)

## Licensing

MIT. See [LICENSE](LICENSE).
