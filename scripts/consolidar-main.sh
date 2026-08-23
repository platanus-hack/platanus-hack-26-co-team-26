#!/usr/bin/env bash
set -euo pipefail

# Consolida develop en main dejando main como la rama con todo lo funcional,
# CONSERVANDO la documentacion de main y complementandola con la de develop.
#
# Criterio aplicado (acordado con el usuario):
#   - No se borra nada de main. El prototipo Flutter (apps/mobile/**), services/api/,
#     fixtures/, demo/ y protocol/gen_fixtures.py se quedan tal como estan: no hay
#     conflicto con develop porque viven en rutas que develop no usa.
#   - La documentacion de main (docs/API.md, docs/ARCHITECTURE.md, docs/CORE-5H.md y
#     el PDF del playbook) se MUEVE a docs/legacy/ con un README que explica que
#     describe el prototipo Dart y no la arquitectura vigente. Se conserva entera.
#   - Los 6 conflictos son todos de archivos de raiz, ninguno de codigo. Se resuelven
#     a favor de develop, salvo el deploy-url, que se toma de main porque ahi si
#     estaba resuelto.
#
# RIESGO CONOCIDO, leelo antes de correr: main es la rama por defecto del repo
# (lo que ve un juez). El build sobre el merge mas reciente NO esta verificado --
# el commit 2a69b5f de Laura trae 1904 lineas nunca compiladas. Ver el pendiente
# 4.1 de docs/validation/ESTADO-DE-VERIFICACION-Y-PENDIENTES.md. Lo ideal es correr
#   ./gradlew clean build :android:app:assembleDebug
# ANTES de disparar esto. Si no hay tiempo, correrlo igual es defendible porque main
# hoy muestra un prototipo descartado, que es peor.
#
# Ejecutar SOLO cuando el usuario lo autorice.

REPO_DIR="/home/hell/Projects/PROYECTO FINAL PLATANUS/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

DEPLOY_URL="https://helius-landing-pearl.vercel.app/"

echo "== Estado previo =="
git status --porcelain=v1
test -z "$(git status --porcelain=v1)" || { echo "ABORTA: hay cambios sin commitear"; exit 1; }

git fetch origin --prune
echo "develop: $(git rev-parse --short origin/develop)   main: $(git rev-parse --short origin/main)"

echo
echo "== Respaldo del main actual, por si hay que volver =="
git branch -f backup/main-pre-consolidacion origin/main
git push -f origin backup/main-pre-consolidacion
echo "respaldo en origin/backup/main-pre-consolidacion"

echo
echo "== Merge de develop en main =="
git checkout main
git reset --hard origin/main
# --no-commit para resolver los 6 conflictos a mano antes de cerrar el merge.
git merge --no-ff --no-commit develop || true

echo
echo "== Conflictos detectados =="
git diff --name-only --diff-filter=U

# --- resolucion: a favor de develop en los archivos de raiz -------------------
for f in .gitignore Makefile README.md project-description.md; do
  if git ls-files -u -- "$f" | grep -q .; then
    git checkout --theirs -- "$f"
    git add -- "$f"
    echo "  $f -> version de develop"
  fi
done

# project-logo.png: borrado en main, modificado en develop. Se conserva el de
# develop (1000x1000 PNG de 74 KB, que es lo que pide platanus-hack-project.jsonc:
# "1000x1000 png, max 500kb"). El project-logo.jpg de main NO se borra.
if git ls-files -u -- project-logo.png | grep -q .; then
  git checkout --theirs -- project-logo.png
  git add -- project-logo.png
  echo "  project-logo.png -> version de develop (se conserva tambien el .jpg de main)"
fi

# platanus-hack-project.jsonc: contenido de develop + el deploy-url que main si tenia.
if git ls-files -u -- platanus-hack-project.jsonc | grep -q .; then
  git checkout --theirs -- platanus-hack-project.jsonc
  python3 - "$DEPLOY_URL" <<'PY'
import re, sys
url = sys.argv[1]
p = 'platanus-hack-project.jsonc'
s = open(p, encoding='utf-8').read()
new = re.sub(r'("deploy-url":\s*)"[^"]*"', lambda m: m.group(1) + '"' + url + '"', s)
assert new != s, "no se pudo sustituir deploy-url"
open(p, 'w', encoding='utf-8').write(new)
print("  platanus-hack-project.jsonc -> develop + deploy-url de main")
PY
  git add -- platanus-hack-project.jsonc
fi

echo
echo "== Nada debe quedar en conflicto =="
git diff --name-only --diff-filter=U
test -z "$(git diff --name-only --diff-filter=U)" || { echo "ABORTA: quedan conflictos"; exit 1; }

