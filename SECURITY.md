# Security policy

## Reporting a vulnerability

Please report security issues **privately** through GitHub:
[Report a vulnerability](https://github.com/git-cgallagher/ansible-collection-isc/security/advisories/new)
(the **Security** tab, then **Report a vulnerability**). Don't open a public issue for a security problem.

You can expect an acknowledgement within a week. This is a one-person project, so fixes are best effort.

## Supported versions

Only the latest release gets fixes.

## Scope

This collection configures ISC Kea and ISC Stork on hosts and Kubernetes clusters, with the
privileges your playbook gives it. Reports about how it handles credentials (Kea API passwords,
the Stork database password and server token, TLS keys), file permissions, or the Kubernetes
objects it creates are in scope. Vulnerabilities in Kea or Stork themselves belong with
[ISC](https://www.isc.org/security-report/).
