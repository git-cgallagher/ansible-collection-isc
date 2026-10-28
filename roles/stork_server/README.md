# git_cgallagher.isc.stork_server

Installs and configures the [ISC Stork](https://stork.readthedocs.io/)
server, either on a host from ISC's packages or in Kubernetes as a
single-replica Deployment. It can also bootstrap a local PostgreSQL, and it
rotates the `admin`/`admin` bootstrap password.

## Requirements

- **PostgreSQL ≥ 10 with `pgcrypto`**: local (`stork_server_db_install_local: true`)
  or external (RDS, CloudNativePG, …). For an external server, create the
  database, user and extension first.
- Kubernetes mode: `kubernetes.core` plus `pip install kubernetes` on the
  control node, and a Stork server image. ISC publishes none, so build
  `docker/Dockerfile.stork-server` from this collection.

Stork keeps all of its state in PostgreSQL, so its availability is the
database's. Run one server against an HA database rather than several
servers.

## Role Variables

Every variable is documented in [defaults/main.yml](defaults/main.yml) and
validated by [meta/argument_specs.yml](meta/argument_specs.yml) when the role
starts (`ansible-doc -t role git_cgallagher.isc.stork_server` lists them). The
main ones:

| Variable | Default | Description |
|---|---|---|
| `stork_server_deploy_mode` | `package` | `package` or `kubernetes` |
| `stork_server_version` | `""` | Pin, e.g. `2.6.0` (empty = latest) |
| `stork_server_rest_host` / `_port` | `0.0.0.0` / `8080` | REST API and UI listener |
| `stork_server_tls` | `{}` | `{cert, key, ca}` for HTTPS (and mutual TLS with `ca`) |
| `stork_server_enable_metrics` | `false` | `/metrics` has **no authentication**; firewall it |
| `stork_server_extra_env` | `{}` | Any other `STORK_*` setting, e.g. OIDC |
| `stork_server_db_install_local` | `true` | Install PostgreSQL here and create role, database and pgcrypto |
| `stork_server_db_host` / `_port` / `_name` / `_user` | `localhost` / `5432` / `stork` / `stork` | Database |
| `stork_server_db_password` | `""` | **Required.** Vault it. |
| `stork_server_db_sslmode` | `disable` locally, else `require` | |
| `stork_server_admin_password` | `""` | When set, replaces the `admin`/`admin` bootstrap password. Stork's default policy needs 12+ characters with upper and lower case letters, a digit and a special character or space. A refused password fails the run with Stork's reason. |
| `stork_server_k8s_image` | `""` | **Required** in Kubernetes mode |
| `stork_server_k8s_namespace` | `stork` | Created unless `stork_server_k8s_create_namespace: false` |
| `stork_server_k8s_service_type` | `ClusterIP` | |
| `stork_server_k8s_api_url` | `""` | URL the control node uses for the password rotation in Kubernetes |
| `stork_server_k8s_state` | `present` | `absent` removes everything |

## Dependencies

`git_cgallagher.isc.stork_repository`, included automatically in package
mode.

## Example Playbook

```yaml
- hosts: stork_server
  become: true
  roles:
    - role: git_cgallagher.isc.stork_server
      vars:
        stork_server_version: "2.6.0"
        stork_server_db_password: "{{ vault_stork_db_password }}"
        stork_server_admin_password: "{{ vault_stork_admin_password }}"
```

## License

MIT

## Author Information

Chris Gallagher ([@git-cgallagher](https://github.com/git-cgallagher))
