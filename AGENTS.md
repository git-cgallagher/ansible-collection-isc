# AGENTS.md — ansible-collection-isc

Ansible collection **`git_cgallagher.isc`** (MIT) for ISC network services. It
holds the Kea roles `kea_dhcp` and `kea_dhcp_msdns`, the BIND role `bind9`, and
the Stork roles `stork_server`, `stork_agent` and `stork_repository`. Public repo `git-cgallagher/ansible-collection-isc`,
published to Galaxy as `git_cgallagher.isc`.

It **replaces** the standalone role `git-cgallagher.kea_dhcp` (repo
`ansible-role-kea-dhcp`, deleted 2026-10-31), whose full git history is merged in under
`roles/kea_dhcp`. Work on branches and PRs; `main` is protected.

⚠️ Other sessions may use `~/Code/ansible-collection-isc` at the same time:
`git checkout -b` there carries their uncommitted work onto your branch. Do
your work in a separate `git worktree` instead.

## Layout

```
roles/kea_dhcp/          Kea DHCP (packages or Kubernetes); its README is the user guide
roles/bind9/             BIND 9 authoritative server from distro packages (Kea's DDNS target)
roles/stork_*            Stork server, agent, package repository
docker/                  Stork image Dockerfiles (ISC publishes none)
examples/kea_dhcp/       ready-to-adapt Kea inventories
roles/kea_dhcp/molecule/default/    Kea package installs on 7 platforms (no init: configs validated, services not started)
roles/kea_dhcp/molecule/ha3/        Kea 3-node HA (primary + standby + backup): starts Kea, checks states + failover
roles/kea_dhcp/molecule/container/  Kea container mode: systemd + Docker in the node, Kea 3.0 and 2.6 + ctrl-agent
roles/kea_dhcp/molecule/dns/        Kea DDNS end to end: MIT KDC + BIND 9, bind9-gss-tsig and rfc2136
roles/kea_dhcp_msdns/molecule/default/  kea_dhcp_msdns on Samba AD + Kea ms-dns: kinit and GSS-TSIG key exchange
roles/kea_dhcp_msdns/molecule/windows/  real Windows Server 2022 DC + Microsoft DNS (KVM; manual windows-dc workflow)
roles/bind9/molecule/default/           BIND on 5 distros (9.16/9.18/9.20): named started in verify, TSIG update lands, unsigned refused
roles/stork_server/molecule/default/    Stork server + agents next to Kea 3.0 (no auth) and 3.2 (basic auth)
roles/stork_agent/molecule/container/   Stork on AL2023: server from packages, agent in a container next to containerised Kea
tests/kea_dhcp/          render 8 Kea deployment shapes + `kea -t` in ISC 2.6/3.0/3.2 images
docs/                    stork-research, stork-kubernetes, testing, kea_dhcp-changelog-standalone
```

## Checks (all must pass before a change is done)

```bash
# The tools at CI's versions, plus the Molecule driver and its collection (one tag for both):
pip install -c .github/ci/requirements.txt ansible-core ansible-lint yamllint molecule \
  "molecule-git-cgallagher[windows] @ git+https://github.com/git-cgallagher/ansible-collection-molecule@v0.2.1"
ansible-galaxy collection install git+https://github.com/git-cgallagher/ansible-collection-molecule.git,v0.2.1
ansible-galaxy collection install -r requirements.yml -p ./collections
mkdir -p .molecule-collections/ansible_collections/git_cgallagher && ln -sfn ../../.. .molecule-collections/ansible_collections/git_cgallagher/isc
ansible-lint && yamllint .          # production profile, must stay at 0
tests/kea_dhcp/run.sh               # Kea render + kea -t (Docker; amd64 images)
tests/argument_specs/run.sh         # every role: spec matches defaults, ansible-doc loads, bad input rejected
# Molecule runs from the role directory (scenarios live in roles/<role>/molecule/):
(cd roles/kea_dhcp && molecule test -s default)    # per platform in CI: --platform-name <name>
(cd roles/kea_dhcp && molecule test -s ha3)        # 3-node HA states + failover
(cd roles/kea_dhcp && molecule test -s dns)        # DDNS: GSS-TSIG + TSIG updates land in BIND
(cd roles/kea_dhcp && molecule test -s container)  # container mode (native-arch nodes; dockerd crashes under QEMU)
(cd roles/kea_dhcp_msdns && molecule test -s default)  # AD side (Samba) + Kea Kerberos/TKEY
(cd roles/kea_dhcp_msdns && molecule test -s windows)  # real Windows DC + Microsoft DNS (Linux+KVM only; CI: manual windows-dc workflow)
(cd roles/bind9 && molecule test -s default)       # per platform in CI: --platform-name <name>
(cd roles/stork_server && molecule test -s default)
(cd roles/stork_agent && molecule test -s container)
```

