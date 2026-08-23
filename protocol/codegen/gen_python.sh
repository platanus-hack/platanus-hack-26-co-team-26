#!/usr/bin/env bash
set -euo pipefail
# Genera services/shared/src/api/protocol/ desde protocol/proto/**/*.proto
# Dueño: Miguel. TODO: invocar protoc --python_out (o grpc_tools.protoc).
echo "TODO(dueño=Miguel): python -m grpc_tools.protoc --python_out=... protocol/proto/sismomesh/v1/*.proto"
