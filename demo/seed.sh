#!/usr/bin/env bash
# Carga los fixtures en el backend. Sirve para que D5 trabaje el dashboard sin
# depender de que la malla ya funcione.
set -euo pipefail
API="${1:-http://127.0.0.1:8000}"
cd "$(dirname "$0")/.."
python3 - "$API" <<'PY'
import json, sys, urllib.request
api = sys.argv[1]
names = ["bundle-valid", "bundle-with-evidence", "bundle-duplicate",
         "bundle-tampered", "bundle-forged-key", "bundle-low-sqi"]
body = json.dumps({"bundles": [json.load(open(f"fixtures/{n}.json")) for n in names]}).encode()
req = urllib.request.Request(f"{api}/bundles/batch", body,
    {"Content-Type": "application/json", "Idempotency-Key": "seed-demo"})
print(json.dumps(json.load(urllib.request.urlopen(req)), indent=2, ensure_ascii=False))
PY
