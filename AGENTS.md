# AGENTS.md — ansible-collection-isc

Ansible collection **`git_cgallagher.isc`** (MIT) for ISC network services. It
holds the Kea role `kea_dhcp` and the Stork roles `stork_server`, `stork_agent`
and `stork_repository`. Public repo `git-cgallagher/ansible-collection-isc`,
published to Galaxy as `git_cgallagher.isc`.

It **replaces** the standalone role `git-cgallagher.kea_dhcp` (repo
`ansible-role-kea-dhcp`, archived), whose full git history is merged in under
`roles/kea_dhcp`. Work on branches and PRs; `main` is protected.

⚠️ Other sessions may use `~/Code/ansible-collection-isc` at the same time:
`git checkout -b` there carries their uncommitted work onto your branch. Do
your work in a separate `git worktree` instead.

## Layout

```
roles/kea_dhcp/          Kea DHCP (packages or Kubernetes); its README is the user guide
roles/stork_*            Stork server, agent, package repository
docker/                  Stork image Dockerfiles (ISC publishes none)
examples/kea_dhcp/       ready-to-adapt Kea inventories
extensions/molecule/kea_dhcp/       Kea package installs on 5 distros (no init: configs validated, services not started)
extensions/molecule/kea_dhcp_container/ Kea container mode: systemd + Docker in the node, Kea 3.0 and 2.6 + ctrl-agent
extensions/molecule/kea_dhcp_ha3/   Kea 3-node HA (primary + standby + backup): starts Kea, checks states + failover
extensions/molecule/stork/          Stork server + agents next to Kea 3.0 (no auth) and 3.2 (basic auth)
tests/kea_dhcp/          render 8 Kea deployment shapes + `kea -t` in ISC 2.6/3.0/3.2 images
docs/                    stork-research, stork-kubernetes, testing, kea_dhcp-changelog-standalone
```

## Checks (all must pass before a change is done)

```bash
ansible-galaxy collection install -r requirements.yml -p ./collections
mkdir -p .molecule-collections/ansible_collections/git_cgallagher && ln -sfn ../../.. .molecule-collections/ansible_collections/git_cgallagher/isc
ansible-lint && yamllint .          # production profile, must stay at 0
tests/kea_dhcp/run.sh               # Kea render + kea -t (Docker; amd64 images)
molecule test -s kea_dhcp           # per distro in CI: --platform-name <name>
molecule test -s kea_dhcp_ha3       # 3-node HA states + failover
molecule test -s kea_dhcp_container # container mode (native-arch nodes; dockerd crashes under QEMU)
molecule test -s stork
```

Sanity needs an `ansible_collections/git_cgallagher/isc` checkout:
`ansible-test sanity --venv`. The tests reach the roles as `git_cgallagher.isc.*`
through a collections path created at run time. Never commit a directory
symlink: ansible-test's `symlinks` check rejects it, and the old
`tests/render/roles/kea_dhcp -> ../../..` link made ansible-lint recurse.

## Releasing (automated: every merge to main is released)

1. In the PR, bump `version` in `galaxy.yml` (semver) and add a
   `## <version>` entry to `CHANGELOG.md`. The **`version-bump`** check in
   `ansible-test.yml` fails any PR that changes shipped files (anything not
   in `build_ignore`, `tests/` or `extensions/molecule/`) without both. PRs that only
   touch CI, tests or `AGENTS.md` need no bump.
2. Merge. When `ansible-test` goes green on `main`, **`release.yml`**:
   - builds the collection;
   - publishes it to Galaxy if that version isn't there (secret
     `GALAXY_API_KEY` in the `galaxy` environment, which only `main` can
     deploy to);
   - creates the `v<version>` tag and GitHub release (tarball plus the
     CHANGELOG section) if they're missing.
3. `release.yml` is idempotent. It also runs **weekly** (Tue 14:00 UTC) and
   on demand (`gh workflow run release.yml`), so a failed or skipped publish
   heals itself.

**A Galaxy version can't be replaced**, only deprecated, so every fix ships
as a new version. Never push shipped-file changes straight to `main`
without a bump: the release job would see the version already published and
skip it, leaving Galaxy behind `main`.

