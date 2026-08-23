# Habeas data — de la Ley 1581 al código

**Ámbito:** `services/found_persons` (API de personas localizadas).
**Dueño:** Miguel. **Revisor obligatorio:** Helmut (cifrado break-glass) y Laura (NNA).

**Fundamento jurídico:** ver [`HABEAS-DATA-FUNDAMENTACION-JURIDICA.md`](HABEAS-DATA-FUNDAMENTACION-JURIDICA.md)
para por qué el interés vital es la única causal disponible en el caso central, qué
condiciones le impone la doctrina humanitaria, y hasta dónde llega esa lectura.

Este documento existe para que cualquiera —un revisor de PR, un abogado, un auditor
de la SIC— pueda ir de un artículo de la ley al archivo que lo implementa y al test
que lo verifica. Si una fila de estas tablas queda sin test, el cumplimiento vuelve a
ser una declaración de intenciones.

## Marco normativo

| Norma | Qué aporta |
|---|---|
| Constitución Política, art. 15 | Derecho fundamental a conocer, actualizar y rectificar |
| Ley 1581 de 2012 | Régimen general de protección de datos personales |
| Decreto 1074 de 2015 | Compila el Decreto 1377 de 2013 (reglamentario) |
| Sentencia C-748 de 2011 | Control previo de la Ley 1581; interés superior del NNA |
| Ley 1523 de 2012 | Crea el SNGRD; define qué autoridad territorial responde en un desastre (y por tanto quién puede ser `Controller`) |

Autoridad: Superintendencia de Industria y Comercio. Registro Nacional de Bases de
Datos (art. 25) — el radicado se declara en `Controller.rnbd_registration`.

## Referencias normativas

*Verificado al 23 de agosto de 2026 — cada URL se abrió y se confirmó que corresponde
al texto real de la fuente antes de ponerla aquí.*

| Fuente | URL | Tipo |
|---|---|---|
| Constitución Política de Colombia, art. 15 (derecho a la intimidad y habeas data) | https://www.mincit.gov.co/ministerio/normograma-sig/procesos-estrategicos/gestion-de-informacion-y-comunicacion/constitucion-politica/derechos/articulo-15.aspx | Oficial |
| Ley 1581 de 2012 — texto completo | https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=49981 | Oficial |
| Decreto 1074 de 2015 — Decreto Único Reglamentario del Sector Comercio, Industria y Turismo (protección de datos: Título 2, Cap. 25-26) | https://www.alcaldiabogota.gov.co/sisjur/normas/Norma1.jsp?i=62508 | Oficial |
| Sentencia C-748 de 2011, Corte Constitucional — control previo de la ley estatutaria | https://www.corteconstitucional.gov.co/relatoria/2011/c-748-11.htm | Oficial |
| Registro Nacional de Bases de Datos (RNBD), SIC | https://www.sic.gov.co/registro-nacional-de-bases-de-datos | Oficial |
| Circular Única SIC, Título V — Protección de Datos Personales | https://www.sic.gov.co/circular-unica | Oficial |
| Águeda-Muñoz del-Carpio-Toia et al. (2023). "Protección de datos de salud: el reto de la armonización legislativa en América Latina." *Rev. Cuerpo Médico HNAAA* — datos sensibles de salud bajo condiciones de emergencia/crisis en Colombia y la región, contexto relevante para el art. 6 de este documento | https://pmc.ncbi.nlm.nih.gov/articles/PMC11349313/ | Secundaria (académica) |

Las fuentes canónicas de texto legal colombiano (`funcionpublica.gov.co`,
`secretariasenado.gov.co`) fallan por certificado TLS, así que se usaron espejos
oficiales equivalentes con el mismo número de norma. El detalle del alcance de cada
verificación, incluidas las fuentes que no se pudieron recuperar y las que se
descartaron por no haberlas podido leer, está en la nota de verificación de
[`HABEAS-DATA-FUNDAMENTACION-JURIDICA.md`](HABEAS-DATA-FUNDAMENTACION-JURIDICA.md).

## Roles

| Ley 1581 | Aquí |
|---|---|
| Titular | La persona localizada — `FoundPersonRecord.subject` |
| Responsable del Tratamiento | La autoridad del incidente — `Controller` |
| Encargado del Tratamiento | Este servicio |

Sin `Controller` no hay a quién dirigirse para ejercer derechos, así que es un campo
obligatorio del registro y se expone en el aviso de privacidad.

## Principios (art. 4) → código