Sanity needs an `ansible_collections/git_cgallagher/isc` checkout:
`ansible-test sanity --venv`. The tests reach the roles as `git_cgallagher.isc.*`
through a collections path created at run time. Never commit a directory
symlink: ansible-test's `symlinks` check rejects it, and the old
`tests/render/roles/kea_dhcp -> ../../..` link made ansible-lint recurse.

**Argument specs.** Every role has `meta/argument_specs.yml`, and ansible-core
validates it when the role starts. A new or renamed variable in
`defaults/main.yml` needs a matching option there, with a type and
description; secrets need `no_log: true`. The `argument-specs` workflow
(`tests/argument_specs/check.py`) fails a PR that forgets. Variables starting
with `_` or containing `__` are internal and exempt.

## Releasing (automated: every merge to main is released)

1. In the PR, bump `version` in `galaxy.yml` (semver) and add a
   `## <version>` entry to `CHANGELOG.md`. The **`version-bump`** check in
   `ansible-test.yml` fails any PR that changes shipped files (anything not
   in `build_ignore`, `tests/` or `roles/*/molecule/`) without both. PRs that only
   touch CI, tests or `AGENTS.md` need no bump.
   **Docs ship too.** The job's `ignore` regex (the source of truth) skips only
   `.github/`, `roles/*/molecule/`, `tests/`, `AGENTS.md`, `.ansible-lint`,
   `.ansible-lint-ignore`, `.yamllint` and `.gitignore`. Everything else counts
   as shipped: `README.md`, `CHANGELOG.md`, `docs/`, role READMEs. So even a
   typo fix there needs a version bump and publishes a new Galaxy release.
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

- Role variables are prefixed with the role name (`kea_dhcp_`, `bind9_`,
  `stork_server_`, `stork_agent_`, `stork_repository_`). Internal names:
  `kea_dhcp__*`, `bind9__*` and `_stork_<role>_*`.
- New roles name their deployment mode `<role>_deployment` (as `kea_dhcp` and
  `bind9` do), not `<role>_deploy_mode` (the Stork roles' older name, kept for
  compatibility).
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

- Molecule scenarios live **with their role**, in `roles/<role>/molecule/<scenario>` (owner's
  choice, 2026-10-31; 1.3.1–1.6.1 used the collection-level `extensions/molecule/`). Run them from
  the role directory. `MOLECULE_PROJECT_DIRECTORY` is then the role, so each `molecule.yml` reaches
  the repo root as `${MOLECULE_PROJECT_DIRECTORY}/../..` (collections path, `requirements.yml`,
  `docker/`). A scenario that exercises several roles lives under the role it mainly tests
  (`kea_dhcp_msdns/molecule/default` also deploys `kea_dhcp`). `galaxy.yml` `build_ignore` has
  `roles/*/molecule`, so scenarios never ship to Galaxy; CI job names are unchanged, so the
  ruleset's required checks didn't change.
- ansible-lint treats `register:` names in `roles/<role>/molecule/` playbooks as role variables
  (`var-naming[no-role-prefix]`). `.ansible-lint-ignore` skips that one rule per scenario file; a new
  scenario file that registers variables needs a line there. The rule still applies to role code.
