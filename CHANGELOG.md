# Changelog

## 1.1.0 — 2026-10-28

- **`kea_dhcp`**: new example
  [`examples/kea_dhcp/vm-ha3`](examples/kea_dhcp/vm-ha3/): three VMs as
  primary + standby + backup. No role changes.
- New Molecule scenario `kea_dhcp_ha3`, also run in CI. It starts Kea on three
  Debian 12 nodes and checks the HA states, then a real failover: the standby
  takes over when the primary stops and the backup stays passive.

## 1.0.1 — 2026-10-28

- Docs: the migration notes now cover only the standalone Kea role.
- `stork_server`: the header of the generated `server.env` names this
  collection's role.

## 1.0.0 — 2026-10-27

First release of `git_cgallagher.isc`.

- **`kea_dhcp`**, previously the standalone Galaxy role `git-cgallagher.kea_dhcp`:
  - Behaviour and variables are unchanged.
  - New: `kea_dhcp_k8s_share_process_namespace` (default `false`) sets
    `shareProcessNamespace` on Kea pods so a Stork agent sidecar can see
    Kea's process.
  - Its pre-merge history is in
    [docs/kea_dhcp-changelog-standalone.md](docs/kea_dhcp-changelog-standalone.md).
- **`stork_server`, `stork_agent`, `stork_repository`** (new): the Stork
  server, agents next to Kea on hosts, in containers or as a Kubernetes
  sidecar, and ISC's Stork package repository.
- One CI pipeline covers everything:
  - ansible-test sanity on ansible-core 2.18–2.21;
  - ansible-lint (production profile);
  - Kea render plus `kea -t`;
  - Kea Molecule per distro;
  - Stork Molecule.
- Releases are automated: a green merge to `main` publishes to Galaxy and
  creates the GitHub release.

### Migrating

| Before | After |
|---|---|
| `git-cgallagher.kea_dhcp` (role) | `git_cgallagher.isc.kea_dhcp` |
