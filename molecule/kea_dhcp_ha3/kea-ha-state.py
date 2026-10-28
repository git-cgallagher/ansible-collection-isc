#!/usr/bin/env python3
"""Print this Kea server's HA state (ha-heartbeat over the unix control socket)."""
import json
import socket

sock = socket.socket(socket.AF_UNIX)
sock.connect("/var/run/kea/kea4-ctrl-socket")
sock.sendall(json.dumps({"command": "ha-heartbeat"}).encode())
data = b""
while chunk := sock.recv(65536):
    data += chunk
reply = json.loads(data)
reply = reply[0] if isinstance(reply, list) else reply
print(reply.get("arguments", {}).get("state") or f"error {reply.get('result')}: {reply.get('text')}")
