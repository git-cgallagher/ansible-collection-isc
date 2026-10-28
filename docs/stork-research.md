# Research notes: ISC Stork (and the Kea behaviour it depends on)

As of 2026-10-27. Items marked **verified** were reproduced in containers
while building this collection; the rest come from ISC docs or mailing lists,
cited inline.

## Versions

| Component | Line | Status |
|---|---|---|
| Stork | **2.6.0** | Stable (even minor), released 2026-10-09, in the `stork` repo |
| Stork | 2.4.x | Previous stable; the first with direct Kea API support (no Control Agent) |
| Stork | 2.5.x | Development (odd minor), in the `stork-dev` repo; not for production |
| Kea | 3.0 (LTS) / 3.2 (stable) | Both work. **Verified:** Stork 2.6.0 monitors Kea 3.0.4 and 3.2.1. |

Kea's Control Agent is deprecated in 3.0 and removed in 3.2
([ISC KB](https://kb.isc.org/docs/kea-control-agent-migration)). Each daemon
serves its own API through `control-sockets`, and Stork ≥ 2.4 uses that
directly
([kea-users 2026-04](https://lists.isc.org/pipermail/kea-users/2026-April/006049.html)).

## Packaging (verified)

- Packages are `isc-stork-server` and `isc-stork-agent`, from Cloudsmith
  `isc/stork`. The systemd/OpenRC units are `isc-stork-server` and
  `isc-stork-agent`. Config lives in `/etc/stork/{server,agent}.env`.
- **Amazon Linux 2023** has no ISC repo, but the EL9 RPMs install and run
  (aarch64, Stork 2.6.0). **`shadow-utils` must be installed in an earlier
  transaction:** the `%pre` scriptlets call `groupadd`/`useradd` and abort
  without it.
- **RPM version** strings are `2.6.0.<build>`, so pins must be globs:
  `-2.6.0*` for dnf, `=2.6.0*` for apt, `~2.6.0` for apk.
- **Alpine:** each repo signs its index with its own RSA key, saved as
  `<repo>@isc-<KEYID>.rsa.pub`. apk picks the key by **file name**, so any
  other name gives "UNTRUSTED signature". The generic `/rsa.key` URL serves the
  PGP key.
- **ISC publishes no Stork container images.** The Dockerfiles under
  `docker/` build them from ISC's Alpine packages for amd64 and arm64.

## Server

- One Go binary plus **PostgreSQL ≥ 10 with `pgcrypto`**. All state lives in
  PostgreSQL, so you get availability by running one server against an HA
  database.
- **Verified API on 2.6.0:**
  - `POST /api/sessions {authenticationMethodId: internal, identifier, secret}`
    returns the user, including `id` and `changePassword`. (It is *not*
    `/api/users/login`.)
  - `GET /api/machines-server-token` returns `{token}`.
  - `PUT /api/users/{id}/password {oldpassword, newpassword}`.
  - The first-boot login is `admin`/`admin`.
- `/metrics` has no authentication.
- RHEL-family PostgreSQL defaults to `ident` for host connections. The role
  adds a `scram-sha-256` line for the Stork user on 127.0.0.1.

## Agent

- **Discovery.** The agent scans `/proc`, reads the config path from Kea's
  command line, opens that file to find the control sockets, and talks HTTP(S)
  to them. It therefore runs next to Kea: same host, or same pod with a shared
  PID namespace.
- **Verified: it runs `/usr/sbin/kea-dhcp4 -v` *from its own filesystem*** to
  identify each daemon. Consequences:
  - A sidecar or container without Kea binaries logs "Failed to detect Kea
    daemon(s)".
  - With Kea in a container on a host, a *packaged* agent on that host can't
    identify it either.

  So `Dockerfile.stork-agent` bundles the Kea binaries. It strips their file
  caps and makes them 0755, because ISC ships them as `0754 kea:kea` with
  `cap_net_bind_service,cap_net_raw=ep`, and the agent only runs `-v`.
- **API credentials** come from each daemon's Kea config. The agent prefers a
  client whose user name starts with `stork` and needs read access to the
  password file ([Stork docs](https://stork.readthedocs.io/en/latest/install.html)).
  **Verified:** Kea 3.2.1 with `authentication.clients: [{user-file,
  password-file}]` (the layout `kea_dhcp` renders) is monitored and active,
  with the agent reading the files through Kea's group.
  **Verified (2026-10-28):** the agent opens the files of *every* client,
  not only the preferred one. With `ha` and `stork` clients and only the
  `stork` files mounted, it logged "cannot read client credentials: could
  not read the user file '/etc/kea/api-creds/ha.user'" and monitored
  nothing.
- **Registration** is `stork-agent register --non-interactive --server-url …
  --agent-host … [--server-token …]`.
  - With the server token, the machine is authorized at once. Without it,
    someone approves it in the UI.
  - It writes `/var/lib/stork-agent/{root-cert.pem,server-cert.pem,server-key.pem,token.txt}`.
  - Its last step binds a ping listener on `--agent-host`. Behind a Kubernetes
    Service address that fails, but only *after* the certs are stored.
- **Verified:** with `STORK_AGENT_SERVER_URL` in `agent.env`, the agent
  re-registers on every start and exits fatally when `STORK_AGENT_HOST` is a
  wildcard ("agent host address is not provided"). The collection registers
  explicitly and leaves that variable out.
- The Prometheus Kea exporter listens on :9547 (BIND 9 on :9119).

## Kubernetes

- The sidecar needs `shareProcessNamespace: true` on the Kea pod, and
  `SYS_PTRACE` to read `/proc/<pid>/cwd`. That puts it above Pod Security
  "baseline": the namespace needs `privileged`. Talos enforces baseline
  cluster-wide by default; EKS enforces nothing.
- **Verified (2026-10-28): Stork keys a machine on (address, port).**
  - Re-registering at an existing address, with fresh certificates and
    token, reuses the machine entry.
  - Each pod restart under `$(POD_IP)` added an entry: three restarts left
    three dead machines. Stork kept polling them, and one HA status lookup
    still went to a dead daemon's agent.
- **Verified:** a slow first registration (about 29 s, while the server was
  timing out against dead agents) made `register` retry. The retries failed
  with `duplicate key value violates unique constraint` ("Cannot store
  machine"). The sidecar exits and recovers on the kubelet's restart.
- **Verified:** the 2.6 admin password policy is 12+ characters, upper and
  lower case, a digit and a special character or space. A refused change is
  a 400 with a message naming the unmet rules.
- **Verified on k3s 1.33 with this collection's roles:**
  - the server in Kubernetes mode, with the password rotated through a
    port-forward;
  - sidecar agents in a `kea_dhcp` hot-standby pair (service mode, basic
    auth), monitored with HA state visible.

  See [stork-kubernetes.md](stork-kubernetes.md).
