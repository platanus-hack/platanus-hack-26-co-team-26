# core/crypto (androidMain)

**Implementación real** (no stub) usando `javax.crypto`/`java.security` de la
JVM — JVM-only, por eso vive en `androidMain` y no en `commonMain` (mismo
razonamiento que `core/protocol`, ver ese README). `core/domain`/`core/dtn` en
`commonMain` nunca importan esto directo: reciben funciones inyectadas (p. ej.
`BundleFactory(payload, signer: (ByteArray) -> ByteArray)`) o lo consumen a
través de `IdentityPort` (`core/application/ports/SystemPorts.kt`).

| Archivo | Contenido |
|---|---|
| `Hkdf.kt` | HKDF (RFC 5869) sobre HMAC-SHA256, sin dependencias externas |
| `Identity.kt` | `Ed25519Identity` (implementa `IdentityPort`), `PseudonymDeriver`, `X25519Handshake`, `PayloadCipher` (ChaCha20-Poly1305), `BundleSigner`, `BeaconAuthenticator` |

**Pendiente antes de producción (marcado con TODO en el código):**

1. Respaldar `Ed25519Identity` con Android Keystore (StrongBox si existe) en
   vez de mantener la clave privada en heap Java.
2. Ampliar `IdentityPort.Handshake` para exponer la pública efímera propia
   (hoy resuelto en `X25519Handshake.performReturningOwnPublic`, fuera del puerto).
3. Verificar disponibilidad de `Ed25519`/`X25519` por API level en la matriz de
   dispositivos (`docs/validation/VALIDATION.md`); si falta en algún
   fabricante/API, sumar BouncyCastle como proveedor JCA — no reinventar la
   primitiva.
4. Implementar el cifrado del `EncryptedIdentityProfile` (ADR-0008,
   `protocol/proto/helius/v1/identity.proto`) reutilizando
   `X25519Handshake` + `PayloadCipher` contra la clave pública de cada
   destinatario (familia/autoridad) — aún no escrito.

**Dueño:** Helmut. **Revisor obligatorio:** Miguel (consumo desde
`services/shared/src/api/application/ports.py::CryptoVerifierPort`).

**Etiqueta de madurez:** `ENGINEERING` — primitivas estándar bien elegidas,
pendiente de auditoría de seguridad antes de exponerse a un dispositivo real.
