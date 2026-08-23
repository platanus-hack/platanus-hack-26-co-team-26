#!/usr/bin/env bash
set -euo pipefail

# Renombra el proyecto de SismoMesh a HELIUS en todo el repo (paquetes Kotlin,
# proto, codigo generado, docker-compose, pyproject/package.json, docs) y
# limpia emojis/contenido decorativo poco profesional del README y docs.
# Completa project-description.md y platanus-hack-project.jsonc.
# Rama develop. Ejecutar SOLO cuando el usuario lo autorice.

REPO_DIR="/home/hell/Projects/PROYECTO FINAL PLATANUS/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

echo "== Rama actual (debe ser develop) =="
git branch --show-current

echo "== Estado antes de stagear =="
git status --porcelain=v1 | wc -l

git add -A

echo "== Resumen de cambios a commitear =="
git status --porcelain=v1 | awk '{print $1}' | sort | uniq -c

git commit -m "$(cat <<'EOF'
rebrand: renombrar proyecto de SismoMesh a HELIUS + limpieza profesional

Renombra el proyecto completo: paquetes Kotlin (co.sismomesh -> co.helius,
directorios movidos con git mv), paquete protobuf (sismomesh.v1 -> helius.v1,
codigo Java/Kotlin/Python regenerado desde cero, no parcheado, para no
corromper descriptores binarios embebidos), docker-compose (db/usuario),
pyproject.toml y package.json de cada servicio, applicationId/namespace de
Gradle, SismoMeshApp.kt -> HELIUSApp.kt, y todas las menciones en
documentacion (READMEs, ADRs, glosario, etc). Vectores dorados regenerados
con el nuevo paquete.

Excepcion intencional: docs/ppg/* preserva com.sismomesh.ppg como referencia
historica de la entrega original de Laura, con nota aclaratoria; las rutas
reales del monorepo usan co.helius.*.

Corrige de paso un bug real preexistente en protocol-ci.yml que seguia
apuntando a commonMain para el codigo de protocolo (vive en androidMain).

Limpieza de contenido no profesional: quita emojis decorativos del README
(del template original de Platanus y de encabezados propios), convierte el
checklist "Before Submitting" a casillas reales, y completa
project-description.md y platanus-hack-project.jsonc que seguian con el
placeholder "<FILL THIS>" sin llenar desde el commit inicial del organizador.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"

echo "== Commit creado =="
git log --oneline -1
git status --porcelain=v1

echo
echo "Push manual (cuando quieras publicar develop):"
echo "  cd \"$REPO_DIR\" && git push origin develop"
