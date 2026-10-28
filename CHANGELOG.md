# Changelog

## 1.0.0 — 2026-10-27

First release of `git_cgallagher.isc`. It merges two earlier projects; both
keep their full git history in this repository.

- **`kea_dhcp`**, previously the standalone Galaxy role `git-cgallagher.kea_dhcp`:
  - Behaviour and variables are unchanged.
  - New: `kea_dhcp_k8s_share_process_namespace` (default `false`) sets
    `shareProcessNamespace` on Kea pods so a Stork agent sidecar can see
    Kea's process.
  - Its pre-merge history is in
    [docs/kea_dhcp-changelog-standalone.md](docs/kea_dhcp-changelog-standalone.md).
- **`stork_server`, `stork_agent`, `stork_repository`**, previously the
  collection `git_cgallagher.stork` 1.0.0: behaviour and variables are
  unchanged.
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
| `git_cgallagher.stork.<role>` | `git_cgallagher.isc.<role>` |
