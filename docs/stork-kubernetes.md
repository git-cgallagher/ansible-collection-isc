# Stork on Kubernetes

## Server

`stork_server_deploy_mode: kubernetes` applies a Namespace (optional),
Secret, Service and a single-replica Deployment from the control node. It
needs an image (`docker/Dockerfile.stork-server`) and an external PostgreSQL
with `pgcrypto`: RDS on EKS, CloudNativePG or similar on Talos.

To rotate the `admin`/`admin` bootstrap password, set
`stork_server_admin_password` and a `stork_server_k8s_api_url` the control
node can reach (ingress, LoadBalancer, or `kubectl port-forward`). The
password must meet Stork's policy (12+ characters, upper and lower case, a
digit, a special character or space). If it doesn't, the run fails with
Stork's reason.
`stork_server_k8s_apply: false` together with `stork_server_k8s_render_dir`
only writes the manifests, for review or GitOps. That file holds the DB
password, so treat it like a Secret.

## Agent as a sidecar

The agent must live **in the Kea pod**. `stork_agent_deploy_mode: kubernetes`
doesn't apply a workload. Instead it:

1. sets two facts, `stork_agent_k8s_containers` (the sidecar) and
   `stork_agent_k8s_volumes` (its state volume);
2. creates Kea's namespace if it doesn't exist yet, and applies a Secret
   holding the registration token there (`stork_agent_k8s_manage_secret`,
   in `stork_agent_k8s_namespace`).

The Kea role then puts the facts into its pod template. With
`git_cgallagher.isc.kea_dhcp`:

```yaml
- hosts: kea          # logical Kea instances, ansible_connection: local
  gather_facts: false
  roles:
    - role: git_cgallagher.isc.stork_agent
      vars:
        stork_agent_deploy_mode: kubernetes
        stork_agent_image: registry.example/stork-agent:2.6.0-kea3.0.4
        stork_agent_server_url: http://stork-server.stork.svc.cluster.local:8080
        stork_agent_server_token: "{{ vault_stork_server_token }}"
        stork_agent_k8s_namespace: kea-dhcp
        # Service network mode: the per-peer HA Service is a stable address.
        stork_agent_k8s_address: "kea-{{ inventory_hostname }}-ha.kea-dhcp.svc.cluster.local"
    - role: git_cgallagher.isc.kea_dhcp
      vars:
        kea_dhcp_deployment: kubernetes
        kea_dhcp_k8s_share_process_namespace: true
        kea_dhcp_k8s_extra_containers: "{{ stork_agent_k8s_containers }}"
        kea_dhcp_k8s_extra_volumes: "{{ stork_agent_k8s_volumes }}"
        kea_dhcp_api_http_enabled: true
        kea_dhcp_api_auth_clients:
          - { user: stork, password: "{{ vault_kea_api_password }}" }
```

`kea_dhcp_k8s_share_process_namespace: true` also turns on
`kea_dhcp_k8s_extra_containers_mount_config`, which gives the sidecar every
config mount of the Kea containers, at the same paths. The sidecar then needs
no `stork_agent_k8s_volume_mounts` of its own.

### What the sidecar depends on

Each of these was hit in the live test (see [testing.md](testing.md)).

- **Kea's process.** `shareProcessNamespace: true`, plus `SYS_PTRACE` in the
  sidecar to read `/proc/<pid>/cwd`. That puts the namespace above Pod
  Security "baseline": it needs `privileged`.
- **The same paths as Kea.** The agent opens the config named on Kea's
  command line, then the `user-file` and `password-file` of **every** API
  client listed there, not just the `stork…` one. One missing file and it
  logs `Failed to detect Kea daemon(s) … cannot read client credentials`.
  `kea_dhcp` mounts each file from its `config` Secret with a `subPath`, so a
  directory mount at `/etc/kea` doesn't work. Let
  `kea_dhcp_k8s_extra_containers_mount_config` copy the mounts.
- **A `stork…` API client.** Give Kea an API client whose user name starts
  with `stork`; the agent picks it automatically.
- **A stable agent address.** Stork identifies a machine by address and
  port.
  - Re-registering at the same address reuses the machine entry, even with
    fresh agent state.
  - A new address creates a new entry and leaves the old one behind. Stork
    keeps polling the dead entry, and its HA view can follow the dead daemon.
  - So the default `$(POD_IP)` leaves one stale machine per pod restart.
  - Where the address comes from depends on the network mode:
    - **Host network** (the default on Talos and generic clusters): the pod
      IP is the node IP. It's stable, so the default is fine.
    - **Service mode** (EKS) with HA: `kea_dhcp` adds the sidecar's TCP ports
      to each peer's `<instance>-ha` Service. Use its DNS name, as above.
      `register` then logs `cannot setup the GRPC listener: listen tcp
      <ClusterIP>:8080`. That's harmless: the certificates are stored first,
      and the entrypoint carries on.
    - **Service mode without HA:** there is no per-peer Service. Expose the
      agent port yourself, or accept the stale entries.
- **The image.** `docker/Dockerfile.stork-agent` bundles Kea's binaries,
  because the agent runs `kea-dhcp4 -v` from its own filesystem. Keep its
  `KEA_VERSION` equal to the Kea image's.

### Restarts and registration

- Registration state lives in an `emptyDir`. It survives container restarts
  but not pod restarts.
- When a pod comes back at the same address, the agent registers again at
  once and Stork reuses the machine entry.
- If the server is slow to answer, `register` retries. The retries can hit
  Stork's unique key on (address, port): `Cannot store machine … duplicate
  key value violates unique constraint`. This happened in the test while the
  server was still timing out against dead pods. The entrypoint then exits,
  the kubelet restarts the sidecar, and the next attempt finds the stored
  certificates.

### What Stork showed in the live test

For a hot-standby pair (Kea 3.0.4, Stork 2.6.0, k3s 1.33):

- both `dhcp4` daemons active and monitored;
- the subnet found on both;
- HA `hot-standby`, both peers in touch;
- hooks `lease_cmds` and `ha` loaded.

Its log target was `stdout`, so Stork's log viewer had nothing to show: it
only reads log files.

## EKS / Talos notes

- **EKS:**
  - Expose the server with `stork_server_k8s_service_type: LoadBalancer`
    plus AWS Load Balancer Controller annotations
    (`stork_server_k8s_service_annotations`), or through an Ingress.
  - For RDS, `stork_server_db_sslmode: require` is the default for external
    databases.
  - Kea runs in service mode, so set the agent address as shown above.
- **Talos:**
  - The sidecar needs Pod Security `privileged` on Kea's namespace. With
    `kea_dhcp_k8s_platform: talos` the Kea role already sets that label.
  - Use MetalLB or Cilium if the server needs a LoadBalancer.
  - Flannel (the default CNI) doesn't enforce NetworkPolicy.
