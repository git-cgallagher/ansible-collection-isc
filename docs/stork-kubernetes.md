# Stork on Kubernetes

## Server

`stork_server_deploy_mode: kubernetes` applies a Namespace (optional),
Secret, Service and a single-replica Deployment from the control node. It
needs an image (`docker/Dockerfile.stork-server`) and an external PostgreSQL
with `pgcrypto`: RDS on EKS, CloudNativePG or similar on Talos.

To rotate the `admin`/`admin` bootstrap password, set
`stork_server_admin_password` and a `stork_server_k8s_api_url` the control
node can reach (ingress, LoadBalancer, or `kubectl port-forward`).
`stork_server_k8s_apply: false` together with `stork_server_k8s_render_dir`
only writes the manifests, for review or GitOps. That file holds the DB
password, so treat it like a Secret.

## Agent as a sidecar

The agent must live **in the Kea pod**. This collection doesn't deploy Kea,
so `stork_agent_deploy_mode: kubernetes` doesn't apply a workload. Instead it:

1. sets two facts, `stork_agent_k8s_containers` (the sidecar) and
   `stork_agent_k8s_volumes` (its state volume);
2. optionally applies a Secret holding the registration token
   (`stork_agent_k8s_manage_secret`, in `stork_agent_k8s_namespace`).

Your Kea role puts the facts into its pod template, and the pod must also set
**`shareProcessNamespace: true`**.

```yaml
- hosts: localhost
  connection: local
  roles:
    - role: git_cgallagher.isc.stork_agent
      vars:
        stork_agent_deploy_mode: kubernetes
        stork_agent_image: registry.example/stork-agent:2.6.0-kea3.0.4
        stork_agent_server_url: http://stork-server.stork.svc.cluster.local:8080
        stork_agent_server_token: "{{ vault_stork_server_token }}"
        stork_agent_k8s_namespace: kea-dhcp
        # Mirror the Kea container's mounts: same volume names, same paths.
        stork_agent_k8s_volume_mounts:
          - { name: config, mountPath: /etc/kea, readOnly: true }
    - role: kea_dhcp
      vars:
        kea_dhcp_k8s_extra_containers: "{{ stork_agent_k8s_containers }}"
        kea_dhcp_k8s_extra_volumes: "{{ stork_agent_k8s_volumes }}"
```

### Rules the sidecar depends on

- **Same paths as Kea.** The agent opens the config path from Kea's command
  line, then the API password files it names. Every one of those paths must
  exist in the sidecar. With `kea_dhcp`, which mounts each file from its
  `config` Secret with a `subPath`, copy those `volumeMounts` (config files and
  `api-creds/*`) into `stork_agent_k8s_volume_mounts`.
- **A `stork…` API client.** Give Kea an API client whose user name starts
  with `stork`; the agent picks it automatically.
- **Pod Security `privileged`** on Kea's namespace, for `SYS_PTRACE`.
- **Agent address.** The default, `$(POD_IP)`, works for an in-cluster server,
  but every pod restart registers a new machine and leaves the old entry
  behind. Use a stable per-pod Service name when Kea has one, for example
  `stork_agent_k8s_address: "$(POD_NAME).kea-headless.kea-dhcp.svc"`.
- **Image.** `docker/Dockerfile.stork-agent` bundles Kea's binaries, because
  the agent runs `kea-dhcp4 -v` from its own filesystem. Keep its
  `KEA_VERSION` equal to the Kea image's.

### Status with `kea_dhcp`

`kea_dhcp` exposes `kea_dhcp_k8s_extra_containers` and `_extra_volumes`
but **not `shareProcessNamespace`** (as of 2026-10-27). Until it does, the
sidecar starts but can't see Kea's process. That one switch is all that's
needed on the Kea side.

## EKS / Talos notes

- **EKS:** expose the server with `stork_server_k8s_service_type:
  LoadBalancer` plus AWS Load Balancer Controller annotations
  (`stork_server_k8s_service_annotations`), or through an Ingress. For RDS,
  `stork_server_db_sslmode: require` is the default for external databases.
- **Talos:**
  - Label Kea's namespace `pod-security.kubernetes.io/enforce: privileged`.
  - Use MetalLB or Cilium if the server needs a LoadBalancer.
  - Flannel (the default CNI) doesn't enforce NetworkPolicy.
