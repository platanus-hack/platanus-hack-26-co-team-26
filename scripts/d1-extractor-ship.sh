#!/usr/bin/env bash
# Prepara y sube la rama d1-extractor (C1 · Extractor, D1/Helmut), y al final imprime un
# aviso listo para copiar/pegar al canal del equipo con lo que se hizo, se integro y lo
# que queda pendiente (y por que).
#
# Corre este script VOS desde donde quieras (no hace falta estar parado en el repo, este
# cd te lleva ahi). No hace nada destructivo: solo agrega los archivos de este componente
# (nunca `git add -A`), te muestra el diff antes de commitear y pide confirmacion antes de
# tocar el remoto.
set -euo pipefail

REPO_DIR="/home/hell/Projects/PlatanusDevelopment/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

BRANCH="d1-extractor"
FILES=(
  "target-agent"
  "backend/adapters/extractor"
  "backend/tests/test_extractor.py"
  "backend/pyproject.toml"
  "backend/uv.lock"
  "scripts/d1-extractor-ship.sh"
)

echo "== Estado actual del repo =="
git status --short

if git show-ref --verify --quiet "refs/heads/${BRANCH}"; then
  echo "== Cambiando a la rama existente ${BRANCH} =="
  git checkout "${BRANCH}"
else
  echo "== Creando rama ${BRANCH} desde $(git rev-parse --abbrev-ref HEAD) =="
  git checkout -b "${BRANCH}"
fi

echo "== Agregando archivos del componente C1 (Extractor) =="
git add -- "${FILES[@]}"

echo "== Esto es lo que se va a commitear =="
git status --short

read -r -p "¿Confirmar commit con los archivos de arriba? [y/N] " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
  echo "Cancelado. Los archivos quedan en staging, sin commitear."
  exit 0
fi

git commit -m "$(cat <<'EOF'
feat(d1): extractor real (ast+semgrep+LLM opcional) + target-agent Acme

- target-agent/: agente de prueba (run_shell sin sanitizar, MCP Notion third-party,
  send_email, ACME_API_KEY en contexto, referenciada en SYSTEM_CONTEXT) -- narrativa
  specs/diagrams/real-case-flow.md.
- backend/adapters/extractor/: PyAstExtractor implementa ArchitectureExtractorPort.
  ast nativo (un solo parseo por archivo) + 1 regla Semgrep de corroboracion (con
  fallback si no esta instalado, y cruce contra data_flows para avisar de sinks que
  ast no vinculo) + pasada LLM opcional con guardrail anti-invencion (sin
  ANTHROPIC_API_KEY es no-op; cualquier id inventado por el LLM se descarta).
- Cumple los 4 criterios de aceptacion de specs/03-components.md #C1, incluyendo T1
  (agregar una tool cambia architecture.json), probado sobre una copia real de
  target-agent, no un mock.
- 22 tests (backend/tests/test_extractor.py) cubren los criterios de aceptacion +
  guardrails de robustez (semgrep ausente, LLM sin key, resolucion de scope de
  Python -- shadowing, reasignacion, closures anidados -- para `secrets[].in_context`).
- No toca ningun archivo compartido (api/main.py, domain/, contracts/): PyAstExtractor
  queda deliberadamente SIN conectar en `_build_deps()` por ahora. Alex (D3) esta
  montando la integracion real del Sandbox/Executor sobre ese mismo composition root;
  el wiring del extractor se hace despues, revisando su commit, para no pisarnos y
  para que el swap tenga valor demostrable de una sola vez.
EOF
)"

echo "== Pusheando ${BRANCH} =="
git push -u origin "${BRANCH}"

PR_CREATED=0
if command -v gh >/dev/null 2>&1; then
  read -r -p "¿Crear el PR con gh ahora? [y/N] " CONFIRM_PR
  if [[ "${CONFIRM_PR}" == "y" || "${CONFIRM_PR}" == "Y" ]]; then
    gh pr create \
      --title "D1: Extractor real + target-agent (Acme)" \
      --base main \
      --head "${BRANCH}" \
      --body "$(cat <<'EOF'
