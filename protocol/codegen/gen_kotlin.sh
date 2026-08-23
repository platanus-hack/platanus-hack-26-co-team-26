#!/usr/bin/env bash
set -euo pipefail
# Genera las clases Java (java_out) y las extensiones DSL de Kotlin (kotlin_out)
# desde protocol/proto/**/*.proto hacia core/src/androidMain/{java,kotlin}.
#
# Por qué androidMain y no commonMain: el runtime de protobuf-java es JVM-only,
# no multiplatform. Con solo androidMain activo (ver core/src/iosMain/README.md)
# esto es seguro; en Fase 2 (iOS) este código deberá quedar detrás de un puerto
# de (de)serialización con `expect`/`actual`, o iosMain usará SwiftProtobuf.
#
# Requiere protoc >= 26 (soporta --kotlin_out nativo, sin plugin externo).
# Dueño: Helmut.
set -x
cd "$(dirname "$0")/../.."

JAVA_OUT="core/src/androidMain/java"
KOTLIN_OUT="core/src/androidMain/kotlin"

mkdir -p "$JAVA_OUT" "$KOTLIN_OUT"

protoc \
  --proto_path=protocol/proto \
  --java_out="$JAVA_OUT" \
  --kotlin_out="$KOTLIN_OUT" \
  protocol/proto/helius/v1/*.proto

echo "Generado en $JAVA_OUT y $KOTLIN_OUT. No editar a mano — regenerar con este script."