`GALAXY_API_KEY` is an environment secret (Settings → Environments → `galaxy`)
that Chris sets. Agents never read or set it.

The manual fallback, from a clean checkout of the tag, uses
`~/.ansible/galaxy_token`:

```bash
ansible-galaxy collection build --force && ansible-galaxy collection publish git_cgallagher-isc-<version>.tar.gz
```

git_cgallagher.isc 1.0.0 was published this way on 2026-10-27.

## Conventions

- Role variables are prefixed with the role name (`kea_dhcp_`, `stork_server_`,
  `stork_agent_`, `stork_repository_`). Internal names: `kea_dhcp__*` and
  `_stork_<role>_*`.
- Roles reference each other by FQCN (`git_cgallagher.isc.<role>`).
- Booleans are read with `| bool`.
- READMEs follow Ansible conventions:
  - the collection README uses the collection-template sections;
  - each role README uses the `ansible-galaxy role init` sections.
- Never commit a real secret (workspace rule). Fixtures use obvious
  placeholders, and `tests/kea_dhcp/render/tls.json` (generated test PKI) is
  gitignored.

### kea_dhcp

- Every variable is prefixed `kea_dhcp_` (public) or `kea_dhcp__` (internal); loop vars too.
- Never assume the network: no default interfaces or subnets — assert instead.
- Kea keys are passed through hyphenated, never renamed into role variables.
- Jinja `set` inside a `for` loop does not escape the loop — accumulate with `namespace()`.
- k8s templates rely on `trim_blocks`; keep a blank line before every `---` that follows a
  `{% endif %}` or the YAML documents run together.

## ⚠️ Gotchas (each one was hit during development)

### kea_dhcp

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

- Molecule scenarios live in `extensions/molecule/<scenario>` (the layout `ansible-creator` scaffolds
  for collections). Molecule detects the collection and finds them there; run them from the repo
  root by name (`molecule test -s kea_dhcp`). `MOLECULE_PROJECT_DIRECTORY` stays the repo root.
- Container mode validates configs with `<runtime> run --network host`: `kea -t` checks that the
  configured interfaces exist, so `--network none` fails ("interface 'eth0' doesn't exist").
- Never wrap a Jinja `{% for %}` that emits text across lines inside a YAML folded scalar (`>-`):
  more-indented lines keep their newline, which split the generated `docker run` command
  ("invalid reference format"). Build such strings with filters (zip/join/map), and avoid
  `regex_replace` backreferences there too (`\\1` lost its backslash).
- Container mode tests need a NATIVE-arch test node: dockerd (Go) crashes under QEMU, so the
  `kea_dhcp_container` node is built from its Dockerfile for the host's own architecture, and the
  amd64 Kea images run inside it through binfmt (`kea_dhcp_container_platform: linux/amd64`).
- **Amazon Linux 2023 on x86-64 is the owner's primary platform (2026-10-28).** Test it first and keep its
  Molecule jobs (`kea-al2023`, `kea-al2023-min`, `kea_dhcp_ha3`, `kea_dhcp_container`) required in
  the `main protection` ruleset. EL packages name the Kea user `kea` (Debian: `_kea`).
- Amazon Linux 2023: ISC's `amzn/2023` repos exist but are EMPTY (168-byte primary index), and AL2023
  ships no kea/log4cplus. The role maps AL2023 to ISC's `el/9` repo plus an EPEL 9 repo restricted to
  `log4cplus*` (`epel-release` needs `redhat-release`, which AL2023 lacks). AL2023 minimal's `dnf` is
  `microdnf`: the bootstrap runs `microdnf swap microdnf-dnf dnf` first.
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

- Galaxy's role importer takes `galaxy_info.namespace` **verbatim** as the legacy namespace
  (`overriding namespace name via metadata`). It must be exactly `git-cgallagher`; `cgallagher`
  and `git_cgallagher` fail with "legacy namespace … does not exist". Lint accepts the hyphen.

### Stork roles

- **RPM PostgreSQL: allow `::1` as well as `127.0.0.1`.** The server's Go
  resolver dials `localhost` as `::1` when `/etc/hosts` has that entry, and
  the stock `pg_hba.conf` answers `::1` with `ident`. Only `127.0.0.1` was
  allowed until 1.4.1, so the server never started on RHEL, Rocky or AL2023.
  The Molecule server ran on Ubuntu and hid it; `stork_container` puts it on
  AL2023.
