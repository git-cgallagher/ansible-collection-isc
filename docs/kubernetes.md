# Kea on Kubernetes (EKS, Talos, any conformant cluster)

`kea_deploy_mode: kubernetes` renders plain manifests and applies them with
`kubernetes.core.k8s` from the control node. The same variables work on
EKS and Talos; `kea_k8s_profile` changes only:

| Concern | `eks` | `talos` | `generic` |
|---|---|---|---|
| DHCP load balancer | AWS Load Balancer Controller NLB (`loadBalancerClass: service.k8s.aws/nlb`, IP targets, internal, TCP health check) | MetalLB annotation (`metallb.io/loadBalancerIPs`) or Cilium LB-IPAM (`lbipam.cilium.io/ips`) via `kea_k8s_lb_implementation` | plain `LoadBalancer` |
| Lease storage | PVC (cluster default StorageClass) | `emptyDir` (Talos ships no StorageClass; HA resyncs leases) | PVC |
| Pod Security label | set explicitly (EKS enforces nothing by default) | set explicitly (Talos enforces `baseline` by default) | set explicitly |

## Topology

```
relay agents ──UDP/67──▶ LB kea-kea1-dhcp ──▶ pod kea-kea1-0 ─┐  HA over pinned
            └─UDP/67──▶ LB kea-kea2-dhcp ──▶ pod kea-kea2-0 ─┘  ClusterIPs :8001
                                              │  shareProcessNamespace
                                              └─ stork-agent sidecar ──▶ stork-server ──▶ PostgreSQL
```

- **One StatefulSet per HA peer**, each with `replicas: 1`. HA runs between
  the StatefulSets, not between replicas, because every peer needs its own
  `this-server-name` and role.
- **Pinned ClusterIPs.** Kea HA URLs must be IP literals and pod IPs change,
  so each peer has a Service with a fixed `spec.clusterIP`
  (`kea_k8s_peers[].cluster_ip`). Choose free addresses in the cluster's
  **service** CIDR. EKS defaults to `10.100.0.0/16` or `172.20.0.0/16`, Talos
  to `10.96.0.0/12`, and k3s to `10.43.0.0/16`.
- **A pod's own peer URL is `0.0.0.0`.** Kea binds the HA listener to the host
  in its own URL, and a pod can't bind its Service IP. Partners point at each
  other's ClusterIP. Verified: asymmetric URLs pair up fine.
- **Relayed DHCP only.** Pods never see L2 broadcasts, so the role forces
  `dhcp-socket-type: udp`. Configure **every relay with both peers' LB
  addresses**, as for any DHCP HA pair; HA state decides which peer answers.
  Kea sends replies to `giaddr` straight from the pod, so the relay must be
  routable from the pod network. On EKS with the VPC CNI that holds, because
  pod IPs are VPC IPs.
- **Rollouts go one peer at a time.** The role applies `kea1`, waits for
  Ready, then applies `kea2`, so a config change never restarts both
  partners. A config checksum annotation forces the roll.

## EKS checklist

- Install the AWS Load Balancer Controller. The in-tree controller can't do
  UDP with IP targets.
- NLB UDP target groups always preserve the client IP. The health check is TCP
  on the HA port (8001), or the Stork agent port when HA is off.
- Graviton nodes: ISC's images are amd64-only. Build `files/Dockerfile.kea`
  for `linux/arm64`, push to ECR, and set `kea_dhcp4_image`. Otherwise pin
  `kea_k8s_node_selector: {kubernetes.io/arch: amd64}`.
- NetworkPolicy only takes effect when VPC CNI network policy is enabled
  (`enableNetworkPolicy: "true"` on the add-on).
- Stork DB: use RDS PostgreSQL. `pgcrypto` is available; create the DB, user
  and extension first, and set `stork_db_sslmode: require`.

## Talos checklist

- Talos has no cloud LB. Run MetalLB (L2/BGP) or Cilium LB-IPAM, and give each
  peer a fixed IP with `kea_k8s_lb_ips`.
- **The default CNI (Flannel) does not enforce NetworkPolicy.** Use Cilium or
  Calico if you rely on `kea_k8s_network_policy`.
- PSA: Talos enforces `baseline` cluster-wide. The Kea containers are
  baseline-compliant. The Stork sidecar (SYS_PTRACE) and `hostnetwork`
  exposure need `privileged`, and the role labels the namespace for that
  automatically.
- For `hostnetwork` exposure (pods bind the node's NIC directly, with no LB),
  pin peers to dedicated nodes with `kea_k8s_node_selector`/tolerations. The
  pinned ClusterIPs still carry HA traffic.

## Images

ISC publishes amd64-only Kea images and no Stork images. Build all three from
`roles/kea_stork/files/` for both architectures:

```bash
cd roles/kea_stork/files
docker buildx build --platform linux/amd64,linux/arm64 --build-arg KEA_VERSION=3.0.4 -t REGISTRY/kea:3.0.4 -f Dockerfile.kea --push .
docker buildx build --platform linux/amd64,linux/arm64 --build-arg STORK_VERSION=2.6.0 --build-arg KEA_VERSION=3.0.4 -t REGISTRY/stork-agent:2.6.0-kea3.0.4 -f Dockerfile.stork-agent --push .
docker buildx build --platform linux/amd64,linux/arm64 --build-arg STORK_VERSION=2.6.0 -t REGISTRY/stork-server:2.6.0 -f Dockerfile.stork-server --push .
```

The Stork agent image **includes the Kea binaries**. The agent identifies a
daemon by running `kea-dhcp4 -v` from its own filesystem. Keep its
`KEA_VERSION` equal to the Kea image's.

## Stork in-cluster

- `kea_k8s_stork_server_enabled: true` deploys one `stork-server` replica
  against an external PostgreSQL (`stork_db_host`).
- Agents register to `stork_server_url`, normally the in-cluster Service.
  Each agent advertises `kea-<peer>.<ns>.svc.cluster.local`; override that
  with `kea_k8s_stork_agent_addresses` for an out-of-cluster server.
- **Unattended registration:** give `stork_server_token` directly, or set
  `stork_admin_password` plus a `stork_api_url` the *control node* can reach
  (an ingress, LB, or `kubectl port-forward`). The role then reads the token
  after the server is up and stores it in the `kea-stork-agent` Secret.
  Without either, approve machines in the UI.

## Operational gotchas

- A StatefulSet rolling update **won't replace a pod in CrashLoopBackOff**.
  After fixing the spec, run `kubectl -n dhcp delete pod kea-<peer>-0`.
- On a single-node test cluster (k3s servicelb), the second peer's UDP/67
  LoadBalancer stays `<pending>`, because the port is already taken on that
  node. Real clusters give each LB its own IP.
- Remove everything with `kea_k8s_state: absent`. PVCs from
  `volumeClaimTemplates` are kept, as is normal for StatefulSets.