| Principio | Dónde vive | Test |
|---|---|---|
| Legalidad | `Consent.legal_basis` obligatorio | `test_exceptional_basis_requires_written_justification` |
| Finalidad (lit. b) | `Purpose` declarado por operación y contrastado | `test_purpose_outside_the_authorized_ones_is_denied` |
| Libertad | Autorización revocable en cualquier momento | `test_revocation_stops_all_further_disclosure` |
| Veracidad (lit. d) | Nivel de verificación mínimo para avisar a la familia | `test_unverified_finding_is_not_disclosed_to_family` |
| Transparencia (lit. e) | `GET /v1/hallazgos/{id}/accesos` | `test_access_history_lists_every_actor_that_touched_the_record` |
| Acceso restringido (lit. f) | `SCOPE_CEILING` + token ciego | `test_family_scope_gets_coarse_location_only` |
| Seguridad (lit. g) | Ed25519, X25519+ChaCha20, límite de tasa | `test_device_hourly_quota_stops_bulk_harvesting` |
| Confidencialidad | Cápsula sellada; los relays no leen | `test_signed_query_returns_a_sealed_capsule_the_phone_can_open` |
| Temporalidad (lit. c) | `Retention` + barrido de anonimización | `test_expired_retention_is_anonymized_and_no_longer_disclosed` |

## Datos sensibles (art. 5 y 6)

Se consideran sensibles la información de salud y la biométrica. En este servicio
aparecen como `DataCategory.HEALTH_RELATED` y `DataCategory.BIOMETRIC`, y se detectan
**del contenido**, no de lo que declare el formulario:

- `care_notes` con cualquier texto
- estado `at_care_facility` o `in_transfer`
- `placement.site_type == "care_facility"`
- `biometric_ref` con una URI

Solo cuatro causales del art. 6 los habilitan:

| Causal | Enum | Cuándo |
|---|---|---|
| Autorización explícita | `SUBJECT_CONSENT` | La persona puede y quiere autorizar |
| Representante legal | `LEGAL_GUARDIAN_CONSENT` | NNA o persona con capacidad limitada |
| Interés vital + incapacidad (lit. b) | `VITAL_INTEREST_INCAPACITY` | **El caso central**: atrapada o inconsciente |
| Urgencia sanitaria (art. 10 lit. c) | `HEALTH_EMERGENCY` | No requiere autorización previa |

`PUBLIC_AUTHORITY_DUTY` (art. 10 lit. a) permite tratar datos **no** sensibles sin
autorización, pero no habilita salud ni biométricos. El dominio lo rechaza:
`test_sensitive_data_under_a_basis_that_does_not_allow_it_is_rejected`.

Toda causal excepcional exige **justificación escrita** y **caducidad**. Una
excepción sin fecha de vencimiento acaba comportándose como la regla.

## Minimización por ámbito (ADR-0007)

Lo que se entrega es la intersección de tres cosas: el techo del ámbito, lo que el
Titular autorizó y lo que el registro realmente contiene.

| Categoría | `public` | `family` | `responder` | `authority` |
|---|:---:|:---:|:---:|:---:|
| Identidad (nombre) | — | sí | sí | sí |
| Documento | — | — | sí | sí |
| Ubicación | — | municipio | completa | completa |
| Contacto | — | sí | sí | sí |
| Salud | — | — | sí | sí |
| Biométrico | — | — | — | sí |

El ámbito público no recibe **ningún** dato personal, sin excepción. El marcador de
NNA viaja siempre que haya divulgación: no es un dato que se entregue de más, es lo
que le dice a quien recibe la ficha que está tratando con un menor.

Lo recortado se declara en `withheld_categories`. Recortar en silencio haría creer al
solicitante que eso es todo lo que hay.

## Derechos del Titular (art. 8)

| Literal | Derecho | Ruta |
|---|---|---|
| a | Conocer, actualizar, rectificar | `GET`/`PUT /v1/hallazgos/{id}` |
| b | Prueba de la autorización | `GET /v1/hallazgos/{id}/autorizacion` |
| c | Ser informado del uso | `GET /v1/hallazgos/{id}/accesos` |
| d | Quejarse ante la SIC | `GET /v1/habeas-data/aviso-de-privacidad` |
| e | Revocar y suprimir | `POST .../revocacion`, `DELETE /v1/hallazgos/{id}` |
| f | Acceder gratuitamente | Sin costo ni límite útil |

**Revocar no es suprimir.** Revocar detiene toda divulgación futura pero el registro
sobrevive por si hay deberes de conservación. Suprimir redacta el contenido.

**La supresión no es absoluta.** El Decreto 1074 art. 2.2.2.25.2.6, que compila el art. 9
del Decreto 1377 de 2013, dispone que la solicitud de supresión y la revocatoria "no
procederán cuando el Titular tenga un deber legal o contractual de permanecer en la base
de datos". Eso es `Retention.legal_hold`. Lo que el campo debe nombrar es **ese deber**,
no un motivo genérico, porque es exactamente lo que se le responde al Titular en el 409.

## Plazos (art. 14 y 15)