- **Every scenario runs on one driver, `molecule-git-cgallagher`** (2.0.1; repo
  `git-cgallagher/ansible-collection-molecule`). `.config/molecule/config.yml` holds what they share
  (driver, galaxy dependency, collections path, verifier, test sequence), and Molecule merges it under
  each scenario from the role directory, so a `molecule.yml` is only platforms, inventory and any
  different `test_sequence`. Platforms pick a `kind`: `docker` (the default; molecule-plugins'
  key names) or `windows_vm` (the Windows DC). A key the kind doesn't know fails the run, so check
  new keys against the driver's README. Molecule loads every scenario in a role's `molecule/` dir,
  which is why a single driver matters: the old mixed drivers made `windows-dc` install
  molecule-plugins for a scenario it never ran.
- **CI installs Molecule through the `setup-molecule` action**, pinned by SHA with a `# vX.Y.Z`
  comment (Dependabot bumps it), under `.github/ci/requirements.txt` via its `constraints` input.
  The lint job doesn't need it: ansible-lint passes without `git_cgallagher.molecule` (it doesn't
  resolve the Windows scenario's dynamic `include_role` of `ad_forest`; checked 2026-10-31 with only
  `requirements.yml`'s collections installed).
- **Merge one PR at a time and wait for its release.** `release.yml` runs after the merge's CI, then
  tags and publishes that merge commit. If another PR merges first, GITHUB_TOKEN can't tag the older
  commit (its workflows differ from main's): `gh release create` fails with HTTP 403 "Resource not
  accessible by integration". Galaxy still gets the version, but the GitHub release is lost (1.3.1,
  2026-10-28). Wait for the release run to go green before the next merge.
- **Every CI `pip install` uses `.github/ci/requirements.txt` as constraints** (2026-10-31). It
  caps ansible-core to the sanity matrix's range (`>=2.18,<2.22`) and pins the tools. Before it,
  only the two Stork Molecule jobs carried the cap (inherited from the first Stork commit), so the
  other jobs would have moved to 2.22 the day it shipped. When a new minor ships, raise the cap and
  extend the sanity and argument-specs matrices in one PR; Dependabot bumps the tool pins monthly
  but ignores ansible-core. `release.yml` and `argument-specs.yml` install their own ansible-core.
- **GSS-TSIG / AD (learned 2026-10-28):**
  - The AD account's **UPN must equal Kea's client principal**: AD only issues TGTs to UPNs. `ktpass -mapuser` does it on Windows; Samba needs `ldbmodify` (`ldb-tools`). The symptom is `GSS_TSIG_NEW_KEY_SETUP_FAILED ... bad client credentials`, and `kinit -k -t <keytab> <principal>` gives a one-line diagnosis.
  - `client-keytab` alone is enough; no credentials cache is needed.
  - Samba's internal DNS rejects Kea's signed updates (`gssapi_check_packet ... NT_STATUS_ACCESS_DENIED`), and its response TSIG fails even for `nsupdate -g`. Samba with BIND9_DLZ couldn't decrypt AES-256 tickets (exportkeytab omits AES-256 for the DNS principal). So signed updates are tested against MIT KDC + BIND (`kea_dhcp_dns`), and AD/Kerberos against Samba (`kea_dhcp_msdns`).
  - **Microsoft DNS (real Windows Server 2022, learned 2026-10-28):**
    - Kea can't verify the GSS-TSIG signature on Microsoft DNS's error responses (`GSS_TSIG_VERIFY_FAILED ... Packet was replayed in wrong direction`, then `..._RESP_CORRUPT`). A first update for a new name works; one whose prerequisite fails doesn't. So the `ms-dns` preset uses `no-check-with-dhcid` (no prerequisites).
    - `win_powershell` reports `changed` unless the script sets `$Ansible.Changed = $false`, and in check mode it skips a script that doesn't declare `SupportsShouldProcess` (reporting `changed`). Since 2.2.0 only `ktpass` is a script: the account is `microsoft.ad.user` (`update_password: on_create` is mandatory, the default `always` would reset the password every run, bump the key version and invalidate Kea's keytab) and the zones are `ansible.windows.win_dns_zone` (lower-case `dynamic_update`; the argument spec keeps `Secure`/`NonsecureAndSecure`).
    - `no_log` also censors the error. The ktpass task registers with `failed_when: false` and fails in a following assert that shows the PowerShell error with the password masked. The modules no_log the password themselves and fail normally.
    - The domain's password complexity rejects a password containing the account name (`kea`).
    - `kea_dhcp_msdns/molecule/windows` runs only on Linux with `/dev/kvm` (the GitHub runner), not on a Mac. It reaches the DC through QEMU user-mode port forwards on 127.0.0.1 (5985, 15353→53, 18088→88), so Kea's config uses `servers[].port` and `kdcs: ['127.0.0.1:18088']`.
  - Keytabs are binary: in Kubernetes they go through `slurp` into the Secret's `data`, never `stringData` or text lookups.
  - Presets live in `vars/dns/<integration>.yml` as one internal dict, `kea_dhcp__dns_preset`, so it never outranks `kea_dhcp_dns`.
