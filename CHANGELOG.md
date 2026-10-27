# Changelog

## 0.1.0 — 2026-10-27

Initial role.

- Kea 3.0 LTS / 3.2 from ISC Cloudsmith on AL2023 (EL9 RPMs + EPEL
  log4cplus), RHEL-family 8–10, Fedora, Debian/Ubuntu and Alpine.
  Version pins supported.
- HA: hot-standby, load-balancing and passive-backup, with backups, the HA+MT
  dedicated listener and optional mutual TLS. Inputs are validated (IP-literal
  URLs, role/mode consistency, explicit subnet ids).
- No Control Agent: per-daemon unix and HTTP control sockets.
- Stork 2.6: unattended agent registration (server token read from the API),
  Prometheus exporter, and a server with optional local PostgreSQL. The
  bootstrap admin password is rotated.
- Container mode (podman/docker + systemd) for distros without ISC packages.
- Kubernetes mode with `eks`, `talos` and `generic` profiles: per-peer
  StatefulSets, pinned ClusterIPs, LB per peer, Stork sidecar, in-cluster
  Stork server, NetworkPolicy, PSA labels, and serial per-peer rollout.
- Multi-arch Dockerfiles for Kea, the Stork agent and the Stork server.
- Molecule HA integration test (AL2023 + Debian 12 + Rocky 9 + Ubuntu 24.04),
  including a failover check.
