"""Validate rendered Kea configs inside the real ISC images.

For every manifest in tests/kea_dhcp/output/**.yaml: take the Secret's payload, lay it
out exactly as the Deployment/DaemonSet mounts it, and run each container's
binary with `-t` (config check, which also loads and validates hook libraries)
in the container image the role chose. Needs docker and PyYAML.

usage: python3 tests/kea_dhcp/validate.py [tests/kea_dhcp/output]
"""
import pathlib
import subprocess
import sys
import tempfile

import yaml

out = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else pathlib.Path(__file__).parent / "output")
failures = 0
checks = 0

for manifest in sorted(out.rglob("*.yaml")):
    docs = [d for d in yaml.safe_load_all(manifest.read_text()) if d]
    secret = next(d for d in docs if d["kind"] == "Secret")
    workload = next(d for d in docs if d["kind"] in ("Deployment", "DaemonSet"))
    pod = workload["spec"]["template"]["spec"]
    for ctr in pod["containers"]:
        with tempfile.TemporaryDirectory() as tmp:
            args = []
            for m in ctr["volumeMounts"]:
                if m["name"] != "config":
                    continue
                src = pathlib.Path(tmp) / m["subPath"]  # subPaths are unique per pod
                src.write_text(secret["stringData"][m["subPath"]])
                args += ["-v", f"{src}:{m['mountPath']}:ro"]
            binary, _, conf = ctr["command"]
            cmd = ["docker", "run", "--rm", "--platform", "linux/amd64", *args,
                   ctr["image"], binary, "-t", conf]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)  # return code inspected below
            checks += 1
            label = f"{manifest.parent.name}/{manifest.stem} {ctr['name']} ({ctr['image'].rsplit(':', 1)[1]})"
            if res.returncode == 0:
                print(f"PASS {label}")
            else:
                failures += 1
                print(f"FAIL {label}")
                for line in (res.stdout + res.stderr).splitlines():
                    if any(k in line for k in ("ERROR", "FATAL", "rror", "failed")):
                        print(f"     {line.strip()[:300]}")

print(f"\n{checks - failures}/{checks} configs passed")
sys.exit(1 if failures else 0)
