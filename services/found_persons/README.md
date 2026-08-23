# services/found_persons — API de personas localizadas

**Propósito:** registrar que una persona reportada como no localizada fue **ubicada**,
y permitir que otros dispositivos de la malla lo consulten sin que eso equivalga a
repartir datos personales por el camino.

**Dueño:** Miguel. **Revisores obligatorios:** Helmut (firma, sellado, DTN) y Laura
(vocabulario y tratamiento de datos de NNA).

**Etiqueta de madurez:** `APPLICATION` — implementado y probado (95 tests), sobre
SQLite. La migración a PostgreSQL+PostGIS está detrás del puerto `RecordRepository`.

**Marco legal:** Constitución art. 15, Ley 1581 de 2012, Decreto 1074 de 2015. El
detalle de cómo cada regla se traduce en código está en
[`docs/privacy/HABEAS-DATA.md`](../../docs/privacy/HABEAS-DATA.md) y la decisión de
diseño en [ADR-0010](../../docs/architecture/ADR/0010-found-persons-habeas-data.md).

---

## Arranque

```bash
cd services/found_persons
python3 -m venv .venv && ./.venv/bin/pip install -e ".[dev]"
./.venv/bin/pytest -q                    # 95 tests
./.venv/bin/uvicorn found_persons.bootstrap.main:app --port 8010 --reload
```

Documentación interactiva en <http://localhost:8010/docs>.

Variables de entorno para un despliegue real:

| Variable | Para qué | Si falta |
|---|---|---|
| `FOUND_PERSONS_DB` | Ruta del SQLite | `:memory:` (todo se pierde al reiniciar) |
| `FOUND_PERSONS_MASTER_KEY` | Deriva la clave HMAC del token ciego | Clave de desarrollo — los tokens serían predecibles |
| `FOUND_PERSONS_SIGNING_SEED` | Semilla Ed25519 del servicio | Clave efímera — **invalida todas las cápsulas ya emitidas en cada reinicio** |

---

## Los cuatro verbos

| Verbo | Ruta | Qué hace |
|---|---|---|
| `POST` | `/v1/hallazgos` | Registra el hallazgo. Falla con 422 si el registro no sería legal de conservar. |
| `GET` | `/v1/hallazgos` y `/v1/hallazgos/{id}` | Devuelve la vista **minimizada** según el ámbito del solicitante. |
| `PUT` | `/v1/hallazgos/{id}` | Rectificación completa (art. 8 lit. a). Sube `version` y emite lápida. |
| `DELETE` | `/v1/hallazgos/{id}` | Supresión (art. 8 lit. e). Redacta la PII, deja esqueleto auditable y lápida. |

Toda ruta que toca datos personales exige dos cabeceras y escribe en `audit_log`
**antes** de responder:

```
Authorization:   Bearer <token>
X-Purpose:       family_reunification
X-Justification: El%20hermano%20pregunta%20en%20el%20punto%20de%20encuentro
```

La justificación va percent-encoded porque las cabeceras HTTP no transportan UTF-8 y
cualquier justificación en español lleva tildes. No va como parámetro de consulta a
propósito: una justificación real es PII y en la URL acabaría en el log de acceso de
cada proxy del camino.

---

## El método entre dispositivos

Es el caso de uso que el resto del servicio existe para habilitar. Un teléfono en
zona pregunta por alguien y la respuesta puede tener que cruzar teléfonos ajenos.

```
 teléfono A                    relays                    gateway + API
     │                                                        │
     │  consulta firmada (Ed25519) con token ciego            │
     ├───────────────────────────▶ ~~~~~~~~~~~~~~~~~~~~~~~~~▶ │
     │                                                        │ 1. verifica firma y acreditación
     │                                                        │ 2. anti-replay (nonce + ventana)
     │                                                        │ 3. límite de tasa por dispositivo
     │                                                        │ 4. escribe audit_log
     │                                                        │ 5. minimiza según ámbito
     │  cápsula sellada (X25519 + ChaCha20) y firmada         │ 6. sella hacia la clave de A
     │ ◀─────────────────────────  ~~~~~~~~~~~~~~~~~~~~~~~~◀──┤ 7. firma la cápsula
     │                            (bytes opacos)              │
```

| Ruta | Para qué |
|---|---|
| `POST /v1/malla/dispositivos` | Acredita un teléfono con un ámbito. Solo la autoridad del incidente. |
| `POST /v1/malla/consultas` | La consulta firmada. Devuelve la cápsula. |
| `POST /v1/malla/capsulas/verificar` | Revalida una cápsula recibida por malla: firma, vigencia, si quedó obsoleta. |
| `GET /v1/malla/lapidas` | Supresiones y revocaciones a propagar. Sincronización incremental. |

