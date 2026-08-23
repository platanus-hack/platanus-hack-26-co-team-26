# ADR-0008: Identidad pseudónima en la malla, nombre solo por break-glass consentido (familia y/o autoridad)

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** Helmut (protocolo/criptografía)

## Contexto

El beacon y los bundles en claro usan un `ephemeral_id` pseudónimo — ningún
relay intermedio puede leer nombre ni identidad (ver `docs/security/THREAT-MODEL.md`,
regla de minimización). Eso protege contra rastreo y robo de datos médicos, pero
plantea una pregunta legítima: **si un familiar vinculó su cuenta con
consentimiento antes del desastre, ¿tiene derecho a saber quién es su familiar
cuando aparece en la malla?** La respuesta del equipo es sí — no solo la
autoridad de rescate.

## Decisión

El *break-glass* (ya previsto en el diseño original, Sección 14.2) se formaliza
con **dos destinatarios independientes**, cada uno con su propia clave y su
propio blob cifrado — nunca un solo blob "para cualquiera":

- **Familia:** claves X25519 de cada contacto que el usuario vinculó y aceptó
  *antes* del desastre (`/familia`, vínculo consentido — ADR-0007).
- **Autoridad de rescate:** clave pública de la autoridad activa del incidente.

El usuario define en modo "Preparación" una `EmergencyDataPolicy`
(`protocol/proto/helius/v1/identity.proto`) que decide, campo por campo, qué
ve cada destinatario: `share_name_with_family`, `share_name_with_authority`,
`share_medical_notes_with_family`, etc. El contenido real
(`IdentityProfilePlaintext`: nombre, notas médicas, contacto de emergencia) solo
existe **dentro** del `ciphertext` de un `EncryptedIdentityProfile` — nunca como
mensaje propio del protocolo, para que ningún relay, log o mensaje intermedio
pueda exponerlo por accidente.

El perfil cifrado **no viaja hop-by-hop por la malla** como los bundles de
estado/pulso: se sincroniza del nodo (o de un gateway que lo transporta) al
backend cuando hay conectividad (mismo campo `encrypted_profile`+`key_policy`
que ya existía en `services/shared/src/api/domain/models.py::Node`), y el
backend entrega a cada visor (`/familia`, `/ops`) solo el blob cifrado para su
propia clave — el backend tampoco puede leerlo.

## Consecuencias

- La vista pública (`/mapa`) sigue sin nombre, sin excepción — eso no cambia (ADR-0007).
- Un familiar con vínculo consentido puede ver el nombre si el usuario lo
  autorizó; una autoridad de rescate puede ver un subconjunto potencialmente
  distinto (p. ej. notas médicas sí, contacto de emergencia no).
- Si el usuario nunca configuró una `EmergencyDataPolicy` (no tuvo tiempo, o no
  quiso), el sistema **no infiere** consentimiento — se muestra pseudónimo y
  nada más, en cualquier vista.
- Aumenta la superficie de gestión de claves (una por familiar vinculado); se
  acepta porque es la única forma de dar acceso diferenciado sin un servidor
  central que pueda leer identidades.