- **Amazon Linux 2023 has no podman**, only Docker (`dnf install docker`).
  Neither role installs a runtime. `runtime: auto` picks Docker there.
- **The agent runs next to Kea and identifies it by running `kea-dhcp4 -v`
  from its own filesystem.** In container and Kubernetes modes its image must
  bundle Kea's binaries; `docker/Dockerfile.stork-agent` does, with file caps
  stripped. With Kea in a container, a packaged agent on the host can't see
  Kea's binary.
- **Never put `STORK_AGENT_SERVER_URL` in agent.env.** The agent re-registers
  on every start and dies on a wildcard host. Registration is explicit;
  `/var/lib/stork-agent/root-cert.pem` is the idempotency marker.
- **Stork reads Kea API credentials from Kea's config**, preferring a
  `stork…` user. `user-file` + `password-file` work (verified with Kea 3.2.1).
  The agent needs Kea's group to read them.
- **The agent opens EVERY client's credential files**, not just the
  `stork…` client's. One missing file (for example `ha.user` absent from the
  sidecar) means "Failed to detect Kea daemon(s) … cannot read client
  credentials". That's why `kea_dhcp_k8s_extra_containers_mount_config`
  copies all of Kea's config mounts into sidecars.
- **Stork keys machines on (address, port).**
  - Re-registering at the same address reuses the entry, even with fresh
    agent state.
  - A new address (`$(POD_IP)` after a pod restart) leaves a stale entry
    that Stork keeps polling.
  - Use a stable address: the `<instance>-ha` Service in service mode; host
    mode is already stable.
- **Slow registration produces duplicate-key 500s.** When the server answers
  slowly (seen while it was still timing out against dead pods), `register`
  retries, and the retries collide with the row the first request created:
  `Cannot store machine … duplicate key`. The sidecar exits and the kubelet
  restarts it. Diagnose it from the server log; the line must not be cut at
  400 characters, because the DB error comes after the struct dump.
- **Stork's admin password policy** (2.6 default): 12+ characters, upper and
  lower case, a digit and a special character or space. `stork_server`
  reports Stork's message when it refuses one. Never reuse a test password
  that doesn't meet it.
- **ISC's Kea images are amd64-only**, and `kea_dhcp` pins pods to
  `kubernetes.io/arch: amd64`. On an arm64 test node, set
  `kea_dhcp_k8s_node_selector: {}` and install binfmt emulation first.
- **Login is `POST /api/sessions`**, not `/api/users/login`.
- **RPM versions are `2.6.0.<build>`**, so pin with globs.
- **AL2023:** use the EL9 repo, and install `shadow-utils` in an earlier
  transaction.
- **Alpine:** name each apk key `<repo>@isc-<KEYID>.rsa.pub`.
- **Podman prints "Writing manifest" even when nothing changed**, so compare
  image IDs to detect a real pull.
- Dynamic `include_tasks` don't inherit block keywords such as
  `delegate_to`; pass them with `apply:`.

## TODO / follow-ups

- Automate the Stork sidecar live test, which was done by hand in 1.4.0 (see
  `docs/testing.md`). It needs a k3s or kind job with amd64 Kea images, so an
  amd64 CI runner.
- Test the sidecar with Kea in host network mode and with Kea 3.2.
- Stable agent address for service mode **without** HA: there is no per-peer
  Service to reuse.
- Run the Stork agent's container mode under podman (`stork_container` covers
  Docker on AL2023). Nested podman
  can't exec on the dev Mac.
- Publish the Stork images (GHCR) so container and Kubernetes users don't have
  to build them.
- `kea-admin` schema management is untested against a live MySQL/PostgreSQL.
- Molecule cannot start services (no init in containers): `kea_dhcp_ha3` starts kea-dhcp4 directly, but starting Kea through systemd/OpenRC is still untested in CI.
- Possible additions: BIND 9 (Stork already monitors it); reuse
  `stork_repository` for Kea's Cloudsmith repos.
