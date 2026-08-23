#!/usr/bin/env bash
set -euo pipefail

# Sube los 2 commits locales de develop (limpieza co.sismomesh/GPS/motion,
# guia de voz, merge de develop-alert-ingestor/develop-api ya se subieron con
# scripts/push-and-cleanup-branches.sh; este script sube lo que sigue: el
# port de mejoras del prototipo Flutter a Kotlin) y borra las 3 ramas Dart
# que ya no hacen falta.
#
# A diferencia de scripts/push-and-cleanup-branches.sh, estas 3 ramas NO son
# ancestros de develop -- son codigo Flutter/Dart ramificado de `main`, nunca
# mergeado. Se borran porque el equipo decidio quedarse 100% en Kotlin y las
# ideas realmente utiles (negociacion de MTU + multiples peers en BLE desde
# BleGattPlugin.kt, sdnnMs/pnn50 en PPG) ya se re-implementaron a mano en
# Kotlin -- ver el commit "feat(transport,ppg): portar mejoras reales..." y
# docs/validation/PHONE-READINESS.md. No hay chequeo de "is-ancestor" posible
# aqui porque nunca hubo un merge real. backup/pre-reset-main NO esta en esta
# lista a proposito -- ver AGENTS.md ("No integres en main ni
# backup/pre-reset-main"), es el backup de seguridad de main, no una rama de
# feature.
#
# Ejecutar SOLO cuando el usuario lo autorice.

REPO_DIR="/home/hell/Projects/PROYECTO FINAL PLATANUS/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

BRANCHES_TO_DELETE=(
  feat/motion-evidence
  feat/offline-triage-ppg
  eval/vitals-localization-comparison
)

echo "== Rama actual (debe ser develop) =="
git branch --show-current

echo "== Commits locales que se van a subir =="
git log --oneline origin/develop..develop

echo
echo "== Subiendo develop =="
git push origin develop

echo
echo "== Borrando ramas Dart ya extraidas (sin chequeo de merge, ver comentario arriba) =="
git fetch origin --prune
for branch in "${BRANCHES_TO_DELETE[@]}"; do
  if ! git show-ref --verify --quiet "refs/remotes/origin/$branch"; then
    echo "  $branch: ya no existe en origin, se omite"
    continue
  fi
  echo "  $branch: borrando..."
  git push origin --delete "$branch"
done

echo
echo "== Ramas remotas restantes (deberia quedar solo develop, main y backup/pre-reset-main) =="
git branch -r
