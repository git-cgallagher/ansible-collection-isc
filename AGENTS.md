# AGENTS.md — ansible-collection-stork

Ansible collection **`git_cgallagher.stork`**: ISC Stork server + agent.
**Kea is out of scope.** The collection pairs with any Kea role; the usual
companion is `~/Code/ansible-role-kea-dhcp` (`kea_dhcp`). Read
`README.md`, then `docs/research.md`, which holds the verified facts the
design rests on.

Published on Galaxy as `git_cgallagher.stork`. The GitHub repo
`git-cgallagher/ansible-collection-stork` is public, with secret scanning and
push protection.

## Commands

```bash
ansible-galaxy collection install -r requirements.yml -p ./collections
mkdir -p .molecule-collections/ansible_collections/git_cgallagher && ln -sfn ../../.. .molecule-collections/ansible_collections/git_cgallagher/stork
molecule test                     # Stork server + agents next to Kea 3.0 and 3.2 (basic auth)
ansible-lint && yamllint .        # production profile, must stay at 0
```

Sanity runs from an `ansible_collections/git_cgallagher/stork` checkout:
`ansible-test sanity --venv`.

## Releasing (automated: every merge to main is released)

1. In the PR, bump `version` in `galaxy.yml` (semver) and add a
   `## <version>` entry to `CHANGELOG.md`. The **`version-bump`** check in
   `ansible-test.yml` fails any PR that changes shipped files (anything not
   in `build_ignore`, `tests/` or `molecule/`) without both. PRs that only
   touch CI, tests or `AGENTS.md` need no bump.
2. Merge. When `ansible-test` goes green on `main`, **`release.yml`**:
   - builds the collection;
   - publishes it to Galaxy if that version isn't there (secret
     `GALAXY_API_KEY`);
   - creates the `v<version>` tag and GitHub release (tarball plus the
     CHANGELOG section) if they're missing.
3. `release.yml` is idempotent. It also runs **weekly** (Tue 14:00 UTC) and
   on demand (`gh workflow run release.yml`), so a failed or skipped publish
   heals itself.

**A Galaxy version can't be replaced**, only deprecated, so every fix ships
as a new version. Never push shipped-file changes straight to `main`
without a bump: the release job would see the version already published and
skip it, leaving Galaxy behind `main`.

`GALAXY_API_KEY` is a repo Actions secret that Chris sets. Agents never read
or set it.

The manual fallback, from a clean checkout of the tag, uses
`~/.ansible/galaxy_token`:

```bash
ansible-galaxy collection build --force && ansible-galaxy collection publish git_cgallagher-stork-<version>.tar.gz
```

1.0.0 was published this way on 2026-10-27, from commit `680bc20`.

## Conventions

- Role variables are prefixed with their role name (`stork_server_*`,
  `stork_agent_*`, `stork_repository_*`). Internal facts and registers start
  with `_<role>_`.
- Roles reference each other by FQCN (`git_cgallagher.stork.stork_repository`).
- Booleans are always read with `| bool`.
- READMEs follow Ansible conventions:
  - The collection README uses the collection-template sections (Description,
    Tested with, External requirements, Included content, Using this
    collection, Release notes, More information, Licensing).
  - Each role README uses the `ansible-galaxy role init` sections
    (Requirements, Role Variables, Dependencies, Example Playbook, License,
    Author Information).

## ⚠️ Gotchas (each one was hit during development)

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

- `kea_dhcp` needs a `shareProcessNamespace` switch before the sidecar works
  in its pods (docs/kubernetes.md). Then add a live k8s integration test
  against it.
- Run container mode end to end on a real VM; nested podman can't exec on the
  dev Mac.
- Publish the multi-arch images (GHCR) so container and Kubernetes users don't
  have to build them.
- The Kea findings from the old all-in-one role (AL2023 log4cplus, Kea binary
  caps/permissions, socket-dir rules, HA in Kubernetes) belong in `kea_dhcp`.
  They are in this repo's git history, commit `c427689`.
