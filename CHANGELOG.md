# Changelog

## 2.2.1 — 2026-11-01

`kea_dhcp_msdns` Windows backend, fixes from the review of 2.2.0:

- **Fix: an existing service account outside the OU was not found.** The
  `microsoft.ad.user` task had no `identity`, so the module only looked at
  `CN=<account>` under `kea_dhcp_msdns_service_account_ou` (or Users). On a
  domain where the account already existed elsewhere it would have tried to
  create a second one and failed. It now finds the account by sAMAccountName
  and moves it into the OU when one is set, which is what 2.2.0's notes
  claimed. The Molecule `windows` scenario pre-creates the account in Users and
  checks that converge moves it.
- **New `kea_dhcp_msdns_zone_replication`** (`Domain`, `Forest` or `Legacy`;
  default `Domain`, which 2.2.0 hard-coded). `win_dns_zone` applies the scope to
  existing zones on every run, so a pre-existing zone in another scope is
  converted and a file-backed zone fails. The 2.1 script never touched an
  existing zone's scope. Set the variable to the scope your zones use.
- `.claude/worktrees/` is gitignored.

## 2.2.0 — 2026-11-01

`kea_dhcp_msdns` Windows backend: the service account and the zones are now
managed by modules instead of `win_powershell` scripts
([#21](https://github.com/git-cgallagher/ansible-collection-isc/issues/21)).

- **`microsoft.ad.user`** creates the account, sets its UPN and SPN, and adds
  it to DnsUpdateProxy, with `update_password: on_create`: the password is only
  set when the account is created (and by `ktpass` when a keytab is produced),
  so a run never bumps the key version of a keytab Kea already has. Check mode
  and diff work; a failure is reported directly (the module keeps the password
  out of its output), so the `no_log` + `failed_when: false` + assert
  workaround is gone. One behaviour change: with
  `kea_dhcp_msdns_service_account_ou` set, an existing account in another OU is
  moved there (the script only used the OU at creation).
- **`ansible.windows.win_dns_zone`** creates the forward and reverse zones
  (primary, domain replication) and converges their dynamic-update setting,
  with check mode and diff. `kea_dhcp_msdns_dynamic_update` keeps its values
  (`Secure`, `NonsecureAndSecure`); the role lower-cases them for the module.
- `ktpass` stays a `win_powershell` task: it only takes the password on its
  command line. In check mode the script is skipped and reported as a change.
- `requirements.yml`: `ansible.windows` >= 2.6.0 (`win_dns_zone`), new
  `microsoft.ad` >= 1.6.0. Both are soft dependencies, only needed on a Windows
  DC. The Molecule `windows` scenario and the `windows-dc` workflow install them
  from `requirements.yml`; `git_cgallagher.molecule` already depends on both.
- The Molecule `windows` scenario waits, after the DC's promotion reboot, for
  the domain zone's replication scope to leave its transient `Legacy` state:
  `win_dns_zone` can't update a zone in that state.

## 2.1.0 — 2026-11-01

- **New role `bind9`:** ISC BIND 9 as an authoritative server, from the
  distro's packages (Debian/Ubuntu, EL/Fedora/Amazon Linux 2023, Alpine). It
  writes `named.conf`, TSIG keys, the GSS-TSIG keytab, update policies and
  primary, secondary or forward zones. Primary zone files are seeded once and
  then left to dynamic updates. Every config is checked with `named-checkconf`
  / `named-checkzone` before it's installed. It has no default listen
  addresses or zones (it asserts), and recursion is off unless
  `bind9_allow_recursion` is set. Optional rndc key and statistics channels.
- New Molecule scenario `roles/bind9/molecule/default` (AL2023, Rocky 9,
  Debian 12, Ubuntu 24.04, Alpine 3.22: BIND 9.16, 9.18, 9.20): zones answer,
  a TSIG-signed update lands, an unsigned one is refused, rndc and the
  statistics channel respond. CI job `molecule bind9 (<platform>)`.

## 2.0.1 — 2026-10-31

No role behaviour changes.

- **Molecule scenarios run on the shared `molecule-git-cgallagher` driver**
  ([`git_cgallagher.molecule`](https://github.com/git-cgallagher/ansible-collection-molecule)
  0.2.0) instead of molecule-plugins' docker driver, and the Windows DC
  scenario's own create/destroy (290 lines) is gone. What the scenarios share is
  in `.config/molecule/config.yml`; each `molecule.yml` keeps its platforms and
  inventory. CI installs it all with the driver's `setup-molecule` action, still
  under `.github/ci/requirements.txt`, which no longer pins `molecule-plugins`
  or the `docker` SDK.
- `galaxy.yml` `build_ignore` now lists `.config`, so that base config stays out
  of the Galaxy tarball. That's why this is a release.
- The Windows DC scenario keeps its box cache and VM disk in `$MOLECULE_LAB_DIR`
  (was `$KEA_LAB_DIR`).

## 2.0.0 — 2026-10-31

Secure defaults for `stork_server`. **Breaking:** plays that relied on the old
defaults now fail at the input check, with a message saying what to set.

- **`stork_server_admin_password` is required.** Before, an empty password left
  Stork on `admin`/`admin`, listening on every interface over plain HTTP by
  default. The role now fails unless the password is set (and differs from
  `stork_server_admin_bootstrap_password`). Set the new
  `stork_server_allow_bootstrap_admin: true` to keep the old behaviour, for
  example when the password is changed by hand or logins use OIDC.
- **Kubernetes mode requires `stork_server_k8s_api_url`** (unless
  `stork_server_allow_bootstrap_admin` is true, the state is `absent`, or
  `stork_server_k8s_apply` is false), so the rotation can't be skipped
  without anyone noticing.
- **The Kubernetes password change checks the API's TLS certificate.** It used
  to send both admin passwords to `stork_server_k8s_api_url` with certificate
  checks off. New `stork_server_k8s_api_validate_certs` (default `true`) and
  `stork_server_k8s_api_ca_path` (a private CA bundle). A self-signed ingress
  now needs the CA, or `stork_server_k8s_api_validate_certs: false`. Package
  mode still skips the check, because its call only goes to `127.0.0.1`.
- **`requires_ansible` is now `>=2.18.0`** (was `>=2.16.0`). CI has only
  tested 2.18–2.21, and ansible-core 2.16 and 2.17 are end of life.

## 1.6.2 — 2026-10-31

No role behaviour changes.

- **Molecule scenarios moved back under their roles**, from
  `extensions/molecule/<scenario>` to `roles/<role>/molecule/<scenario>`. Run
  them from the role's directory, for example
  `cd roles/kea_dhcp && molecule test -s ha3`.

  | Was | Now |
  |---|---|
  | `kea_dhcp` | `roles/kea_dhcp/molecule/default` |
  | `kea_dhcp_ha3` | `roles/kea_dhcp/molecule/ha3` |
  | `kea_dhcp_container` | `roles/kea_dhcp/molecule/container` |
  | `kea_dhcp_dns` | `roles/kea_dhcp/molecule/dns` |
  | `kea_dhcp_msdns` | `roles/kea_dhcp_msdns/molecule/default` |
  | `kea_dhcp_msdns_windows` | `roles/kea_dhcp_msdns/molecule/windows` |
  | `stork` | `roles/stork_server/molecule/default` |
  | `stork_container` | `roles/stork_agent/molecule/container` |

  `galaxy.yml` `build_ignore` now lists `roles/*/molecule`, so the scenarios
  still aren't in the Galaxy tarball. CI check names are unchanged.

## 1.6.1 — 2026-10-28

Fixes found by running `ms-dns` against a real Windows Server 2022 domain
controller for the first time.

- **`kea_dhcp` `ms-dns` preset:** `ddns-conflict-resolution-mode` is now
  `no-check-with-dhcid` (was `check-exists-with-dhcid`). Kea can't verify the
  GSS-TSIG signature on Microsoft DNS's error responses
  (`GSS_TSIG_VERIFY_FAILED … Packet was replayed in wrong direction`). So any
  update that carries prerequisites failed as soon as the name already existed,
  for example a client moving to a new address. Kea still writes DHCID
  records. Set the mode in `kea_dhcp_dns.dhcp_ddns_params` to override it.
- **`kea_dhcp_msdns` (Windows backend):**
  - The account and zone tasks reported `changed` on every run, because
    `win_powershell` defaults to changed. They now report a change only when
    they make one.
  - A failure in the service-account or `ktpass` task now shows the PowerShell
    error with the password masked, instead of a censored result. For example,
    domain complexity rejects a password that contains the account name.
  - `ktpass` output is captured instead of discarded.
- New Molecule scenario **`kea_dhcp_msdns_windows`** and manual workflow
  **`windows-dc`**. They boot a Windows Server 2022 DC with Microsoft DNS under
  QEMU/KVM on the GitHub runner. The scenario runs `kea_dhcp_msdns`'s Windows
  backend, deploys Kea on AL2023 x86-64, and reads the A and PTR records from
  Kea's GSS-TSIG updates back out of Microsoft DNS.

## 1.6.0 — 2026-10-28

- **`stork_server`, `stork_agent`, `stork_repository`**: new
  `meta/argument_specs.yml`. ansible-core now validates their variables when
  the role starts, as it already did for `kea_dhcp`, and `ansible-doc -t role`
  documents them. A value of the wrong type or outside its choices now fails
  at the start of the run instead of partway through, for example
  `stork_agent_port: abc` or `stork_server_deploy_mode: helm`. Passwords and
  tokens are `no_log`.
- New workflow **`argument-specs`** (`tests/argument_specs/run.sh`, on
  ansible-core 2.18 and 2.21), covering every role, `kea_dhcp` and
  `kea_dhcp_msdns` included. It
  fails when:
  - a default has no spec option, or a spec option has no default;
  - a literal default doesn't match its declared type, list elements or
    choices;
  - a password, token or secret option isn't `no_log`;
  - `ansible-doc` can't load the role;
  - the role accepts a bad value at runtime.
## 1.5.0 — 2026-10-28

- **`kea_dhcp`: DNS integrations.** `kea_dhcp_dns_integration: none | ms-dns |
  bind9-gss-tsig | rfc2136` loads a provider preset (`vars/dns/`) under
  `kea_dhcp_dns`, which you can override. Anything but `none` enables
  `kea-dhcp-ddns`. The role generates:
  - the DDNS daemon's forward and reverse domains from one `servers` list;
  - TSIG keys for `rfc2136`;
  - ISC's GSS-TSIG hook for the Kerberos providers (`isc-kea-gss-tsig`, a
    keytab, and a Kea-only `krb5.conf` passed through `KRB5_CONFIG`, so the
    host's `/etc/krb5.conf` is untouched), in package, container and
    Kubernetes mode. In Kubernetes the binary keytab goes into the Secret's
    `data`.
  - The DHCP-side policy comes from the preset; `ms-dns` overrides client
    updates and uses `check-exists-with-dhcid`.
- **New role `kea_dhcp_msdns`** prepares Active Directory / Microsoft DNS:
  service account with UPN equal to the client principal, SPN,
  DnsUpdateProxy, zones, and a keytab fetched to a controller path. Windows
  (PowerShell + ktpass) and Samba AD backends.
- New Molecule scenarios, also run in CI:
  - `kea_dhcp_dns`: signed GSS-TSIG and TSIG updates land in BIND 9 behind
    an MIT KDC, including a client moving to a new address.
  - `kea_dhcp_msdns`: the companion role on Samba AD, then Kea's `kinit`
    and GSS-TSIG key exchange with the DC.
  - The Windows backend and Microsoft DNS's own GSS-TSIG verifier aren't
    covered by CI.
- Render tests cover all three integrations with `kea -t` on Kea 3.0 and 3.2.

## 1.4.1 — 2026-10-28

Stork on Amazon Linux 2023, including next to Kea in containers.

- **`stork_server`**: fixed the local PostgreSQL on RPM hosts. On Amazon
  Linux 2023 the server never started: "Ident authentication failed for user
  stork". RHEL and Rocky have the same `::1 localhost` entry and the same
  stock `pg_hba.conf`, so they're likely affected too (unconfirmed).
  The server dials `localhost` as `::1` when `/etc/hosts` lists it,
  and the role had only allowed password auth on `127.0.0.1`. Both loopback
  addresses are allowed now. CI hadn't caught it because the Molecule server
  ran on Ubuntu.
- **`stork_agent`**: in container mode, missing `stork_agent_container_kea_mounts`
  paths are created as empty directories. Podman refuses a missing bind
  source, and Kea logging to stdout leaves no `/var/log/kea`.
- New Molecule scenario `stork_container`, also run in CI:
  - the Stork server from packages on Amazon Linux 2023, with a local
    PostgreSQL 16;
  - `kea_dhcp` in container mode (Kea 3.0.4) on an Amazon Linux 2023 node
    with its own Docker engine;
  - `stork_agent` in container mode next to it.

  Stork monitors the daemon, and the idempotence run changes nothing.

## 1.4.0 — 2026-10-28

Fixes from the first live run of a Stork agent sidecar inside `kea_dhcp`
pods (k3s, hot-standby pair). See
[docs/stork-kubernetes.md](docs/stork-kubernetes.md).

- **`kea_dhcp`**: new `kea_dhcp_k8s_extra_containers_mount_config`. It
  defaults to `kea_dhcp_k8s_share_process_namespace`. It gives every extra
  container the Kea containers' config mounts (config files, API credential
  files, `kea_dhcp_files`) at the same paths. The Stork agent opens all of
  them: it reads **every** API client's credential files, not only the
  `stork…` client's.
- **`kea_dhcp`**: in service network mode, each peer's `<instance>-ha`
  Service also exposes the extra containers' TCP ports. A sidecar can then
  register under that stable name instead of a pod IP. A pod IP leaves a
  stale Stork machine behind on every restart.
- **`stork_agent`**: `stork_agent_k8s_volume_mounts` now defaults to `[]`.
  The old default, a directory mount of `config` at `/etc/kea`, never matched
  `kea_dhcp`'s per-file `subPath` layout. If you used the default with
  another Kea pod that has a `config` volume at `/etc/kea`, set it
  explicitly.
- **`stork_agent`**: new `stork_agent_k8s_create_namespace` (default `true`).
  It creates Kea's namespace before writing the token Secret. Before, the
  documented order (agent role, then Kea role) failed on a fresh cluster with
  `namespaces "kea-dhcp" not found`.
- **`stork_server`**: a refused `stork_server_admin_password` now fails with
  Stork's reason, for example "password must include at least one special
  character or whitespace", instead of a censored HTTP 400. Stork's default
  policy is 12+ characters with upper and lower case, a digit and a special
  character or space.
## 1.3.2 — 2026-10-28

- Amazon Linux 2023 on x86-64 is now the primary tested platform for `kea_dhcp`:
  - The 3-node HA scenario (`kea_dhcp_ha3`) runs on `amazonlinux:2023-minimal`
    nodes (x86-64).
  - The container-mode scenario's test nodes are Amazon Linux 2023 with
    systemd and AL2023's own `docker` package.
  - The AL2023 Molecule jobs are required checks for merging.
- Docs and examples lead with Amazon Linux 2023: quick start, the
  supported-platforms table, and the `vm-ha3` and `package-ha` inventories
  (NIC `ens5`). No role changes.

## 1.3.1 — 2026-10-28

- Molecule scenarios moved from `molecule/` to `extensions/molecule/`, the
  layout `ansible-creator` scaffolds for collections, which Molecule expects.
  Run them from the repo root as before (`molecule test -s <scenario>`). No
  role changes; the published collection's contents are unchanged apart from
  docs.

## 1.3.0 — 2026-10-28

- **`kea_dhcp`**: new deployment mode `container`. It runs ISC's Kea images on
  the host with Podman or Docker, one systemd unit per daemon, with host
  networking.
  - Configs are validated with `kea -t` inside the image before they're
    installed, then bind-mounted read-only at the same paths.
  - Leases stay on the host. On 2.6, the control agent shares the socket
    directory with Kea.
  - Images are pulled on every run; units restart only when an image ID,
    config or unit changes.
  - New variables: `kea_dhcp_container_runtime`, `_pull`, `_platform`,
    `_run_dir`, `_volume_options`, `_extra_args`.
  - New Molecule scenario `kea_dhcp_container` (Kea 3.0, and 2.6 with the
    control agent), also run in CI.

## 1.2.0 — 2026-10-28

- **`kea_dhcp`**: Amazon Linux 2023 support, including the minimal image, on
  x86_64 and arm64.
  - ISC's `amzn/2023` repositories are empty, so the role uses ISC's EL9 RPMs.
    It adds EPEL 9 restricted to `log4cplus`, because Amazon doesn't support
    `epel-release`. New variable `kea_dhcp_isc_repo_rpm_release` overrides the
    repo path (`el/9`, `fedora/42`…).
  - Python bootstrap fixed for hosts where `dnf` is really `microdnf`
    (AL2023 minimal): it swaps in real `dnf` first.
  - Creates the Kea user when the packages couldn't (no systemd, so no
    `systemd-sysusers`).
  - Molecule and CI cover `amazonlinux:2023` and `amazonlinux:2023-minimal`.

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
