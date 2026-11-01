# Testing

| Check | How | Result (2026-10-27) |
|---|---|---|
| Kea render | `tests/kea_dhcp/run.sh`: 8 deployment shapes (14 instances) rendered without a cluster, every config checked with `kea-<daemon> -t` in the ISC 2.6.5 / 3.0.4 / 3.2.1 images | ✅ see CI |
| Kea packages | `molecule test -s default` in `roles/kea_dhcp`: Debian 12, Ubuntu 24.04, Rocky 9, Alpine 3.20 (ISC) and 3.22 (distro); install, idempotence, config re-validation | ✅ see CI (services aren't started: no init in those containers) |
| BIND 9 | `molecule test -s default` in `roles/bind9`: AL2023 (9.18), Rocky 9 (9.16), Debian 12 and Ubuntu 24.04 (9.18), Alpine 3.22 (9.20); install, idempotence, `named-checkconf -z`, then `named` started by verify | ✅ zones answer, a TSIG-signed update lands, an unsigned one is REFUSED, rndc and the statistics channel respond (`named` isn't started through systemd/OpenRC: no init) |
| Stork | `molecule test -s default` in `roles/stork_server`: server on Ubuntu 24.04; agents next to Kea 3.0.4 on AL2023 (no API auth) and Kea 3.2.1 on Debian 12 (basic auth via `user-file`/`password-file`) | ✅ both daemons active + monitored, unattended registration, rotated admin password |
| Stork on AL2023, Kea in containers | `molecule test -s container` in `roles/stork_agent`: server from packages + PostgreSQL 16 on Amazon Linux 2023; `kea_dhcp` container mode (Kea 3.0.4, basic auth) and `stork_agent` container mode on an AL2023 node with its own Docker engine | ✅ the agent registered unattended, the daemon is active + monitored, units running, idempotent |
| Kubernetes | Stork server manifests and the generated sidecar spec checked with `kubectl apply --dry-run=server` (k3s 1.33). The Kea Kubernetes path was proven live on kind before the merge (see the Kea role README). | ✅ |
| Stork sidecar, live (2026-10-28, by hand) | k3s 1.33 in Docker. `stork_server` in Kubernetes mode against an in-cluster PostgreSQL, with the admin password rotated through a port-forward. Then `stork_agent` (Kubernetes mode) plus `kea_dhcp`: a hot-standby pair in service network mode, with API basic auth for `ha` and `stork`. Stork 2.6.0, Kea 3.0.4. Also tested: a pod deleted, and an agent re-registered with fresh state at the same address. | ✅ both daemons active + monitored, subnet found on both, HA hot-standby with both peers in touch. Fixes from this run are in CHANGELOG 1.4.0; [stork-kubernetes.md](stork-kubernetes.md) lists the behaviour seen. |
| Argument specs | `tests/argument_specs/run.sh` (workflow `argument-specs`, ansible-core 2.18 and 2.21): every role's spec matches its defaults (names, types, choices, `no_log` on secrets); `ansible-doc` loads each role; each role rejects a bad value through its spec | ✅ |
| Lint | `ansible-lint` (production), `yamllint` | ✅ |
| Sanity | `ansible-test sanity` | ✅ |

The Kea in `roles/stork_server/molecule/default` comes from that scenario's `prepare.yml`, a
fixture. The real Kea role is tested by its own scenario.

## Not covered yet

- The agent's container mode under podman. `stork_container` uses Docker,
  the only runtime Amazon Linux 2023 has. Nested podman can't exec on the
  development machine (Docker Desktop).
- The Stork sidecar in CI. The live test above was run by hand. It needs
  amd64 emulation on arm64 (ISC's Kea images are amd64-only), so it runs
  slowly on a Mac.
- The sidecar with Kea in host network mode (Talos/generic default), and
  with Kea 3.2.
- `kea-admin` schema management against a live MySQL/PostgreSQL.
- Alpine (OpenRC) hosts, and real EKS or Talos clusters.

## Running

See the Checks section of [AGENTS.md](../AGENTS.md). CI runs every check on
each push and PR, plus weekly.
