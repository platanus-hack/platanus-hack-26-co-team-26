#!/usr/bin/env bash
set -euo pipefail
# Genera core/src/commonMain/kotlin/co/sismomesh/core/protocol/ desde protocol/proto/**/*.proto
# Dueño: Helmut. TODO: invocar protoc + plugin de Kotlin (protobuf-kotlin-lite).
echo "TODO(dueño=Helmut): protoc --kotlin_out=... protocol/proto/sismomesh/v1/*.proto"
