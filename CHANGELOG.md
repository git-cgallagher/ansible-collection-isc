# Changelog

## 1.0.0 — 2026-10-27

First release of `git_cgallagher.stork`. Kea is out of scope: pair it with
any Kea role.

- `stork_server`:
  - Installs ISC packages on AL2023, EL 8–10, Fedora, Debian/Ubuntu and
    Alpine.
  - Optionally sets up a local PostgreSQL (role, database and pgcrypto).
  - Writes `server.env`, supports TLS and extra `STORK_*` settings, and
    rotates the `admin`/`admin` bootstrap password.
  - Kubernetes mode: Deployment, Service and Secret, plus render-only output.
- `stork_agent`:
  - Three modes: package, container (systemd + `--pid host`) and a
    Kubernetes sidecar spec.
  - Unattended registration with a server token, given directly or read from
    the API.
  - Joins Kea's group so the agent can read Kea's config, logs and API
    password files.
- `stork_repository`: ISC Cloudsmith repo for deb, rpm and apk, including
  `shadow-utils` ordering and the Alpine key naming.
- Multi-arch Dockerfiles for the Stork server and the agent. The agent image
  bundles Kea's binaries.

This collection was split out of the earlier all-in-one `kea_stork` role
(local only, never published).
