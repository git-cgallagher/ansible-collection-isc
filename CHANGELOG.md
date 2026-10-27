# Changelog

All notable changes to this role. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added
- Initial role `kea_dhcp` (2026-10-27).
- Package deployment on Alpine (OpenRC), Debian/Ubuntu and RHEL family/Fedora (systemd) from
  ISC Cloudsmith repos (3.0/3.2/2.6, public or subscriber token), distro packages or none;
  arbitrary extra apt/yum/apk repositories; optional raw Python bootstrap for minimal hosts.
- Config generation for DHCPv4, DHCPv6, DDNS and the 2.6 control agent with user settings
  deep-merged last; version-aware 3.x vs 2.6 dialect (sockets, hook paths, SQL hook libraries).
- HA: hot-standby, load-balancing, passive-backup, backup peers, hub-and-spoke relationships,
  multi-threaded dedicated listener or API-based transport, TLS and basic auth pass-through.
- Shared SQL lease databases, host databases, configuration backend, `kea-admin` schema init/upgrade.
- HTTP(S) control API with TLS and basic-auth password files.
- Kubernetes deployment (Talos, EKS, generic): `ha_peers` / `shared_db` topologies, `host` /
  `service` network modes, hostPath/PVC/emptyDir storage, per-peer ClusterIP HA Services,
  config-checksum rollouts, render-only GitOps output.
- EPEL management on EL (Kea RPMs need log4cplus); `kea_dhcp_k8s_state: absent` keeps lease PVCs
  unless `kea_dhcp_k8s_absent_delete_pvc`; HA peer addresses resolve from inventory for peers
  outside the play and must be IPs (fails instead of rendering a hostname URL).
- Kea 3.2 API hardening: credentials via `user-file`/`password-file`; assert against an
  unsecured 3.2 HTTP API. Non-MT HA mirrors `multi-threading: false` to the server and injects
  `basic-auth-*` into peers when the API uses auth (`kea_dhcp_ha_api_auth_user`).
  Pods set `KEA_PIDFILE_DIR=/tmp` (stale PID file on 2.6 container restarts).
- Verified live on a 3-node kind cluster: Talos-style host-network HA and EKS-style
  ClusterIP-service HA both reach HOT-STANDBY; re-runs idempotent; removal works.
- README follows the standard Galaxy role layout (Requirements, Installation, Role Variables,
  Dependencies, Example Playbook, License, Author Information); Galaxy name `git-cgallagher.kea_dhcp`
  (`galaxy_info.namespace: git-cgallagher`; the importer uses it verbatim).
- CI publishes to Ansible Galaxy after every green merge to `main` (`galaxy-import` job,
  `GALAXY_API_KEY` secret; PRs, scheduled and manual runs never publish).
- Public GitHub repo with CI: ansible-lint, render + `kea -t`, Molecule matrix (weekly too).
- Tests: render + `kea -t` validation of 8 shapes in ISC 2.6.5/3.0.4/3.2.1 images; Molecule
  package install on Debian 12, Ubuntu 24.04, Rocky 9, Alpine 3.20/3.22.
