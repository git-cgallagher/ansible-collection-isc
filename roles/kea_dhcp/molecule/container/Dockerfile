# Test node for container mode: Amazon Linux 2023 with systemd as PID 1 and
# its own Docker engine (AL2023's `docker` package, as a real host would use).
# Built for the host's native architecture: dockerd crashes under QEMU, but
# the amd64 Kea images run fine inside it through binfmt emulation.
FROM amazonlinux:2023
RUN dnf -y install systemd docker python3 iproute ca-certificates \
 && dnf clean all \
 && systemctl enable docker
STOPSIGNAL SIGRTMIN+3
CMD ["/usr/lib/systemd/systemd"]
