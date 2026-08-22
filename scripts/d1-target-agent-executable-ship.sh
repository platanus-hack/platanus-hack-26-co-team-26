#!/usr/bin/env bash
# Sube el fix de "target-agent no ejecutable" (D1 <-> D3, PR #6 de Alex). Corre esto VOS.
#
# Que arregla: SubprocessSandbox real (D3) invoca `python target-agent/src/agent.py
# --message ...` como script suelto. Con imports relativos eso revenia con
# ImportError, y el Oracle real reportaba "resisted" en falso (el agente nunca
# llegaba a ejecutar run_shell). Verificado en vivo con el sandbox real de Alex
# (mergeado temporalmente solo para probar, no esta en este commit):
#   finding.1 exploited (canary real al honeypot) -> finding.2 resisted (regresion
#   con AEG_SANITIZE=1 neutraliza el mismo payload de verdad). Loop T1+T2 cierra.
set -euo pipefail

REPO_DIR="/home/hell/Projects/PlatanusDevelopment/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

BRANCH="d1-target-agent-executable"
FILES=(
  "target-agent/src/agent.py"
  "target-agent/src/tools/shell.py"
  "scripts/d1-target-agent-executable-ship.sh"
)

echo "== Estado actual del repo =="
git status --short

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "== Cambiando a la rama existente ${BRANCH} =="
  git checkout "${BRANCH}"
else
  echo "== Creando rama ${BRANCH} desde main =="
  git checkout main
  git pull --ff-only origin main
  git checkout -b "${BRANCH}"
fi

echo "== Agregando archivos =="
git add -- "${FILES[@]}"

echo "== Esto es lo que se va a commitear =="
git status --short

read -r -p "¿Confirmar commit? [y/N] " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
  echo "Cancelado. Los archivos quedan en staging, sin commitear."
  exit 0
fi

git commit -m "$(cat <<'EOF'
fix(d1): target-agent ejecutable como script para el Sandbox real (D3)

Alex (PR #6, D3) implemento SubprocessSandbox: invoca el agente objetivo como
`python <repo>/src/agent.py --message "..."`. Con imports relativos
(`from .tools.email import ...`), correrlo asi fuera de un paquete revienta con
ImportError -- confirmado corriendolo a mano. El Sandbox no propaga esa excepcion
(solo captura returncode), asi que el Oracle real veia el ataque "resisted" en
falso: no es que el agente resistiera, es que nunca llego a ejecutar run_shell.

- target-agent/src/agent.py: sys.path.insert + imports absolutos (mismo patron que
  ya uso Alex en su fixture, cero cambios de su lado) + CLI real (argparse
  --message, imprime una linea JSON a stdout para la ExecutionTrace) + soporte de
  AEG_SANITIZE=1 en handle_user_message (asi la regresion T2 cierra por un hecho).
- target-agent/src/tools/shell.py: agrega sanitize_command() -- mismo regex que ya
  usa y probo el modulo de ataque cmd_injection real de Alex, para garantizar que
  neutraliza exactamente lo que el Sandbox dispara.

Verificado en vivo (no solo con tests): mergeando temporalmente PR #6 en una rama
descartable y corriendo el pipeline completo con AEG_REAL_D3=1 contra este
target-agent real -> finding.1 exploited (canary real al honeypot real) ->
finding.2 resisted (regresion). No toca ningun archivo de Alex ni de nadie mas.
Extractor sigue en 20/20 tests, arquitectura.json extraida sin cambios de forma.
EOF
)"

echo "== Pusheando ${BRANCH} =="
git push -u origin "${BRANCH}"

if command -v gh >/dev/null 2>&1; then
  read -r -p "¿Crear el PR con gh ahora? [y/N] " CONFIRM_PR
  if [[ "${CONFIRM_PR}" == "y" || "${CONFIRM_PR}" == "Y" ]]; then
    gh pr create \
      --title "D1: target-agent ejecutable (cierra el pendiente D1<->D3 del PR #6)" \
      --base main \
      --head "${BRANCH}" \
      --body "$(cat <<'EOF'
## Que arregla
El PR #6 (Alex, D3) documento un pendiente explicito: el `target-agent/` de D1 es un
agente `@tool` para extraccion AST, no ejecutable como script -- y `SubprocessSandbox`
necesita ejecutarlo de verdad. Este PR lo cierra.

## Causa raiz encontrada
`target-agent/src/agent.py` usaba imports relativos. `SubprocessSandbox` lo invoca como
`python <repo>/src/agent.py --message ...` (script suelto, no paquete) -> `ImportError`
al arrancar. El sandbox no propaga esa excepcion (solo lee el returncode del subproceso),
asi que el Oracle real marcaba el ataque `resisted` -- pero no porque el agente resistiera,
sino porque nunca llego a correr `run_shell`. Falso negativo silencioso.

## Que cambia
- `target-agent/src/agent.py`: imports absolutos + `sys.path.insert` (mismo patron que
  el fixture de Alex, cero cambios de su lado) + CLI (`--message`, imprime una linea JSON)
  + soporte de `AEG_SANITIZE=1` para que la regresion T2 cierre por un hecho real.
- `target-agent/src/tools/shell.py`: `sanitize_command()`, mismo regex que ya usa y probo
  el modulo `cmd_injection` real de Alex.

## Verificacion
- `cd backend && uv run pytest -q` -- 30/30 en verde (extractor completo sin regresiones).
- `cd backend && uv run ruff check .` -- limpio en archivos de este PR.
- **Verificado en vivo con el Sandbox real de Alex** (merge temporal en una rama
  descartable, no incluido en este PR): `AEG_REAL_D3=1`, corrida completa contra este
  `target-agent` -> `finding.1 exploited` (canary real al honeypot) -> `finding.2
  resisted` (regresion). Loop T1+T2 cierra de punta a punta contra el agente real de D1.

## No incluido a proposito
No toca `backend/adapters/fakes.py` ni `backend/api/main.py` (archivos de Alex/compartidos).
Hay un bug aparte, ya reportado, donde `FakeAnalyst` (fallback sin `ANTHROPIC_API_KEY`)
referencia `surface: "tool.shell"` en vez de `tool.run_shell` -- no rompe la ejecucion
(el sandbox no cruza esa referencia) pero es dato incorrecto en el dashboard. Queda para
quien toque `fakes.py`, fuera del scope de este fix.
EOF
)"
  else
    echo "PR no creado. Podes correrlo despues con: gh pr create --base main --head ${BRANCH}"
  fi
else
  echo "gh no esta disponible; crea el PR manualmente para ${BRANCH} -> main."
fi