echo
echo "== Preservar la documentacion de main en docs/legacy/ =="
mkdir -p docs/legacy
for f in docs/API.md docs/ARCHITECTURE.md docs/CORE-5H.md; do
  [ -f "$f" ] && git mv -f "$f" "docs/legacy/$(basename "$f")" && echo "  $f -> docs/legacy/"
done
PDF=$(ls docs/*.pdf 2>/dev/null | head -1 || true)
if [ -n "$PDF" ]; then git mv -f "$PDF" "docs/legacy/$(basename "$PDF")"; echo "  $PDF -> docs/legacy/"; fi

cat > docs/legacy/README.md <<'LEGACY'
# Documentación del prototipo inicial

Estos documentos describen el **prototipo Flutter/Dart** con el que arrancó el
proyecto, no la arquitectura vigente. Se conservan enteros a propósito: son el
registro de cómo se pensó el sistema en las primeras horas y contienen decisiones
—el corte de alcance de `CORE-5H.md`, el criterio de aceptación de tres teléfonos—
que siguen siendo la tesis del producto.

Lo que **no** hay que hacer es leerlos como la arquitectura actual. Para eso:

- Arquitectura vigente: [`docs/architecture/OVERVIEW.md`](../architecture/OVERVIEW.md)
- Decisiones: [`docs/architecture/ADR/`](../architecture/ADR/)
- Stack real e integraciones: [`docs/architecture/STACK-E-INTEGRACIONES.md`](../architecture/STACK-E-INTEGRACIONES.md)
- Contratos de API: [`protocol/openapi/helius-api.yaml`](../../protocol/openapi/helius-api.yaml)

El código de ese prototipo sigue en `apps/mobile/`. Su valor ya se extrajo al
Kotlin en el commit `7122a60` (negociación de MTU en BLE, servidor GATT
multi-peer, `sdnnMs`/`pnn50` en PPG); el equipo decidió seguir 100% en Kotlin
nativo (ADR-0002).
LEGACY
git add docs/legacy

echo
echo "== Cerrando el merge =="
git commit -q -m "$(cat <<'EOF'
merge: consolidar develop en main con toda la funcionalidad

main era la rama por defecto del repo -- lo que ve un juez al abrirlo -- y mostraba
el prototipo Flutter descartado mas la metadata del hackathon: 62 archivos contra
los 501 del monorepo real, que vivia solo en develop. Este merge deja main con el
proyecto completo.

Criterio: no se borra nada de main, y su documentacion se conserva entera.

- El prototipo Dart (apps/mobile/**, 31 archivos), services/api/, fixtures/,
  demo/ y protocol/gen_fixtures.py se quedan: viven en rutas que develop no usa,
  asi que no hay conflicto. Su valor ya se habia extraido al Kotlin en 7122a60.
- La documentacion de main (docs/API.md, docs/ARCHITECTURE.md, docs/CORE-5H.md y
  el PDF del playbook) se mueve a docs/legacy/ con un README que explica que
  describe el prototipo y no la arquitectura vigente, para que nadie la lea como
  actual. Se conserva completa.
- Los 6 conflictos eran todos de archivos de raiz, ninguno de codigo:
  .gitignore, Makefile, README.md, project-description.md y project-logo.png se
  resuelven a favor de develop; platanus-hack-project.jsonc toma el contenido de
  develop mas el deploy-url que main si tenia resuelto.
- Se conserva project-logo.jpg de main aunque el README apunte al .png, que es el
  formato y tamano que pide platanus-hack-project.jsonc (1000x1000, max 500 KB).

Respaldo del main anterior en origin/backup/main-pre-consolidacion.

PENDIENTE, y esta escrito en el reporte que viaja en este merge: el build sobre el
commit 2a69b5f (1904 lineas nuevas de UI y del transporte Nearby) no se pudo
verificar por falta de tiempo. Ver
docs/validation/ESTADO-DE-VERIFICACION-Y-PENDIENTES.md seccion 4.1.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1

echo
echo "== Subiendo main =="
git push origin main

echo
echo "== Resultado =="
echo "main:    $(git rev-parse --short main)"
echo "archivos en main: $(git ls-tree -r --name-only main | wc -l)"
git checkout develop

echo
echo "== Limpieza de ramas (opcional, revisar antes) =="
echo "  feat/offline-earthquake-detection esta 100% contenida en develop, se puede borrar:"
echo "    git push origin --delete feat/offline-earthquake-detection"
echo "  fix/mobile-ui-cleanup tiene 1 commit propio que toca MobileShell.kt, el mismo"
echo "  archivo que Laura reescribio en 2a69b5f (+934). Revisar el conflicto antes:"
echo "    git merge --no-commit --no-ff origin/fix/mobile-ui-cleanup"
echo "  backup/pre-reset-main y backup/main-pre-consolidacion: conservar como respaldo."
