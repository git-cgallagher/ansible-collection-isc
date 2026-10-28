# Kea node for the stork_container scenario: Amazon Linux 2023 with systemd as
# PID 1 and its own Docker engine (AL2023 has no podman). Copied from
# kea_dhcp_container so each scenario stays self-contained. Native arch:
# dockerd crashes under QEMU; the amd64 Kea images run through binfmt.
FROM amazonlinux:2023
RUN dnf -y install systemd docker python3 iproute ca-certificates \
 && dnf clean all \
 && systemctl enable docker
STOPSIGNAL SIGRTMIN+3
CMD ["/usr/lib/systemd/systemd"]
