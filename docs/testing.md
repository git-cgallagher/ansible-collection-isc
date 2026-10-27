# Testing

All results below are from 2026-10-27 on an Apple-silicon Mac (arm64)
running Docker Desktop. Toolchain: ansible-core 2.21, molecule 26.10,
ansible-lint 26.10 (production profile).

## What was tested, and how

| Path | Harness | Result |
|---|---|---|
| **package mode, HA** on AL2023 + Debian 12 + Rocky 9, Stork server on Ubuntu 24.04 | `molecule/default` (4 systemd containers; real ISC packages; real network) | ✅ converge, ✅ idempotence (0 changed), ✅ verify |
| HA state | verify: `status-get` on each peer | ✅ kea1 `hot-standby` (primary, owns scope), kea2 `hot-standby`, kea3 `backup` |
| Config portability | verify: sha256 of rendered config across 3 distros, ignoring `this-server-name` | ✅ identical |
| **Failover** | verify: stop kea1 → kea2 must reach `partner-down` and take scope `kea1` → restart → back to `hot-standby` | ✅ (scenario uses `max-unacked-clients: 0`; see docs/research.md for why) |
| Stork discovery (packages) | verify: `/api/machines?authorized=true` | ✅ 3 machines registered **unattended** via the server token the role fetched; Stork 2.6.0 sees `DHCPv4` 3.0.4 on each, with **no Control Agent** |
| **kubernetes mode, HA** (`talos` profile) | live **k3s v1.33** in Docker, images built from `files/Dockerfile.*` (arm64) | ✅ both StatefulSets Ready; kea1/kea2 `hot-standby` over **pinned ClusterIPs**; 2nd run `changed=0` for cluster objects |
| Stork in-cluster | in-cluster stork-server + PostgreSQL 16; sidecar agents | ✅ 2 machines authorized unattended (token fetched through port-forward), `DHCPv4@kea-kea1-0` / `@kea-kea2-0` active |
| Manifest variants | `kea_k8s_apply: false` render + `kubectl apply --dry-run=server` into a fresh namespace | ✅ eks/loadbalancer (13 objects), talos/loadbalancer+MetalLB (13), talos/hostnetwork (10), generic/none (11), all dual-stack v4+v6 |
| **container mode** | ⚠️ partial — see below | ✅ the unit's exact `run` flags start Kea 3.0.4; the containerised agent registers and Stork lists the daemon |
| Lint | `ansible-lint` (production profile), `yamllint` | ✅ 0 failures, 0 errors |

### Container mode: what was and wasn't covered

Nested containers can't exec any binary in this Docker Desktop environment.
A privileged Rocky 9 container running podman fails with `exec … Invalid
argument` even for `/bin/true`, under crun and runc alike. So the role's
container mode was run up to the point where podman executes something:
runtime detection, unit rendering, and validation-command rendering.

The generated unit's exact flags were then exercised on Docker directly:
`--user 0:101 --cap-drop ALL --cap-add NET_BIND_SERVICE --cap-add NET_RAW`,
with root-owned `0750` state dirs as the role creates them. The agent ran with
`--pid`/`--network` shared with Kea plus `SYS_PTRACE`. Kea started, the agent
registered with a server token, and Stork listed the daemon. **Not yet run:**
the role end to end on a real VM with podman or docker. Do that before relying
on container mode.

### Not covered

- A real EKS cluster (AWS Load Balancer Controller provisioning a UDP NLB) and
  a real Talos cluster. The manifests were accepted by the API server
  (dry-run) and the same manifests ran on k3s. Relay → NLB/MetalLB → pod →
  relay DHCP traffic has **not** been exercised.
- Real DHCP clients and relays. Failover was proven with
  `max-unacked-clients: 0`, which skips the unanswered-client detection.
- Alpine package mode and OpenRC service handling. The Alpine repo/key setup
  and packages were verified by building the images, but the role has not run
  against an Alpine host.
- Kea 3.2 (`kea_branch: "3-2"`), DHCPv6 HA at runtime (it was only rendered
  and dry-run), MySQL/PostgreSQL lease backends, and the TLS options.

## Running the tests

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install "ansible-core>=2.20" molecule "molecule-plugins[docker]" ansible-lint yamllint kubernetes
```

```bash
ansible-galaxy collection install -r requirements.yml -p ./collections
```

```bash
molecule test
```

```bash
ansible-lint && yamllint .
```

Kubernetes, against any throwaway cluster (k3s-in-docker shown):

```bash
docker run -d --name k3s-kea --privileged -p 127.0.0.1:16443:6443 rancher/k3s:v1.33.5-k3s1 server --disable traefik --tls-san 127.0.0.1
```

Then:

- export its kubeconfig with the server set to `127.0.0.1:16443`;
- build the three images and import them with
  `docker save … | docker exec -i k3s-kea ctr -n k8s.io images import -`;
- create a PostgreSQL database for Stork;
- edit the paths and IPs in `molecule/k8s/test-vars.yml`;
- start `kubectl -n dhcp port-forward svc/stork-server 18081:8080` (in a loop
  until it exists);
- run:

```bash
ansible-playbook -i molecule/k8s/inventory.yml -e @molecule/k8s/test-vars.yml examples/playbooks/kubernetes.yml
```

`molecule/k8s/test-vars.yml` and `molecule/container/inventory.yml` hold the
exact settings used on 2026-10-27. `stork_db_host` and the image names are
specific to that setup; adjust them before reuse.
