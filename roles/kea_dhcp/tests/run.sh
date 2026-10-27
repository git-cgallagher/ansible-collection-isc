#!/usr/bin/env bash
# Render every scenario in tests/render/inventory.yml (no cluster needed) and
# check each generated Kea config with `kea-<daemon> -t` in the ISC image the
# role selected. Requires: ansible-core, kubernetes.core, docker, PyYAML, openssl.
set -euo pipefail
cd "$(dirname "$0")"

# Throwaway PKI for the TLS scenario; never committed (see .gitignore).
if [[ ! -f render/tls.json ]]; then
  tmp=$(mktemp -d)
  openssl req -x509 -newkey rsa:2048 -nodes -keyout "$tmp/ca.key" -out "$tmp/ca.pem" -days 30 -subj "/CN=kea-test-ca" 2>/dev/null
  openssl req -newkey rsa:2048 -nodes -keyout "$tmp/peer.key" -out "$tmp/peer.csr" -subj "/CN=kea-peer" 2>/dev/null
  printf 'subjectAltName=IP:172.20.10.11,IP:172.20.10.12,IP:127.0.0.1\n' > "$tmp/ext"
  openssl x509 -req -in "$tmp/peer.csr" -CA "$tmp/ca.pem" -CAkey "$tmp/ca.key" -CAcreateserial \
    -out "$tmp/peer.pem" -days 30 -extfile "$tmp/ext" 2>/dev/null
  python3 - "$tmp" > render/tls.json <<'PY'
import json, sys
d = sys.argv[1]
print(json.dumps([{"dest": "/etc/kea/tls/" + n, "content": open(f"{d}/{n}").read()}
                  for n in ("ca.pem", "peer.pem", "peer.key")]))
PY
  rm -rf "$tmp"
fi

rm -rf output
(cd render && ansible-playbook -i inventory.yml playbook.yml)
python3 validate.py output