## Que hace
Implementa C1 (Extractor, owner D1/Helmut) segun specs/03-components.md:
- `target-agent/`: agente vulnerable de prueba (narrativa Acme, specs/diagrams/real-case-flow.md).
- `backend/adapters/extractor/PyAstExtractor`: ast nativo + 1 regla Semgrep (con fallback si
  no esta instalado, cruzada contra data_flows) + pasada LLM opcional (no-op sin
  ANTHROPIC_API_KEY, con guardrail anti-invencion: el LLM no puede crear tools/mcp_servers
  nuevos, solo refinar campos de entidades que ast ya detecto).

## Criterios de aceptacion (specs/03-components.md #C1)
- [x] >=1 tool `shell` y >=1 `mcp_server` con `trust_level`
- [x] data_flow `user_input->shell_exec` con `sanitized: false`
- [x] valida contra `AgentArchitecture` sin errores
- [x] (T1) agregar una tool y re-extraer cambia `architecture.json` — probado agregando
      `query_database` (kind `sql`) sobre una copia real del agente

## Test plan
- `cd backend && uv run pytest -q` — 22/22 en verde (incluye test_skeleton.py existente)
- `cd backend && uv run ruff check .` — sin errores en los archivos de este PR
- `cd backend && uv run python -m adapters.extractor ../target-agent [--out architecture.json]`
  — architecture.json a mano, revisado campo por campo contra specs/01-data-contracts.md

## Pendiente (fuera de este PR, a proposito)
`PyAstExtractor` NO esta conectado todavia en `backend/api/main.py::_build_deps()` ni en
`backend/tests/test_skeleton.py` (siguen con `FakeExtractor`). Es intencional: Alex (D3)
esta montando ahora mismo la integracion real del Sandbox/Executor sobre ese mismo
composition root. El wiring del extractor se hace apenas Alex commitee/actualice esa
parte -- reviso su cambio y aplico el swap sobre eso, en vez de tocarlo en paralelo y
generar conflicto.
EOF
)"
    PR_CREATED=1
  else
    echo "PR no creado. Podes correrlo despues con: gh pr create --base main --head ${BRANCH}"
  fi
else
  echo "gh no esta disponible; crea el PR manualmente para ${BRANCH} -> main."
fi

BRANCH_URL="$(git remote get-url origin 2>/dev/null | sed -E 's#git@github.com:#https://github.com/#; s#\.git$##')/tree/${BRANCH}"

cat <<EOF

================================================================================
AVISO PARA EL EQUIPO — copia/pega esto donde coordinen (Slack/Discord/WhatsApp)
================================================================================

**D1 (Helmut) — C1 Extractor: listo y pusheado**
Rama: ${BRANCH_URL}

✅ Se hizo:
- target-agent/ real (narrativa Acme: run_shell sin sanitizar, MCP Notion, send_email,
  ACME_API_KEY en contexto).
- PyAstExtractor real (ast + 1 regla Semgrep + LLM opcional) implementando
  ArchitectureExtractorPort. Cumple los 4 criterios de aceptacion de C1 (incluye T1).
- 22 tests en verde, ruff limpio, architecture.json verificado a mano contra el contrato.

✅ Se integro:
- Nada toca archivos compartidos todavia (api/, domain/, contracts/) — el PR es
  autocontenido, sin riesgo de conflicto para nadie.

⏳ Falta acoplar (y por que):
- **Conectar PyAstExtractor en \`backend/api/main.py::_build_deps()\`** (hoy usa
  FakeExtractor) — a proposito sin tocar. @Alex(D3) ya me confirmo que esta montando
  la integracion real del Sandbox/Executor sobre ese mismo composition root, asi que
  espero a que el commitee/actualice esa parte, reviso su cambio, y ahi aplico el
  swap del extractor sobre eso — evita que los dos toquemos \`_build_deps()\` en
  paralelo y generemos conflicto.
- **@D2 (Jorge) / @D5 (Laura):** el architecture.json real ya trae mas semantica de la
  que tenia el ejemplo de la spec (\`rag\`, \`secrets[].in_context\` con evidencia real de
  uso, no un default) — aviso por si el Analista/Designer quieren aprovecharlo cuando
  les toque conectar los suyos.
- **demo-script.md** sigue sin existir en el repo (checklist de arranque, specs/04).
  Puedo escribir la parte de apertura (la narrativa Acme) cuando se arranque ese doc.

@Alex: avisame apenas pushees/mergees tu parte del Sandbox/Executor asi reviso y conecto
el extractor real detras.
================================================================================
EOF
