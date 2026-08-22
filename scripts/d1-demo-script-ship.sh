#!/usr/bin/env bash
# Sube demo-script.md como una rama chica y separada del PR de C1 (no le mete scope creep
# a un PR que ya esta en revision). Corre esto VOS.
set -euo pipefail

REPO_DIR="/home/hell/Projects/PlatanusDevelopment/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

BRANCH="d1-demo-script"
FILES=("demo-script.md" "scripts/d1-demo-script-ship.sh")

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

echo "== Agregando demo-script.md =="
git add -- "${FILES[@]}"

echo "== Esto es lo que se va a commitear =="
git status --short

read -r -p "¿Confirmar commit? [y/N] " CONFIRM
if [[ "${CONFIRM}" != "y" && "${CONFIRM}" != "Y" ]]; then
  echo "Cancelado. Los archivos quedan en staging, sin commitear."
  exit 0
fi

git commit -m "$(cat <<'EOF'
docs: extraer demo-script.md desde specs/04-team-plan.md

- Mismo guion de 4 minutos ya acordado por el equipo, ahora en su propio archivo para
  poder firmarlo (checklist de arranque, specs/04-team-plan.md) sin mezclarlo con el
  resto del plan.
- Agrega una tabla de estado real por beat (que componente ya esta listo, cual falta) y
  el link al procedimiento de T1 en vivo ya probado en target-agent/README.md y
  backend/tests/test_extractor.py.
- No cambia el contenido del guion acordado, solo lo reorganiza y le agrega trazabilidad.
EOF
)"

echo "== Pusheando ${BRANCH} =="
git push -u origin "${BRANCH}"

if command -v gh >/dev/null 2>&1; then
  read -r -p "¿Crear el PR con gh ahora? [y/N] " CONFIRM_PR
  if [[ "${CONFIRM_PR}" == "y" || "${CONFIRM_PR}" == "Y" ]]; then
    gh pr create \
      --title "docs: demo-script.md" \
      --base main \
      --head "${BRANCH}" \
      --body "Extrae el guion del demo ya acordado en specs/04-team-plan.md a su propio archivo para que el equipo lo firme (checklist de arranque). Sin cambios de contenido, solo estructura + estado real por beat."
  else
    echo "PR no creado. Podes correrlo despues con: gh pr create --base main --head ${BRANCH}"
  fi
else
  echo "gh no esta disponible; crea el PR manualmente para ${BRANCH} -> main."
fi
