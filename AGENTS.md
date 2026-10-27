# AGENTS.md — ansible-role-kea-dhcp

Standalone Ansible role `kea_dhcp` (Galaxy name `cgallagher.kea_dhcp`). Local git repo; **no
remote yet** — do not push or create one without the owner's go.

## Layout
- `defaults/main.yml` — public interface, documented inline. `meta/argument_specs.yml` — the
  typed contract (keep both in sync when adding a variable).
- `vars/main.yml` — derived internals (`kea_dhcp__*`). `vars/os/<os_family>.yml` — packages,
  services, user per package source.
- `templates/config/*.json.j2` — build each daemon's config as JSON (role-computed first,
  user settings merged last). `templates/k8s/*.yml.j2` — Kubernetes objects.
- `tasks/package/` — host install path. `tasks/kubernetes/` — cluster path (delegated to localhost).
  `tasks/config/build.yml` — shared config build.

## Checks (all must pass before a change is done)
```bash
ansible-lint                      # production profile, must stay clean
tests/run.sh                      # renders 8 shapes, kea -t in ISC 2.6.5/3.0.4/3.2.1 images
# Live k8s (optional): a kind cluster + side-loaded amd64 image; see CHANGELOG for what was proven.
molecule test                     # package installs on 5 distros (amd64; slow under emulation)
```

## Conventions
- Every variable is prefixed `kea_dhcp_` (public) or `kea_dhcp__` (internal); loop vars too.
- Never assume the network: no default interfaces or subnets — assert instead.
- Kea keys are passed through hyphenated, never renamed into role variables.
- Jinja `set` inside a `for` loop does not escape the loop — accumulate with `namespace()`.
- k8s templates rely on `trim_blocks`; keep a blank line before every `---` that follows a
  `{% endif %}` or the YAML documents run together.

## ⚠️ Gotchas (learned the hard way)
- Kea 3.x **and 2.6.3+** reject unix sockets outside `/var/run/kea` — the literal string
  `/run/kea` fails `kea-ctrl-agent -t` even though it is the same directory.
- ISC images: binaries are `kea:kea 0754`, the container runs as root → dropping ALL caps
  breaks exec. Keep `DAC_OVERRIDE`. Images are linux/amd64 only.
- apk trusts a repo key only if the file name matches the signer
  (`kea-3-0@isc-F10F3BFBD3D43C83.rsa.pub`). New series → add its ID to
  `kea_dhcp_isc_repo_alpine_key_ids` (read it from the repo's `setup.alpine.sh`).
- `deb822_repository` needs `python3-debian` on the target; the role uses `apt_repository`
  with an armored `.asc` keyring instead.
- HA in Kubernetes service mode: Kea needs IPs in peer URLs and binds its own URL, so a peer
  renders itself as `0.0.0.0` and its partner as the partner's ClusterIP (verified live in
  Docker: both peers reach HOT-STANDBY).

- ISC EL RPMs need `log4cplus` from EPEL — without it dnf depsolve fails (caught by Molecule
  on Rocky 9). The role installs `epel-release` unless `kea_dhcp_epel_manage: false`.
- A peer's partner URL must be an IP. A `--limit` run once rendered `http://th2:8001/` because
  the partner wasn't in the play; addresses now resolve centrally
  (`templates/config/ha_peer_addresses.json.j2`) and the build asserts they are IPs.
- Kea 3.2 rejects an HTTP API with neither TLS nor auth, and a clear-text `user` — always use
  `user-file` + `password-file` (fine on 2.6/3.0/3.2). `-t` catches this; the role asserts first.
- Non-MT HA: server `multi-threading` must also be off (else HA sticks in WAITING), and peers
  need `basic-auth-*` when the API has auth (else `Unauthorized`). Both verified live on 2.6.5.
- 2.6 in k8s: shared `/var/run/kea` emptyDir survives container restarts → stale "PID 1" file →
  `DHCP4_ALREADY_RUNNING`. Pods set `KEA_PIDFILE_DIR=/tmp`.
- Docker Desktop on Apple silicon can silently lose its amd64 emulator (every amd64 image then
  fails with `exec format error`, which makes all `kea -t` checks fail at once). Re-register it
  with `docker run --privileged --rm tonistiigi/binfmt --install amd64` (resets on Docker restart).
- Molecule on Apple silicon: a locally cached arm64 tag (e.g. `alpine:3.22`) blocks creating the
  amd64 container — `docker pull --platform linux/amd64 <image>` first.

## TODO / follow-ups
- `kea-admin` schema management is untested against a live MySQL/PostgreSQL.
- Molecule cannot start services (no init in containers); service start is untested in CI.
- No CI workflow yet (repo has no remote).