- Test nodes: `debian:12` has no `pgrep` (install `procps`); AL2023 has no `setsid` (use Ansible async); `dig` segfaults under QEMU (query from a native node).
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
  Molecule jobs (`kea-al2023`, `kea-al2023-min`, `kea_dhcp_ha3`, `kea_dhcp_container`, from 1.5.0 `kea_dhcp_dns`, `kea_dhcp_msdns`, and from 2.1.0 `molecule bind9 (bind9-al2023)`) required in
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

### bind9

- The distros put BIND in different places, and AppArmor (Debian/Ubuntu) or SELinux (EL) only lets
  `named` write in some of them. Zones that take updates live in `/var/lib/bind`,
  `/var/named/dynamic` or `/var/bind/dyn` (`vars/os/<family>.yml`, each path checked in a container,
  2026-11-01). Containers have no AppArmor or SELinux, so Molecule can't catch a dynamic zone placed
  elsewhere; on a real host its journal writes would be denied.
- The role writes primary zone files only when missing (`force: false`): once BIND has journalled
  dynamic updates, rewriting the file would lose them or clash with the journal.
- EL's `named.service` sets `KRB5_KTNAME=/etc/named.keytab`, so the role uses that path for the
  GSS-TSIG keytab there.
- Alpine's init script is in `bind-openrc`, not `bind`; it reads `/etc/bind/named.conf` and the
  pid file from the config.
- Docker Desktop on the dev Mac quit while five amd64 containers were installing BIND in parallel
  under emulation (2026-11-01; the cause isn't confirmed). Run local Molecule platforms one at a time.

### Stork roles

- **RPM PostgreSQL: allow `::1` as well as `127.0.0.1`.** The server's Go
  resolver dials `localhost` as `::1` when `/etc/hosts` has that entry, and
  the stock `pg_hba.conf` answers `::1` with `ident`. Only `127.0.0.1` was
  allowed until 1.4.1, so the server never started on AL2023 (seen there; EL
  hosts have the same `::1 localhost` entry, unconfirmed).
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
- **`stork_server` has secure defaults since 2.0.0** (PR #15): it fails
  at the input check unless `stork_server_admin_password` is set (and differs
  from the bootstrap `admin`), and Kubernetes mode also needs
  `stork_server_k8s_api_url` so the rotation can't be skipped silently. The
  k8s password change verifies the API's certificate
  (`stork_server_k8s_api_validate_certs`, `stork_server_k8s_api_ca_path`).
  Every scenario, example and live test that deploys the server must set a
  password; `stork_server_allow_bootstrap_admin: true` is the explicit opt-out
  (manual rotation or OIDC), not a test shortcut.
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

- Re-run the manual `windows-dc` workflow after changes to `kea_dhcp_msdns`, the `ms-dns` preset or the DDNS templates; `gh run list --workflow windows-dc.yml --repo git-cgallagher/ansible-collection-isc` shows when it last passed. It's untested on Windows Server 2025 and on a real multi-DC domain.
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
- `bind9`: replace the hand-written BIND setup in `roles/kea_dhcp/molecule/dns/prepare.yml` with the
  role, so its GSS-TSIG keytab path is tested end to end (today only TSIG updates are).
- `bind9`: Stork monitoring. Check how the Stork agent finds BIND (process, rndc key, statistics
  channel) before adding anything for it.
- `bind9`: not yet supported: DNSSEC signing, catalog zones, views, ISC's own packages, container and
  Kubernetes modes. Starting `named` through systemd/OpenRC is untested in CI (as for Kea).
- Possible addition: reuse `stork_repository` for Kea's Cloudsmith repos.
