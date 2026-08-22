#!/usr/bin/env bash
# Sube el fix de los 2 bugs del diagnostico clinico: mismatch de path frontend/backend, y
# el fake analyst/sandbox referenciando una tool que no existe. Corre esto VOS.
set -euo pipefail

REPO_DIR="/home/hell/Projects/PlatanusDevelopment/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

BRANCH="d1-fix-run-defaults"
FILES=(
  "backend/adapters/fakes.py"
  "backend/api/main.py"
  "frontend/src/lib/api.ts"
  "scripts/d1-fix-run-defaults-ship.sh"
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
fix: path de repo_path CWD-dependiente + fakes desincronizados del extractor real

Dos bugs del diagnostico clinico en vivo (backend + frontend levantados, corridas
reales disparadas), confirmados con logs y JSON de respuesta, no solo leyendo codigo.

1. frontend/src/lib/api.ts:5 default "./target-agent" vs backend/api/main.py:97
   default "../target-agent" -- dos cwd distintos asumidos, nunca coincidian. El
   frontend siempre manda su propio default explicito, asi que el del backend
   jamas se usaba. Resultado: click en "iniciar corrida" -> ValueError sin
   capturar dentro de threading.Thread -> el SSE mostraba "extract started" ->
   "end done" sin ningun evento de error. Fix: backend/api/main.py resuelve
   repo_path contra la raiz del repo (via Path(__file__), no via cwd) con
   _resolve_repo_path(); probado lanzando uvicorn desde backend/ Y desde la raiz
   del repo, mismo resultado en ambos. Ademas: _run_graph ahora atrapa cualquier
   excepcion del grafo y empuja un HarnessEvent status="error" a la cola en vez
   de terminar el stream en silencio.

2. backend/adapters/fakes.py: FakeAnalyst devolvia threats con surface="tool.shell"
   hardcodeado -- resabio de cuando FakeExtractor (mismo id) era el unico
   extractor que existia. Con PyAstExtractor real conectado (produce
   "tool.run_shell"), el fallback sin ANTHROPIC_API_KEY generaba un
   threat_analysis/harness_spec/finding apuntando a una tool que no existe en el
   architecture.json real. FakeSandbox tenia el mismo problema (surface
   hardcodeado, ignoraba el harness_spec real). Fix: ambos derivan el id de tool
   shell (y el de mcp_server) del `arch`/`spec` real que reciben, con fallback a
   los valores originales -- test_skeleton.py (100% fake, FakeExtractor incluido)
   sigue dando exactamente el mismo resultado que antes.

Verificado en vivo: corrida real sin ANTHROPIC_API_KEY -> threat_analysis y
findings ahora referencian "tool.run_shell" (coincide con architecture.json real,
antes decia "tool.shell"). 30/30 tests en verde, incluyendo test_skeleton.py sin
cambios de comportamiento. tsc/oxlint limpios en api.ts.
EOF
)"

echo "== Pusheando ${BRANCH} =="
git push -u origin "${BRANCH}"

if command -v gh >/dev/null 2>&1; then
  read -r -p "¿Crear el PR con gh ahora? [y/N] " CONFIRM_PR
  if [[ "${CONFIRM_PR}" == "y" || "${CONFIRM_PR}" == "Y" ]]; then
    gh pr create \
      --title "fix: repo_path CWD-dependiente + fakes desincronizados (tool.shell)" \
      --base main \
      --head "${BRANCH}" \
      --body "$(cat <<'EOF'
## Que arregla
Dos bugs encontrados en un diagnostico en vivo (backend + frontend levantados localmente,
corridas reales disparadas, no solo lectura de codigo):

### 1. Mismatch de path -> crash silencioso desde el dashboard
`frontend/src/lib/api.ts` default `"./target-agent"` vs `backend/api/main.py` default
`"../target-agent"` -- asumen `cwd` distintos, nunca coinciden. El click de "iniciar
corrida" en el dashboard terminaba en un `ValueError` sin capturar dentro de un
`threading.Thread`, y el SSE mostraba `extract started -> end done` sin ningun error visible.

**Fix:** `backend/api/main.py::_resolve_repo_path` resuelve contra la raiz del repo
(via `Path(__file__)`), no contra el `cwd` del proceso -- probado lanzando `uvicorn`
desde `backend/` y desde la raiz del repo, mismo resultado. Ademas, `_run_graph` ahora
atrapa cualquier excepcion del grafo y empuja un evento `status="error"` a la cola en vez
de terminar en silencio.

### 2. `FakeAnalyst`/`FakeSandbox` referenciaban una tool que no existe
Con `PyAstExtractor` real conectado (produce `tool.run_shell`), el fallback a
`FakeAnalyst` (sin `ANTHROPIC_API_KEY`) seguia hardcodeando `surface="tool.shell"` --
resabio de cuando `FakeExtractor` (mismo id) era el unico extractor. Esa referencia rota
se propagaba a `harness_spec` y `finding`.

**Fix:** `FakeAnalyst`/`FakeSandbox` derivan el id real de `arch`/`spec` en vez de
hardcodearlo, con fallback a los valores originales -- `test_skeleton.py` (100% fake,
incluye `FakeExtractor`) sigue pasando exactamente igual.

## Verificacion
- `cd backend && uv run pytest -q` -- 30/30 en verde.
- `cd backend && uv run ruff check .` -- sin errores nuevos.
- `cd frontend && npx tsc -b --noEmit && npm run lint` -- limpio en `api.ts`.
- Corrida real sin `ANTHROPIC_API_KEY`: `threat_analysis`/`findings` ahora referencian
  `tool.run_shell` (antes `tool.shell`, inexistente).
- Servidor lanzado desde `backend/` Y desde la raiz del repo -> mismo resultado correcto
  en ambos casos.
EOF
)"
  else
    echo "PR no creado. Podes correrlo despues con: gh pr create --base main --head ${BRANCH}"
  fi
else
  echo "gh no esta disponible; crea el PR manualmente para ${BRANCH} -> main."
fi
