#!/usr/bin/env bash
set -euo pipefail

# Commit de la implementacion real de transporte BLE, motor DTN, criptografia
# y el puente dominio<->protobuf (BundleWireCodec), mas la correccion de
# bugs encontrados por revision manual y el criterio de "listo para telefono"
# (docs/validation/PHONE-READINESS.md). Rama develop.
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
feat(transport): motor DTN, cripto y transferencia GATT real + fixes

Implementa de verdad (no stubs) core/dtn (BundleStore, InventoryBloom,
ForwardingScorer, PriorityQueue, EncounterStateMachine, DyingGasp),
core/crypto (Ed25519, X25519+HKDF, ChaCha20-Poly1305, firma de bundles,
HMAC de beacon) y android/transport (BleTransport, BleGattServer/Client con
protocolo GATT simetrico de intercambio de Bloom filter + bundles, chunked).

Agrega BundleWireCodec: puente entre el modelo de dominio y las clases
protobuf generadas -- sin el no habia forma de transmitir un Bundle real.

Corrige protocol/*.proto: import circular bundle.proto<->status.proto
(extraido a common.proto), mas altitud/AltitudeSource para localizacion 3D
(ADR-0009) e identity.proto para break-glass de identidad (ADR-0008).

Destapa el test de escenario A->B->C->R (ya no @Ignore) con
InMemoryBundleStore. Genera 5 vectores dorados reales via protoc.

Corrige 9 bugs reales encontrados por revision manual linea a linea (no
compilados en este entorno, sin JDK/Android SDK disponible): presupuesto de
BLE advertising excedido, callbacks GATT que resolvian exito sin revisar
status, KeyAgreement con nombre de algoritmo incorrecto, UUID de servicio
divergente entre advertising y GATT real, UUID sin patron de compresion,
onCharacteristicChanged con firma API 33+ que nunca se dispara en minSdk 26,
notificaciones GATT sin pacing. Detalle completo en
docs/validation/PHONE-READINESS.md, con la advertencia explicita de que
falta correr ./gradlew (L0-L3) antes de confiar en este codigo en un
telefono real.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"

echo "== Commit creado =="
git log --oneline -1
git status --porcelain=v1

echo
echo "Push manual (cuando quieras publicar develop):"
echo "  cd \"$REPO_DIR\" && git push origin develop"
