#!/usr/bin/env bash
set -euo pipefail

# Commit del esqueleto inicial del monorepo (Kotlin/Android + Python FastAPI + React)
# y de la documentacion de equipo (arquitectura, division de trabajo, roadmap,
# threat model, validacion, glosario, ADRs) en la rama develop.
# Ejecutar SOLO cuando el usuario lo autorice.

REPO_DIR="/home/hell/Projects/PROYECTO FINAL PLATANUS/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

echo "== Rama actual (debe ser develop) =="
git branch --show-current

echo "== Estado antes de stagear =="
git status --porcelain=v1

git add -A

echo "== Archivos que se van a commitear =="
git status --porcelain=v1

git commit -m "$(cat <<'EOF'
feat: esqueleto inicial del monorepo + documentacion de arquitectura y equipo

Estructura completa (modulos Gradle, contratos protobuf, puertos hexagonales,
servicios backend, dashboard web, ML, simuladores, CI) segun la especificacion
tecnica del proyecto -- solo esqueleto e interfaces, sin implementacion.

Incluye documentacion de organizacion del equipo: arquitectura (docs/architecture),
division de trabajo real por persona (docs/team), roadmap por vertical slices,
modelo de amenazas, estrategia de validacion, glosario obligatorio y ADRs.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"

echo "== Commit creado =="
git log --oneline -1
git status --porcelain=v1

echo
echo "Push manual (cuando quieras publicar develop):"
echo "  cd \"$REPO_DIR\" && git push -u origin develop"