| Petición | Término | Prórroga |
|---|---|---|
| Consulta (art. 14) | 10 días hábiles | 5 días hábiles |
| Reclamo (art. 15) | 15 días hábiles | 8 días hábiles |

Se calculan al radicar y se persisten. La prórroga solo es válida si se informa
**antes** del vencimiento y con expresión de motivos.

> **Limitación conocida.** `domain/deadlines.py` excluye sábados y domingos pero no
> los festivos de la Ley 51 de 1983. El plazo calculado es por tanto **más corto** que
> el legal: se responde antes de lo exigido, que es el lado seguro por el que
> equivocarse, pero sigue siendo inexacto. Falta inyectar el calendario del año.

## El registro de accesos

Regla del proyecto (§12.3 y ADR-0007): **todo endpoint que devuelva PII escribe en
`audit_log` antes de responder.** Aquí eso ocurre dentro de los casos de uso, no en
el borde, para que ninguna ruta futura pueda saltárselo.

Cada asiento guarda actor, ámbito, acción, finalidad, justificación literal, base
legal, categorías divulgadas, resultado y canal. Los accesos **denegados** también se
auditan: son precisamente lo que un auditor quiere poder ver.

El `audit_log` es solo-append. No hay método de borrado ni de actualización en el
puerto: un registro de acceso que se puede editar no prueba nada.

## Amenazas específicas de este servicio

| Amenaza | Mitigación | Test |
|---|---|---|
| Recolección masiva de damnificados | Token ciego + sin búsqueda por texto + límite de tasa | `test_device_hourly_quota_stops_bulk_harvesting` |
| Comprobar si X está registrado | Respuesta uniforme en ámbitos bajos | `test_family_device_gets_the_same_answer_whether_the_record_exists_or_not` |
| Relay que lee datos en tránsito | Cápsula sellada X25519+ChaCha20 | `test_signed_query_returns_a_sealed_capsule_the_phone_can_open` |
| Relay que altera o alarga la cápsula | Firma Ed25519 sobre la forma canónica | `test_a_relay_tampering_with_the_capsule_breaks_the_signature` |
| Reenvío de una consulta ajena | Nonce + ventana + vigencia máxima | `test_replayed_nonce_is_rejected` |
| Copia local que sobrevive a la supresión | Lápidas firmadas + TTL de cápsula | `test_a_capsule_becomes_must_delete_after_erasure` |
| Texto libre que se cuela en un canal que se difunde | Motivo de lápida de enum cerrado | `test_free_text_delete_reason_never_reaches_the_tombstone` |
| Sustraer a un NNA diciendo ser familia | Exige representante legal o autoridad | `test_minor_is_not_disclosed_to_family_on_a_vital_interest_basis` |
| Falsa noticia de hallazgo a una familia | Nivel de verificación mínimo | `test_unverified_finding_is_not_disclosed_to_family` |
| Correlacionar a alguien entre desastres | Clave HMAC por incidente | `test_lookup_token_differs_across_incidents_for_the_same_document` |

## Lo que todavía no cumple

Honestidad sobre el estado real, para que nadie despliegue esto creyendo que está
completo:

- [ ] **Inscripción en el RNBD** (art. 25). El campo existe; el trámite no está hecho.
- [ ] **DPIA formal** con inventario de datos y flujos transfronterizos.
- [ ] **Calendario de festivos** en el cálculo de plazos (ver arriba).
- [ ] **IdP del incidente**: `DEV_TOKENS` no puede llegar a producción.
- [ ] **`audit_log` inmutable**: hoy es una tabla SQLite que un administrador puede
      editar. Necesita volcado a almacenamiento con object lock.
- [ ] **Política de retención del propio `audit_log`**: hoy crece sin límite.
- [ ] **Notificación al Titular** cuando se entró por causal excepcional y la persona
      recupera la capacidad de decidir. Hoy no hay canal, y es el pendiente de mayor
      riesgo jurídico de esta lista: que el Titular pueda conocer el Tratamiento y
      oponerse es una de las condiciones bajo las que se admite apoyarse en el interés
      vital, no un añadido posterior (§5 de la fundamentación jurídica).
- [ ] **Decidir y motivar el acceso a Salud del ámbito `responder`.** La doctrina del CICR
      restringe los datos de salud al personal sanitario o expresamente delegado; la tabla
      de arriba se los concede al rescatista. Puede haber razón operativa para mantenerlo,
      pero tiene que quedar como decisión motivada (§6).
- [ ] **Constancia de interés superior del NNA** en el asiento de auditoría. Hoy se guarda
      quién autorizó; lo que habilita el Tratamiento según C-748 es que responda al
      interés superior, y eso es lo que no queda registrado (§8).
- [ ] **Acotar `Controller`** al conjunto de autoridades que la Ley 1523 de 2012 habilita
      en el territorio, en vez de admitir cualquier valor (§7).
