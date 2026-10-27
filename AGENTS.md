# AGENTS.md — ansible-kea-stork

Ansible role `roles/kea_stork`: ISC Kea DHCP (with HA) + ISC Stork, on VMs
(packages), container hosts (podman/docker + systemd), or Kubernetes
(EKS/Talos/generic). Machine-local repo under `~/Code` (not yet on GitHub).
Read `README.md`, then `docs/research.md` (the verified facts the design
rests on).

## Commands

```bash
ansible-galaxy collection install -r requirements.yml -p ./collections
molecule test                      # 4-container HA + Stork integration test
ansible-lint && yamllint .         # must stay at 0 (production profile)
```

The Kubernetes and container-mode test procedures are in `docs/testing.md`.

## Conventions

- Public variables are prefixed `kea_` / `stork_` and documented in
  `defaults/main.yml`. Internal facts and vars are prefixed `_`.
- Booleans are always read with `| bool`, including inside Jinja `{% if %}`.
  Users pass `-e flag=false` as a string; ansible-core ≥ 2.19 rejects string
  conditionals, and Jinja would treat `"false"` as true.
- Kea config is built as a Jinja **dict** and emitted with `to_nice_json`
  (`templates/kea-dhcp.conf.j2` renders both v4 and v6). Never hand-write JSON
  text. Validate with `kea-dhcp4 -t` through `template: validate:`.
- Hooks are referenced by **bare file name**. One config works on every distro
  and image.
- Per-distro differences (service names, users, prereqs, PG packages) belong
  in `vars/<OsFamily>.yml` or `vars/<Distribution>.yml`, never in tasks.
- Kubernetes objects are templates under `templates/k8s/`. The rendered
  output must pass `kubectl apply --dry-run=server` for every
  profile/exposure combination (see docs/testing.md).

## ⚠️ Gotchas (each one was hit during development)

- **The Control Agent is gone (removed in 3.2).** Never add
  `isc-kea-ctrl-agent`. Daemons use `control-sockets` (plural) with an HTTP
  entry; Stork ≥ 2.4 uses that directly.
- **HA URLs must be IP literals**, and the HA listener binds to the host in
  the server's **own** URL. In Kubernetes the own URL is `0.0.0.0` and the
  partner's is its pinned ClusterIP. Asymmetric URLs are fine.
- **AL2023:** the EL9 RPMs need log4cplus, taken from EPEL 9 restricted to
  `includepkgs=log4cplus`. **shadow-utils must be installed in an earlier
  transaction than Kea/Stork.** Otherwise the `%pre` scriptlets can't create
  users, Stork fails, and Kea installs without its `kea` user.
- **Alpine:** the apk key file must be named `<repo>@isc-<KEYID>.rsa.pub`,
  because apk matches the key by file name. The generic `/rsa.key` URL is the
  PGP key. Key IDs live in `vars/main.yml`.
- **Version pins:** Stork's RPM version is `2.6.0.<build>`. Use globs
  (`-2.6.0*`, `=2.6.0*`).
- **Kea 3 path rules:** the socket dir must be `/var/run/kea` (not `/run/kea`)
  and no looser than 0750. That's why the k8s command chmods the emptyDirs.
- **ISC Kea binaries are 0754 kea:kea and kea-dhcp4 has file caps
  `cap_net_bind_service,cap_net_raw=ep`.** Run as uid 0 with gid 101 and keep
  NET_RAW + NET_BIND_SERVICE in the bounding set. Never `drop: [ALL]` for the
  Kea container, or exec fails with EACCES/EPERM.
- **ISC images are amd64-only; ISC publishes no Stork images.** Use
  `files/Dockerfile.*`.
- **The Stork agent execs `kea-dhcp4 -v` from its own filesystem.** Its image
  bundles Kea (with caps stripped), and in container mode the agent is
  containerised too.
- **Never put `STORK_AGENT_SERVER_URL` in agent.env.** The agent would
  re-register on every start and die with a wildcard host. Registration
  writes `/var/lib/stork-agent/root-cert.pem`, which is the idempotency
  marker.
- **Stork API:** login is `POST /api/sessions`, not `/users/login`.
- **Failover needs unanswered client traffic** with
  `max-unacked-clients > 0`. Tests that have no clients must set it to 0;
  production must not.
- **A StatefulSet won't replace a CrashLoopBackOff pod on update.** Delete
  the pod. `loadBalancerClass` and `volumeClaimTemplates` are immutable, so
  changing `kea_k8s_profile` or `kea_k8s_lease_storage` on a live deployment
  needs the Service/StatefulSet deleted first.
- **YAML:** a bare `on:` key parses as boolean `true`. Don't use `on`, `yes`,
  `no` or `off` as keys.

## TODO / follow-ups

- Run container mode end to end on a real VM. Nested podman can't exec on the
  dev machine, so only the unit flags were proven (docs/testing.md).
- Exercise real DHCP traffic through a relay, on real EKS (NLB UDP) and real
  Talos (MetalLB). So far the manifests have only been dry-run and run on k3s.
- Add a molecule scenario for Alpine (OpenRC) and for Kea 3.2.
- Optional: basic-auth on the control and HA listeners (only TLS is wired
  today), plus the Stork OIDC settings.
- Publish multi-arch images to a registry, and decide whether this repo goes
  to the `git-cgallagher` org.