Cuatro decisiones que conviene entender antes de usarlo:

1. **Token ciego.** Se pregunta por `HMAC-SHA256(clave_del_incidente, documento)`,
   nunca por un nombre. Un dispositivo solo puede preguntar por alguien cuyo
   documento ya conoce: no hay enumeración ni pesca de datos. La clave es por
   incidente, así que el token no correlaciona a la misma persona entre desastres.

2. **Sin oráculo de existencia.** Para los ámbitos `public` y `family`, "no hay
   registro" y "hay registro pero no te corresponde" devuelven exactamente la misma
   respuesta (`no_disclosure`). Si se distinguieran, cualquiera con un documento
   ajeno podría averiguar si esa persona está en el sistema. Los ámbitos acreditados
   sí reciben la verdad operativa, porque responden por ella.

3. **Cápsula sellada y caducable.** Va cifrada hacia la clave X25519 del teléfono
   destinatario, así que los relays transportan bytes que no pueden leer, y lleva
   fecha de muerte (6 h para respondiente, 12 h para familia). Sin clave publicada
   se entrega en claro pero con el reenvío prohibido (`max_hops = 1`).

4. **Lápidas.** Sin ellas la supresión sería una promesa incumplible: el dato ya
   viajó a teléfonos que pueden estar sin conectividad. La lápida es lo único que
   puede alcanzarlos. Va firmada para que un relay no pueda fabricarla ni suprimirla,
   y no lleva PII: un dispositivo que nunca recibió una cápsula de ese registro no
   aprende nada al leerla.

---

## Derechos del Titular

| Derecho (Ley 1581 art. 8) | Ruta |
|---|---|
| lit. a — conocer, actualizar, rectificar | `PUT /v1/hallazgos/{id}` |
| lit. b — prueba de la autorización | `GET /v1/hallazgos/{id}/autorizacion` |
| lit. c — ser informado del uso | `GET /v1/hallazgos/{id}/accesos` |
| lit. d — quejarse ante la SIC | `GET /v1/habeas-data/aviso-de-privacidad` |
| lit. e — revocar y suprimir | `POST /v1/hallazgos/{id}/revocacion`, `DELETE /v1/hallazgos/{id}` |
| art. 14 y 15 — consultas y reclamos | `POST /v1/habeas-data/peticiones` |

Las peticiones se radican **sin credencial**: quien reclama puede ser justamente
alguien que no tiene ninguna y descubrió que sus datos están aquí. El plazo legal
(10 días hábiles para consultas, 15 para reclamos) se calcula y persiste al radicar,
porque vencerlo es un incumplimiento con consecuencias, no un retraso de servicio.

---

## Estructura

```
src/found_persons/
├── domain/          # Sin frameworks. Reglas de la Ley 1581 en código.
│   ├── vocabulary.py    SituationStatus — sin ALIVE/DEAD/INJURED (docs/glossary.md)
│   ├── habeas_data.py   LegalBasis, Purpose, DataCategory, Consent, Retention, Tombstone
│   ├── records.py       FoundPersonRecord + validate() + token ciego
│   ├── policies.py      decide() y project() — el único camino de salida de un dato
│   ├── mesh.py          DeviceQuery, DisclosureCapsule
│   ├── deadlines.py     Plazos en días hábiles
│   └── canonical.py     Serialización estable para firmar
├── application/     # Casos de uso y puertos
├── adapters/        # SQLite, memoria, Ed25519/X25519, FastAPI
└── bootstrap/       # Cableado. El único módulo que conoce adaptadores concretos.
```

Cada puerto tiene adaptador real y *fake* determinista, como exige `CONTRIBUTING.md`.
Las capas las verifica `lint-imports` (contratos 3 a 6 de `.importlinter`).

---

## Qué falta

- [ ] `RecordRepository` sobre PostgreSQL+PostGIS, para converger con `services/shared`.
- [ ] `Principal` desde el IdP del incidente (OIDC + rol + organización) en vez de
      `DEV_TOKENS`. **Los tokens de desarrollo no pueden llegar a producción.**
- [ ] Calendario de festivos (Ley 51 de 1983) en `DataSubjectRightsService`: sin él,
      los plazos calculados son más cortos que los legales — el lado seguro, pero
      inexacto.
- [ ] Volcado de `audit_log` a almacenamiento inmutable (MinIO con object lock).
- [ ] Cliente Kotlin en `:core` que construya la consulta firmada y abra la cápsula;
      el formato canónico ya está fijado en `domain/mesh.py` y en `protocol/`.
