# git_cgallagher.isc.stork_repository

Configures ISC's Cloudsmith package repository for Stork on Debian/Ubuntu
(apt), the RHEL family, Fedora and Amazon Linux 2023 (dnf/yum), and Alpine
(apk). The `stork_server` and `stork_agent` roles include it, so you only
call it directly to pre-stage repositories.

## Requirements

- One of the platforms above. Amazon Linux 2023 uses ISC's EL9 builds.
- `community.general` for Alpine (the `apk` module).

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `stork_repository_name` | `stork` | `stork` (stable, even minors) or `stork-dev` (development) |
| `stork_repository_base_url` | `https://dl.cloudsmith.io/public/isc` | Repository base. Point at a mirror if you have one. |
| `stork_repository_cloudsmith_token` | `""` | Entitlement token for ISC's private `-prv` repositories (vault it) |
| `stork_repository_apk_keys` | see defaults | Per-repo Alpine RSA key file names. apk matches keys by file name. |

The role sets the fact `stork_repository_pkg_format` (`deb`, `rpm` or `apk`).

## Dependencies

None.

## Example Playbook

```yaml
- hosts: all
  become: true
  roles:
    - role: git_cgallagher.isc.stork_repository
      vars:
        stork_repository_name: stork
```

## License

MIT

## Author Information

Chris Gallagher ([@git-cgallagher](https://github.com/git-cgallagher))
