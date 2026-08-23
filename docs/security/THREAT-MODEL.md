# Seguridad y modelo de amenazas

**Dueño:** Helmut (criptografía y transporte). **Revisor obligatorio:** Miguel (exposición en backend/dashboard).

## Amenazas contempladas

| Amenaza | Mitigación |
|---|---|
| Superviviente falso / *victim spoofing* | Identidad Ed25519 por instalación; bundles firmados; reputación por gateway. |
| *Replay* de bundles antiguos | `sequence` monótono + `expires_at` + `disaster_id` + ventana de aceptación. |
| Rastreo de personas en tiempos normales | Pseudónimo **efímero** por desastre; en modo `READY` no se emite beacon identificable. |
| Nodos Sybil | Límite de tasa por gateway, coste computacional en el registro, correlación de observaciones. |
| Gateway malicioso | Los bundles vienen firmados por el origen; el gateway no puede alterar contenido, solo añadir metadatos propios. |
| Rescatista falso | Certificados emitidos por la autoridad del incidente; datos sensibles van cifrados para la clave de rescate. |
| Modificación de ubicación/estado | Firma sobre `header||payload`. |
| Inundación de rutas | `max_copies`, Bloom filters, presupuesto de energía por par. |
| Mensaje "a salvo" falsificado | Firma + regla: `SAFE` nunca borra evidencia previa; `HELP` solo la anota. |
| Robo de datos médicos | Cifrado extremo a extremo hacia familia/autoridad; los relays transportan bytes opacos. |
| APK modificado/reempaquetado | Play Integrity API en el registro de nodo; clave de firma en Keystore respaldado por hardware. |

## Criptografía

- **Identidad persistente:** Ed25519 en Android Keystore (StrongBox si existe).
- **Pseudónimo:** `HKDF(identidad, disaster_id, epoch)`.
- **Handshake:** X25519 + HKDF (patrón tipo Noise XX).
- **Cifrado de payload:** ChaCha20-Poly1305 (o AES-GCM con aceleración HW).
- **Firma de bundle:** `Sign_Kpriv(SHA-256(header||payload))`.
- **Beacon:** HMAC truncado a 4 bytes con clave derivada de sesión del incidente.
- **Base local:** SQLCipher, clave derivada y protegida por Keystore.

**Break-glass (identidad):** ver ADR-0008. El usuario define previamente una
`EmergencyDataPolicy` (`protocol/proto/sismomesh/v1/identity.proto`) — qué
campos (nombre, notas médicas, contacto de emergencia) se cifran para cada
familiar vinculado y consentido, y cuáles para la autoridad de rescate del
incidente. Son destinatarios **independientes**: un familiar puede ver el
nombre sin que eso implique que la autoridad también lo vea, y viceversa. El
contenido en claro (`IdentityProfilePlaintext`) solo existe dentro de un
`EncryptedIdentityProfile` cifrado por destinatario; los nodos intermedios lo
transportan como bytes opacos, sin poder leerlo. El beacon y los bundles de
estado/pulso/movimiento **siguen sin nombre**, sin excepción — el perfil de
identidad viaja por un canal separado (sync directo nodo→backend cuando hay
conectividad, no hop-by-hop por la malla).

## Privacidad y cumplimiento

Artefactos obligatorios en `docs/privacy/`:

- **DPIA** con inventario de datos, base legal y flujos transfronterizos.
- **Política de retención:** datos crudos con caducidad (p. ej. 30 días operativos), luego anonimización irreversible para investigación.
- **Consentimiento granular:** ubicación histórica, perfil de salud, compartición familiar, uso para investigación — cada uno revocable por separado.
- **Minimización:** el beacon no lleva PII; el perfil sensible viaja cifrado y solo si el usuario lo autorizó.
- **Registro de acceso:** cualquier consulta de PII queda en `audit_log` con actor, justificación y sello temporal.
- **Declaración de seguridad de datos de Play Store** coherente con lo anterior.

En Colombia los datos de salud son datos sensibles bajo la Ley 1581; existe la
excepción de urgencia vital, pero eso **no** equivale a publicarlos en Internet
(ver ADR-0007, tres niveles de exposición del dashboard).
