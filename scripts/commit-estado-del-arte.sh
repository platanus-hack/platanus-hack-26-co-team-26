#!/usr/bin/env bash
set -euo pipefail

# Commit del README (Estado del Arte: Comunicaciones + PPG/EMG bioingenieria)
# y de las figuras en docs/figuras-biosignals/. Ejecutar SOLO cuando el usuario lo autorice.

REPO_DIR="/home/hell/Projects/PROYECTO FINAL PLATANUS/platanus-hack-26-co-team-26"
cd "$REPO_DIR"

echo "== Rama actual =="
git branch --show-current

echo "== Estado antes de stagear =="
git status --porcelain=v1

git add README.md docs/figuras-biosignals/

echo "== Diff que se va a commitear =="
git status --porcelain=v1

git commit -m "$(cat <<'EOF'
docs: agregar estado del arte de comunicaciones y PPG/EMG al README

Sintesis propia del equipo (narrativa + formalizacion de apoyo) sobre
dimensionamiento de comunicaciones para malla de emergencia (BLE,
Wi-Fi Aware, UWB, acustico, DTN/FEC) y sobre PPG con camara+flash y
fusion con EMG para triage no diagnostico, con referencias a obras
fundacionales y literatura aplicada reciente. Incluye figuras de
apoyo en docs/figuras-biosignals/.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"

echo "== Commit creado. Estado final =="
git status --porcelain=v1
git log --oneline -1

echo
echo "Push manual (cuando quieras subirlo a origin/main):"
echo "  cd \"$REPO_DIR\" && git push origin main"
