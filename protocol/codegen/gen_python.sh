#!/usr/bin/env bash
set -euo pipefail
# Genera services/shared/src/api/protocol/ desde protocol/proto/**/*.proto
# Dueño: Miguel. Requiere protoc (sin plugins extra; --python_out es nativo).
set -x
cd "$(dirname "$0")/../.."

OUT="services/shared/src/api/protocol"
mkdir -p "$OUT"

protoc \
  --proto_path=protocol/proto \
  --python_out="$OUT" \
  protocol/proto/sismomesh/v1/*.proto

find "$OUT" -type d -exec sh -c 'test -f "$1/__init__.py" || touch "$1/__init__.py"' _ {} \;

echo "Generado en $OUT. No editar a mano — regenerar con este script."
