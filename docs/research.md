# Research notes: ISC Kea + Stork (as of 2026-10-27)

Everything marked **verified** was reproduced in a container on 2026-10-27
during development of this role. The rest comes from ISC docs or mailing
lists, cited inline.

## Versions to deploy

| Component | Line | Status | Notes |
|---|---|---|---|
| Kea | **3.0.x** (3.0.4) | LTS, EOL 2028-06 | Default here (`kea_branch: "3-0"`) |
| Kea | 3.2.x | Current stable, EOL 2027-07 | `kea_branch: "3-2"`. The Control Agent is gone. |
| Kea | 2.6 and older | EOL | Not supported by this role |
| Stork | **2.6.0** | Stable (even minor) | Released 2026-10-09; in the `stork` repo |
| Stork | 2.4.x | Previous stable | First line with direct Kea API support (no CA) |
| Stork | 2.5.x | Development (odd minor) | `stork-dev` repo; not for production |

ISC's Cloudsmith repos are named after the branch: `kea-3-0`, `kea-3-2`,
`kea-dev`, `stork`, `stork-dev`. Subscriber repos append `-prv` and need a
token ([ISC KB: Kea packages](https://kb.isc.org/docs/isc-kea-packages)).

## Changes in Kea 3.x that shape the design

1. **The Control Agent (`kea-ctrl-agent`) is deprecated in 3.0 and removed in
   3.2** ([ISC KB: CA migration](https://kb.isc.org/docs/kea-control-agent-migration)).
   Each daemon now serves its own HTTP(S) API through a `control-sockets`
   list (note the plural). This role never installs the CA. It gives each
   daemon a unix socket plus an HTTP listener on `127.0.0.1` (4: 8004,
   6: 8006, DDNS: 8053).
2. **Most hooks went open source in 3.0**, including HA and lease_cmds. Only
   RBAC and the Configuration Backend stay commercial
   ([ISC KB](https://kb.isc.org/docs/things-to-be-aware-of-when-upgrading-to-kea-300)).
   `isc-kea-hooks` from the public repo is all HA needs.
3. **Hooks load only from the compiled-in hooks directory (since 2.7.9), and
   bare names are accepted.** **Verified:** `"library": "libdhcp_ha.so"`
   validates on AL2023 (`/usr/lib64/kea/hooks`), Debian
   (`/usr/lib/x86_64-linux-gnu/kea/hooks`) and the Alpine images
   (`/usr/lib/kea/hooks`). So one config template serves every platform.
4. **Path restrictions.** **Verified:** a unix socket under `/run/kea` is
   rejected: *"supported path is '/var/run/kea'"*. The socket directory must
   also be mode `0750` or stricter, so a 0777 Kubernetes `emptyDir` fails
   until it is chmod'ed.

## High availability

- Two hooks, in this order: `libdhcp_lease_cmds.so`, then `libdhcp_ha.so`.
- Modes: `hot-standby` (primary + standby), `load-balancing` (primary +
  secondary), `passive-backup` (primary + backups). Any mode can add
  `backup` peers. `passive-backup` rejects `heartbeat-delay`,
  `max-unacked-clients` and `max-rejected-lease-updates`.
- With HA+MT (`multi-threading.http-dedicated-listener: true`), HA traffic
  gets its own listener. It must use a different port from the control API
  (8001 for v4 and 8002 for v6 here).
- **Peer URLs must be IP literals.** Kea does not resolve names, by design
  ([kea#2775](https://gitlab.isc.org/isc-projects/kea/-/issues/2775),
  [kea-users 2021-12](https://lists.isc.org/pipermail/kea-users/2021-December/003287.html)).
- **Verified: the dedicated listener binds the host from this server's own
  peer URL.** An address the host doesn't own fails with `bind: Cannot assign
  requested address`.
- **Verified: peer URLs don't have to match across servers.** Server A can
  list itself as `http://0.0.0.0:8001/` and B at B's real IP, while B does the
  mirror image. The pair reached `hot-standby` in about 6 s. This is what makes
  Kubernetes work (see below).
- **Verified: failover needs client traffic with the default settings.**
  With `max-unacked-clients: 5`, a standby whose primary has died stays in
  `hot-standby` and marks the partner `unavailable`. It moves to
  `partner-down` only after it sees DHCP clients going unanswered. This guards
  against split-brain when only the HA link is cut. Tests that have no clients
  set it to `0`.
- TLS: `trust-anchor`, `cert-file` and `key-file` are all-or-none.
  `require-client-certs` defaults to true. Use mutual TLS whenever peers
  aren't on a trusted L2.

## Packaging matrix (verified 2026-10-27)

| Platform | Repo path | Daemon user | Kea service names | Notes |
|---|---|---|---|---|
| Debian 12 / Ubuntu | `deb/<debian\|ubuntu> <codename>` | `_kea` | `isc-kea-dhcp4-server`, … | apt reads `.asc` keys directly, so gnupg isn't needed |
| RHEL/Rocky/Alma 8–10 | `rpm/el/<major>` | `kea` | `kea-dhcp4`, … | Needs **log4cplus from EPEL** |
| Fedora | `rpm/fedora/<ver>` | `kea` | `kea-dhcp4`, … | log4cplus is in Fedora |
| **Amazon Linux 2023** | `rpm/el/9` | `kea` | `kea-dhcp4`, … | See below |
| Alpine 3.21+ | `alpine/v<x.y>/main` | `kea` | `kea-dhcp4` (OpenRC) | See below |

**Amazon Linux 2023** has no ISC repo, and the EL9 RPMs fail with *"nothing
provides liblog4cplus-2.0.so.3"*. AL2023 doesn't support EPEL as a whole, but
an EPEL 9 repo restricted to `includepkgs=log4cplus` installs log4cplus
2.0.5. After that, Kea 3.0.4 and Stork 2.6.0 install and run (verified,
aarch64). There is also a trap: **`shadow-utils` must be installed in an
earlier transaction.** The Kea and Stork `%pre` scriptlets call
`groupadd`/`useradd`. If shadow-utils arrives in the same `dnf` transaction,
Stork fails outright, and Kea installs without creating the `kea` user, which
its unit files (`User=kea`) then need.

**Alpine.** Each Cloudsmith repo signs its index with its own RSA key, and the
key must be saved as `<repo>@isc-<KEYID>.rsa.pub`. apk picks the key by
**file name**, so any other name gives *UNTRUSTED signature*. The generic
`/rsa.key` URL serves the PGP key, not the RSA one.

**Version pins.** Stork's RPM version is `2.6.0.261009212500`, so `-2.6.0`
doesn't match. The role pins with a glob (`-2.6.0*` for dnf, `=2.6.0*` for
apt, `~2.6.0` for apk).

## Container images

- ISC publishes `docker.cloudsmith.io/isc/docker/kea-dhcp4|kea-dhcp6|kea-dhcp-ddns:<ver>`
  (Alpine-based). In 3.x each image runs a single process, as root, with no
  supervisor and no CA.
- **They are amd64-only** (no arm64 manifest, verified), so they won't run on
  Graviton EKS nodes or ARM Talos nodes. `files/Dockerfile.kea` builds a
  multi-arch equivalent from ISC's Alpine packages.
- **Binary permissions.** The daemons are `0754 kea:kea`, and `kea-dhcp4` has
  file capabilities `cap_net_bind_service,cap_net_raw=ep` (verified in ISC's
  image and the Alpine packages). Two consequences:
  - With every capability dropped, root can't exec them, because it lacks
    DAC_OVERRIDE. The role runs Kea as uid 0 with primary gid 101 (`kea`).
  - Exec fails with EPERM unless `NET_RAW` and `NET_BIND_SERVICE` stay in the
    bounding set, **even in UDP-only mode**. So the role drops every default
    capability except those two, and does not `drop: [ALL]`. Both are runtime
    defaults, so this still passes Pod Security "baseline".
- **ISC publishes no Stork images.** `files/Dockerfile.stork-agent` and
  `Dockerfile.stork-server` build them from the Alpine packages.

## Stork

- The server is one Go binary and needs PostgreSQL ≥ 10 with `pgcrypto`.
  Stork's availability is its database's: run one server against an HA
  PostgreSQL.
- The agent runs **next to Kea**. It finds daemons by scanning `/proc`, reads
  the config path from Kea's command line, opens the config to find the
  control sockets, and then uses the HTTP socket. Stork 2.4+ needs no CA
  ([kea-users 2026-04](https://lists.isc.org/pipermail/kea-users/2026-April/006049.html)).
  **Verified:** Stork 2.6.0 discovered Kea 3.0.4 `dhcp4` through
  `127.0.0.1:8004` on AL2023, Debian 12 and Rocky 9.
- **Verified:** the agent also runs `/usr/sbin/kea-dhcp4 -v` *from its own
  filesystem* to identify the daemon. A Kubernetes sidecar without Kea
  binaries logs *"Failed to detect Kea daemon(s)"*, so the agent image bundles
  them. For the same reason, when Kea runs **in a container on a host**, a
  packaged agent on that host can't identify it. The role therefore runs the
  agent containerised in container mode as well (`--pid host`, verified with
  a shared PID namespace).
- The bundled copies are 0754 with file caps, like the originals.
  `Dockerfile.stork-agent` strips the caps (`setcap -r`) and makes them 0755,
  because the agent only runs them with `-v`. The sidecar then needs nothing
  beyond SYS_PTRACE.
- **Registration.** `stork-agent register --non-interactive --server-url …
  --agent-host … [--server-token …]`:
  - With the server token, the machine is authorized at once.
  - Without it, someone approves it in the UI (Services → Machines →
    Unauthorized).
  - It writes `/var/lib/stork-agent/{root-cert.pem,server-cert.pem,server-key.pem,token.txt}`.
  - Its last step binds a ping listener on `--agent-host`. Behind a k8s
    Service address that bind fails, but only after the certs are stored.
- **Verified:** if `STORK_AGENT_SERVER_URL` is in `agent.env`, the agent tries
  to (re)register on every start and exits fatally when `STORK_AGENT_HOST` is
  `0.0.0.0` (*"agent host address is not provided"*). The role registers
  explicitly and leaves that variable out.
- API used by the role (verified on 2.6.0):
  - `POST /api/sessions {authenticationMethodId: internal, identifier, secret}`
    returns the user, including `id` and `changePassword`.
  - `GET /api/machines-server-token` returns `{token}`.
  - `PUT /api/users/{id}/password {oldpassword, newpassword}`.
  - The bootstrap login is `admin`/`admin`.
- `/metrics` on the server has **no authentication**; firewall it.
- The agent exposes a Prometheus Kea exporter on :9547.

## Kubernetes specifics

- DHCP broadcasts never reach pod networks, so Kubernetes serves **relayed
  DHCP only** (`dhcp-socket-type: udp`). Relays unicast to a LoadBalancer IP.
  Kea replies to `giaddr`, from the pod.
- HA needs stable IP-literal URLs, but pod IPs change. Each peer is its own
  single-replica StatefulSet behind a Service with a **pinned `clusterIP`**.
  A pod can't bind its own ClusterIP (the kernel never assigns it to the pod),
  so each pod's *own* URL is `0.0.0.0` and only the partner's is the
  ClusterIP. **Verified on k3s 1.33:** both pods reached `hot-standby` over
  ClusterIPs.
- Talos enforces Pod Security "baseline" cluster-wide by default; EKS
  enforces nothing. The role labels the namespace explicitly so both behave
  alike: `baseline` normally, `privileged` with hostNetwork or the Stork
  sidecar (SYS_PTRACE).
- A StatefulSet rolling update won't replace a pod stuck in CrashLoopBackOff.
  Delete the pod after fixing the spec. (This is standard Kubernetes
  behaviour; it was hit during testing.)
