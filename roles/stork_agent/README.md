# git_cgallagher.isc.stork_agent

Installs the [ISC Stork](https://stork.readthedocs.io/) agent **next to an
existing ISC Kea** and registers it with a Stork server. This role does not
install Kea.

The agent finds Kea by scanning processes, reads the config file named on
Kea's command line, and talks to the HTTP control socket it defines. It
reads Kea API credentials from that config, preferring a client whose user
name starts with `stork`. It opens **every** client's `user-file` and
`password-file`, not only that one, and fails to detect the daemon if any of
them is missing. Where Kea runs decides the mode:

| `stork_agent_deploy_mode` | Kea runs… | The role… |
|---|---|---|
| `package` | from packages on the host | installs `isc-stork-agent`, adds it to Kea's group, registers it, starts it |
| `container` | in a container on the host | runs the agent image under systemd with `--pid host`, Kea's paths mounted read-only |
| `kubernetes` | in a pod | sets `stork_agent_k8s_containers` / `stork_agent_k8s_volumes` for your Kea pod template and stores the token in a Secret |

The container and Kubernetes modes need the agent image to contain the Kea
binaries: the agent identifies a daemon by running `kea-dhcp4 -v` from its
own filesystem. `docker/Dockerfile.stork-agent` builds such an image.

## Requirements

- Kea installed and running first, with an HTTP(S) entry in `control-sockets`.
- Unattended registration needs either `stork_agent_server_token` or
  `stork_agent_api_password`. With the password, the role reads the token from
  the server's API, from the control node, once per play.
- Kubernetes mode: the Kea pod needs `shareProcessNamespace: true`, and its
  namespace needs Pod Security `privileged`, because the sidecar adds
  `SYS_PTRACE`.

## Role Variables

Every variable is documented in [defaults/main.yml](defaults/main.yml). The
main ones:

| Variable | Default | Description |
|---|---|---|
| `stork_agent_deploy_mode` | `package` | `package`, `container` or `kubernetes` |
| `stork_agent_server_url` | `""` | **Required.** URL the agent registers with. |
| `stork_agent_address` | `ansible_host` | How the server reaches this agent |
| `stork_agent_port` | `8080` | Agent listener |
| `stork_agent_server_token` | `""` | Server token for unattended registration (vault it) |
| `stork_agent_api_user` / `_password` | `admin` / `""` | Or let the role read the token from the API |
| `stork_agent_api_url` | `stork_agent_server_url` | API URL as seen from the control node |
| `stork_agent_kea_group` | `""` (detect `_kea`/`kea`) | Kea's group, for read access to its config and credentials |
| `stork_agent_prometheus_kea_port` | `9547` | Prometheus Kea exporter |
| `stork_agent_image` | `""` | **Required** in container and Kubernetes modes |
| `stork_agent_container_kea_mounts` | `[/etc/kea, /var/log/kea]` | Host paths shared read-only, at the same paths Kea uses |
| `stork_agent_k8s_volume_mounts` | `[]` | Extra sidecar mounts, using your Kea pod's volume names. Leave empty with `kea_dhcp`, which adds its own config mounts. |
| `stork_agent_k8s_address` | `$(POD_IP)` | Address advertised per pod. A pod IP changes on every restart, so set a stable name; with `kea_dhcp` in service mode, `kea-<host>-ha.<namespace>.svc.cluster.local`. |
| `stork_agent_k8s_namespace` | `""` | Kea's namespace, for the token Secret |
| `stork_agent_k8s_create_namespace` | `true` | Create that namespace if it doesn't exist yet. This role usually runs before the Kea role. |

## Dependencies

`git_cgallagher.isc.stork_repository`, included automatically in package
mode.

## Example Playbook

```yaml
- hosts: kea
  become: true
  roles:
    - role: git_cgallagher.isc.stork_agent
      vars:
        stork_agent_version: "2.6.0"
        stork_agent_server_url: http://stork.example.internal:8080
        stork_agent_api_password: "{{ vault_stork_admin_password }}"
```

## License

MIT

## Author Information

Chris Gallagher ([@git-cgallagher](https://github.com/git-cgallagher))
