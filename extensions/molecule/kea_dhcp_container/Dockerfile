# Test node for container mode: systemd as PID 1 plus its own Docker engine.
# Built for the host's native architecture: dockerd crashes under QEMU, but
# the amd64 Kea images run fine inside it through binfmt emulation.
FROM debian:12
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends systemd systemd-sysv python3 docker.io iproute2 ca-certificates \
 && rm -rf /var/lib/apt/lists/* \
 && systemctl enable docker
STOPSIGNAL SIGRTMIN+3
CMD ["/lib/systemd/systemd"]
