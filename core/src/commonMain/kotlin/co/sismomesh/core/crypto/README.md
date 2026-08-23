# core/crypto

**Propósito:** identidad Ed25519, handshake X25519+HKDF (patrón Noise XX), cifrado de
payload (ChaCha20-Poly1305 / AES-GCM con aceleración HW), firma de bundles
(`Sign_Kpriv(SHA-256(header||payload))`), HMAC truncado para beacons, break-glass
(`EmergencyDataPolicy`). Ver `docs/security/THREAT-MODEL.md` § 14.2.

**Puertos que expone:** implementación de apoyo para `IdentityPort` (declarado en
`core/application/ports/SystemPorts.kt`).

**Dueño:** Helmut. **Revisor obligatorio:** Miguel (consumo desde `services/shared/src/api/application/ports.py::CryptoVerifierPort`).

**Etiqueta de madurez:** `ENGINEERING` — criptografía estándar, requiere implementación cuidadosa y revisión de pares antes de exponerse.
