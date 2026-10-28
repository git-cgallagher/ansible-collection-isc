# Testing

| Check | How | Result (2026-10-27) |
|---|---|---|
| Kea render | `tests/kea_dhcp/run.sh`: 8 deployment shapes (14 instances) rendered without a cluster, every config checked with `kea-<daemon> -t` in the ISC 2.6.5 / 3.0.4 / 3.2.1 images | ✅ see CI |
| Kea packages | `molecule test -s kea_dhcp`: Debian 12, Ubuntu 24.04, Rocky 9, Alpine 3.20 (ISC) and 3.22 (distro); install, idempotence, config re-validation | ✅ see CI (services aren't started: no init in those containers) |
| Stork | `molecule test -s stork`: server on Ubuntu 24.04; agents next to Kea 3.0.4 on AL2023 (no API auth) and Kea 3.2.1 on Debian 12 (basic auth via `user-file`/`password-file`) | ✅ both daemons active + monitored, unattended registration, rotated admin password |
| Kubernetes | Stork server manifests and the generated sidecar spec checked with `kubectl apply --dry-run=server` (k3s 1.33). The Kea Kubernetes path was proven live on kind before the merge (see the Kea role README). | ✅ |
| Lint | `ansible-lint` (production), `yamllint` | ✅ |
| Sanity | `ansible-test sanity` | ✅ |

The Kea in `molecule/stork` comes from that scenario's `prepare.yml`, a
fixture. The real Kea role is tested by its own scenario.

## Not covered yet

- Container mode end to end. Nested podman can't exec on the development
  machine (Docker Desktop). An earlier revision exercised the same unit
  through a podman shim and replayed the exact command lines on real Docker.
- A live Stork sidecar inside a `kea_dhcp` pod. The switch exists
  (`kea_dhcp_k8s_share_process_namespace`), but the pair hasn't run together
  on a cluster yet.
- `kea-admin` schema management against a live MySQL/PostgreSQL.
- Alpine (OpenRC) hosts, and real EKS or Talos clusters.

## Running

See the Checks section of [AGENTS.md](../AGENTS.md). CI runs every check on
each push and PR, plus weekly.
