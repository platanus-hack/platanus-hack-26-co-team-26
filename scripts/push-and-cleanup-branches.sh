#!/usr/bin/env bash
set -euo pipefail

# Sube los 6 commits locales de develop (limpieza co.sismomesh/GPS/motion,
# guia de voz, merge de develop-alert-ingestor y develop-api de Miguel) y
# borra las ramas remotas que ya quedaron 100% integradas en develop, para
# dejar el repo solo con develop y main.
#
# Verifica cada rama contra origin/develop antes de borrarla -- si alguna
# no esta completamente mergeada, el script se detiene ahi sin tocar el
# resto. Ejecutar SOLO cuando el usuario lo autorice.

REPO_DIR="/home/hell/Projects/PROYECTO FINAL PLATANUS/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

BRANCHES_TO_DELETE=(
  gps
  feat/motion-alert-evidence
  develop-alert-ingestor
  develop-api
  integration/helios-complete
)

echo "== Rama actual (debe ser develop) =="
git branch --show-current

echo "== Commits locales que se van a subir =="
git log --oneline origin/develop..develop

echo
echo "== Subiendo develop =="
git push origin develop

echo
echo "== Verificando y borrando ramas ya integradas =="
git fetch origin --prune
for branch in "${BRANCHES_TO_DELETE[@]}"; do
  if ! git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    echo "  $branch: ya no existe en origin, se omite"
    continue
  fi
  if git merge-base --is-ancestor "origin/$branch" origin/develop; then
    echo "  $branch: mergeada en develop, borrando..."
    git push origin --delete "$branch"
  else
    echo "  $branch: NO esta completamente mergeada en develop -- me detengo aqui, revisa a mano" >&2
    exit 1
  fi
done

echo
echo "== Ramas remotas restantes =="
git branch -r
