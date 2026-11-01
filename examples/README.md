# Examples

Each directory holds a `playbook.yml` and the `inventory.yml` with every
setting, so a copy of the directory is a working starting point:

```bash
ansible-galaxy collection install git_cgallagher.isc
ansible-playbook -i examples/stork_server/package/inventory.yml examples/stork_server/package/playbook.yml --ask-vault-pass
```

Secrets are `vault_*` variables; each inventory's header lists the ones it
needs. Put them in an Ansible Vault file (`group_vars/all/vault.yml` next to
the inventory) and never in the inventory itself.

| Example | What it deploys |
|---|---|
| [`stork_server/package`](stork_server/package/) | The Stork server from ISC's packages, with a local PostgreSQL and the required admin password. **Run it before any example with Stork agents**: they read their registration token from this server's API. |
| [`kea_dhcp/msdns-stork`](kea_dhcp/msdns-stork/) | Kea 3.0 hot-standby pair that updates **Microsoft DNS** over GSS-TSIG, with the Active Directory side (service account, SPN, zones, keytab) prepared on the domain controller by `kea_dhcp_msdns`, and a Stork agent next to each Kea. Three plays: DC, Kea, agents. |
| [`kea_dhcp/package-ha`](kea_dhcp/package-ha/) | Kea 3.0 hot-standby pair from packages, no DNS updates. |
| [`kea_dhcp/vm-ha3`](kea_dhcp/vm-ha3/) | Three Kea VMs: primary, standby and a backup that holds every lease. |
| [`kea_dhcp/talos-ha`](kea_dhcp/talos-ha/) | Kea HA pair as hostNetwork pods on Talos. |
| [`kea_dhcp/eks-relay`](kea_dhcp/eks-relay/) | Kea replicas on EKS behind an internal NLB, serving relayed DHCP from RDS leases. |

Secrets and keytabs the roles write (`kea_dhcp_msdns_keytab_dest`) belong
outside any repository.
