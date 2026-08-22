#!/usr/bin/env bash
# Reset del incidente entre ensayos. Sin esto, la tercera corrida arranca con
# basura de la primera y el timeline del dashboard miente.
set -euo pipefail
API="${1:-http://127.0.0.1:8000}"
echo "Reseteando $API ..."
curl -sf -X POST "$API/admin/reset" && echo " OK"
curl -sf "$API/health"; echo
echo
echo "En cada teléfono: Depuración (icono terminal) -> papelera -> 'Store y log vaciados'"
