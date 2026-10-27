# Testing

| Check | How | Result (2026-10-27) |
|---|---|---|
| Integration | `molecule test`: Stork server on Ubuntu 24.04; agents next to **Kea 3.0.4 on Amazon Linux 2023 (no API auth)** and **Kea 3.2.1 on Debian 12 (basic auth via `user-file`/`password-file`)** | ✅ destroy → create → prepare → converge → idempotence (0 changed) → verify → destroy |
| What verify asserts | bootstrap `admin`/`admin` refused, rotated password works, 2 machines authorized with no manual approval, both `DHCPv4` daemons `active` + `monitored` | ✅ |
| Kubernetes | Render the server manifests (`stork_server_k8s_apply: false`) and wrap the generated sidecar in a Kea-like pod, then `kubectl apply --dry-run=server` on k3s 1.33 | ✅ accepted |
| Lint | `ansible-lint` (production profile), `yamllint` | ✅ 0 failures |
| Sanity | `ansible-test sanity` (ansible-core 2.21, Python 3.14) | ✅ 24 tests pass |

Kea in the integration test comes from `molecule/default/prepare.yml`, a
fixture standing in for whichever Kea role you use. It is not part of the
collection.

## Not covered yet

- Container mode end to end. Nested podman can't exec on the development
  machine (Docker Desktop). An earlier revision exercised the same unit
  through a podman shim and replayed the exact command lines on real Docker.
- A live sidecar inside a `kea_dhcp` pod. That needs `shareProcessNamespace`
  in `kea_dhcp`.
- Alpine (OpenRC) hosts, and real EKS or Talos clusters.

## Running

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install "ansible-core>=2.18" molecule "molecule-plugins[docker]" ansible-lint yamllint
```

```bash
ansible-galaxy collection install -r requirements.yml -p ./collections
```

```bash
mkdir -p .molecule-collections/ansible_collections/git_cgallagher && ln -sfn ../../.. .molecule-collections/ansible_collections/git_cgallagher/stork
```

```bash
molecule test
```

```bash
ansible-lint && yamllint .
```

Sanity needs the collection at `ansible_collections/git_cgallagher/stork`;
CI does this for you:

```bash
ansible-test sanity --venv
```
