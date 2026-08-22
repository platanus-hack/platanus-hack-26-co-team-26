# SismoMesh — Núcleo en 5 horas

> Corte de alcance sobre `docs/ARCHITECTURE.md`. El playbook original planifica 36 h; esto **no es
> una compresión, es una amputación deliberada**. Todo lo que no aparezca en §2 como DENTRO está
> fuera hasta que el núcleo esté verde y repetible.

---

## 1. Qué significa "sólido" en 5 horas

Una sola frase, y es el criterio de aceptación completo:

> **Tres teléfonos Android. El A está en modo avión, marca TRAPPED y genera un bundle firmado.
> El B lo recibe por proximidad y lo guarda. Se mata la app de B y se reabre: el bundle sigue ahí.
> El B se cruza con el C, que recibe el bundle de A *aunque A ya no esté al alcance*. El C tiene
> Internet y lo sube. El dashboard muestra a A con su estado, ubicación, batería, ruta de saltos y
> firma verificada.**

Y desde el dashboard se descarga un **CSV priorizado para Cruz Roja** con los críticos primero.

Si eso corre tres veces seguidas sin tocar la base de datos a mano, hay producto. Nada más cuenta
como núcleo.

**Lo que el jurado debe entender del núcleo:** la información crítica sobrevive a la pérdida de
infraestructura. Esa es toda la tesis, y se demuestra sin un solo sensor biométrico.

---

## 2. El corte

| DENTRO — las 5 horas | FUERA — después del núcleo |
|---|---|
| App Flutter única, 3 roles en runtime (víctima / relay / gateway) | Fallback BLE GATT nativo |
| Transporte Nearby Connections | Wi-Fi Aware explícito, UWB, acústico `ggwave` |
| `EmergencyBundle` **v1 completo** firmado (Ed25519 + SHA-256), con los campos aún no medidos en `null` | *Implementación* de PPG por cámara y SQI — el campo ya existe |
| Store SQLite que sobrevive reinicio | *Implementación* de evidencia de movimiento — el campo ya existe |
| Store-carry-forward + dedupe por `bundle_id` + TTL | Localización por zona de confianza / RF walk |
| Activación manual de incidente + estados SAFE/HELP/TRAPPED | Pack de voz offline (ElevenLabs) |
| Upload al gateway con idempotencia | Análisis con Claude |
| Backend FastAPI con ingest + verificación de firma | Vista familiar / mapa público |
| Dashboard con mapa, lista de nodos y timeline (polling) | WebSocket en vivo, grafo de peers, heatmap |
| Consola de debug: `bundle_id`, seq, hops, transporte, resultado | Copy budget adaptativo, Bloom filter |
| Detección de `capabilities` por teléfono | Fusión de sensores, grafo de proveniencia avanzado |
| **Exportación a rescatistas** (JSON/CSV/GeoJSON priorizado) | Integración automática con sistemas de Cruz Roja / SGC |
| Registro de rechazos: manipulación y suplantación detectadas | PKI real, revocación de claves |

**Sobre el Bloom filter y el copy budget:** con 3 teléfonos, el inventario cabe en una lista de IDs
plana. El Bloom filter resuelve un problema de escala que el demo no tiene. Va al backlog, y la
interfaz `inventoryDigest()` se conserva para que entre después sin refactor.

---

## 3. Revisiones de ADR forzadas por el timebox

Cinco decisiones de `ARCHITECTURE.md` cambian. No porque estuvieran mal, sino porque el presupuesto
de tiempo es otro. **Todas son reversibles después del núcleo.**

| # | Decisión original | En 5 h | Por qué |
|---|---|---|---|
| ADR-02 | Nearby P0 + BLE GATT fallback | **Nearby solo.** BLE GATT no se toca | Un plugin nativo Kotlin es 3-4 h de un senior: el 70% del presupuesto en un plan B |
| ADR-03 | CBOR canónico | **JSON canónico transmitido como `payload_b64`** | Ver §6: elimina un bug cross-lenguaje y se depura leyéndolo |
| ADR-04 | Drift (codegen) | **`sqflite` con SQL a mano** | `build_runner` con 5 personas en paralelo es un generador de conflictos, no de código |
| ADR-05 | Riverpod + freezed (codegen) | **Riverpod con providers manuales, modelos escritos a mano** | Cero `build_runner` en el camino crítico. Un `part` desincronizado a la hora 3 cuesta 40 min |
| — | PostGIS + WebSocket | **SQLite + polling cada 2 s** | El playbook ya declara polling como fallback válido. Levantar PostGIS es infra, no producto |

También se colapsa el monorepo: **nada de cinco `packages/` con `pubspec` propio.** El núcleo vive
en `apps/mobile/lib/` con subcarpetas por dueño, más `services/api` y `apps/operations-web`. La
ceremonia de paquetes se paga sola en un proyecto de semanas; en 5 h sólo se paga.

---

## 4. Hora 0 — los 10 minutos que pueden invalidar este plan

Verificar **antes** de escribir una línea. Cualquiera de estos en rojo cambia el plan, no el ánimo:

- [ ] **¿Cuántos teléfonos Android físicos hay?** Nearby Connections **no funciona en emulador**.
      Con 2 hay demo A→B. Con 3 hay historia completa A→B→C. Con 1 no hay proyecto: cambiar de idea ya.
- [ ] **¿Tienen Google Play Services actualizado?** Nearby depende de GMS.
- [ ] **¿Hay cables USB de datos** (no sólo de carga) y depuración USB habilitada?
- [ ] **¿Alguien ya tiene Flutter + Android SDK funcionando?** En esta máquina **no están instalados**.
      Instalarlos desde cero es ~45 min: el 15% del presupuesto.
- [ ] ¿Los teléfonos están sobre 60% de batería?

**Consecuencia inmediata del cuarto punto:** quien ya tenga Flutter hace el scaffold y lo commitea en
los primeros 15 minutos, para que los demás clonen en vez de esperar su propia instalación.
Y lo más importante: **D3 y D5 no necesitan Flutter en absoluto.** Backend y dashboard arrancan al
minuto 0. Sólo tres personas pelean con el toolchain de Android.

---

## 5. Reparto — 5 devs, 5 horas

El riesgo dominante ya no es técnico: es **cinco personas editando la misma app Flutter**. Por eso
el reparto es por carpeta, y las carpetas no se cruzan.

| Dev | Dueño exclusivo de | Entrega el núcleo |
|---|---|---|
| **D1 · TL / Integración** | `lib/app/`, `lib/store/` | Shell de la app, roles, `BundleStore` en sqflite, loop DTN, APK. Dueño del merge |
| **D2 · Transporte** | `lib/transport/`, `android/` | Nearby: advertise, discover, connect, enviar/recibir bytes. Permisos. Foreground service |
| **D3 · Protocolo + Backend** | `lib/protocol/`, `services/api/` | Modelo del bundle, bytes canónicos, hash, Ed25519. FastAPI: ingest idempotente, consulta y exportación de triage |
| **D4 · UI** | `lib/ui/` | Preflight de permisos, pantalla de emergencia, lista de peers, consola de debug |
| **D5 · Dashboard + Demo** | `apps/operations-web/`, `demo/` | Mapa, nodos, timeline con polling. Deploy. Script de reset y ensayos |

D4 no tiene trabajo de señales en el núcleo — PPG y movimiento están fuera. Su valor en estas 5 h es
que **la app se vea terminada**, que es literalmente lo que el jurado mira. Trabaja contra los
fixtures de D3 desde el minuto 20, sin esperar a que el transporte funcione.

---

## 6. Contrato — `EmergencyBundle` v1 completo

D3 lo congela a los 30 minutos y publica 3 fixtures: uno válido, uno con firma rota, uno duplicado.

**El esquema entra completo desde la hora 0.** No hay versión "lite". Los campos que el núcleo no
mide todavía viajan en `null` o `[]`, con su forma ya definida y documentada. Lo que está fuera de
las 5 h no es el campo: es la implementación que lo llena.

Esto cuesta ~20 minutos extra a D3 y elimina tres problemas: el backend no migra esquema, el
dashboard de D5 renderiza los estados "sin dato" desde el principio (que es donde suelen aparecer
los bugs de UI a las 4 h), y D4 después sólo escribe un valor donde ya había un hueco.

**Sobre**, mutable, no firmado:

```json
{
  "v": 1,
  "bundle_id": "0191f3a2-...",
  "payload_b64": "eyJpbmNpZGVudF9pZCI6...",
  "payload_hash": "9f86d081...",
  "signer_key_id": "n7Qk2v...",
  "signer_pubkey_b64": "3BpVvY2r...",
  "signature": "MEUCIQD...",
  "relay": {
    "hop_count": 2,
    "received_from": "n7Qk2v",
    "transport": "nearby",
    "rssi": -67,
    "gateway_position": null
  }
}
```

**Payload**, JSON canónico (claves ordenadas), lo que realmente se firma:

```json
{
  "incident_id": "demo-bogota-01",
  "node_pseudonym": "n7Qk2v",
  "seq": 3,
  "created_at": "2026-08-22T17:04:00Z",
  "ttl_s": 86400,
  "priority": 0,

  "status": "TRAPPED",
  "user_reported": true,

  "location": {
    "lat": 4.6533, "lon": -74.0836, "accuracy_m": 12.0,
    "source": "gnss", "measured_at": "2026-08-22T17:03:41Z"
  },

  "evidence": {
    "motion": null,
    "ppg": null,
    "peers": []
  },

  "device": {
    "battery_pct": 78,
    "capabilities": {
      "nearby": true, "ble_gatt": false, "wifi_aware": false,
      "uwb": false, "camera": true, "gnss": true
    },
    "app_version": "0.1.0"
  }
}
```

### Forma de los campos que hoy van vacíos

D4 los llena después sin tocar nada más. D5 ya puede maquetar contra esto:

```jsonc
"motion": {
  "detected": true, "pattern": "deliberate_shake", "confidence": 0.82,
  "window_s": 10, "provenance": "MEASURED", "observed_at": "..."
},
"ppg": {
  "hr_bpm": 112, "sqi": 0.71, "waveform_ref": null,
  "provenance": "DERIVED", "measured_at": "..."
},
"peers": [
  { "node_pseudonym": "aQ91xR", "rssi": -67, "transport": "nearby",
    "provenance": "MEASURED", "observed_at": "..." }
]
```

**`capabilities` sí se llena en el núcleo**, y es casi gratis: D2 ya necesita detectar qué soporta
cada teléfono para el router de transporte. Además cubre desde la hora 0 el gate del playbook
*unsupported != simulated success* — la UI oculta lo que el hardware no tiene, en vez de fingirlo.

> [!IMPORTANT]
> **`null` significa "no medido". Nunca cero, nunca un valor por defecto, nunca un placeholder
> plausible.** Y la UI debe renderizarlo como *sin dato* — no como un medidor en cero, que se lee
> igual que una medición real. Es la misma disciplina de `UNKNOWN / UNCONFIRMED / DERIVED / IMPUTED`
> del playbook, aplicada al nivel del tipo.

Tres propiedades de este diseño que vale la pena entender antes de implementarlo:

1. **El payload viaja en base64 y se firma sobre esos bytes exactos.** Nadie re-serializa nunca:
   ni el relay, ni el gateway, ni el backend en Python. Esto elimina de raíz el bug clásico de
   firmas cross-lenguaje — Dart y Python formatean `4.6533` distinto, y esa diferencia de un
   carácter rompe toda verificación. Verificando los bytes recibidos, el problema no existe.
2. **`relay` está fuera de la firma.** Cada salto añade su capa sin invalidar la de A.
3. **Sin migración pendiente.** Con el esquema completo desde el inicio, pasar de `"ppg": null` a
   un objeto no cambia el contrato ni la versión. Y aunque más adelante hiciera falta un campo
   nuevo, la verificación por bytes hace que los nodos viejos sigan validando firmas correctamente.
4. **El bundle es auto-verificable.** Lleva su propia clave pública, y `signer_key_id` debe ser el
   hash de esa clave. Ningún relay, gateway ni el backend necesitan un registro de claves previo.
   Un atacante que reutilice el `signer_key_id` de una víctima con su propia clave es rechazado
   antes de siquiera revisar la firma.

**Backend:** ver [`docs/API.md`](./API.md). Ingesta `POST /bundles/batch` (idempotente), consulta
`GET /incidents/{id}/{nodes,bundles,rejections}`, y exportación para organismos de socorro en
`GET /incidents/{id}/triage[.csv|.geojson]`.

**Invariante no negociable que sí entra en el núcleo:** no existe `DEAD` en el enum de `status`.
Que no sea representable en el tipo es más barato que revisarlo en code review.

---

## 7. Cronograma y gates

| Ventana | D1 | D2 | D3 | D4 | D5 | Gate |
|---|---|---|---|---|---|---|
| **H+0:00–0:45** | Scaffold, push, roles | Permisos + POC Nearby | Congela bundle + fixtures | Wireframes contra fixtures | FastAPI mock + dashboard | Todos compilan; esquema congelado |
| **H+0:45–2:00** | `BundleStore` + persistencia | **2 teléfonos se ven y envían bytes** | Firma/verificación + ingest | Pantalla de emergencia | Mapa + lista de nodos | **A↔B intercambia bundle en modo avión** |
| **H+2:00–3:15** | Loop DTN: dedupe, forward | Rol gateway + reconexión | Upload idempotente + GETs | Consola de debug | Timeline + polling | **A→B→C con app reiniciada** |
| **H+3:15–4:15** | Integración + APK | Estabilidad de reconexión | Verificación de firma en backend | Pulido de estados vacíos | Deploy + reset | **Vertical slice hasta dashboard** |
| **H+4:15–5:00** | Congelar | Ensayos | Ensayos | Ensayos | Grabar respaldo | **3 corridas limpias** |

**El gate de H+2 es el único que importa.** Si a las 2 horas dos teléfonos no intercambian un
bundle, todo lo demás es decoración. Ver la escalera de §8.

---

## 8. Escaleras de fallback

Cada una con hora de disparo. La regla del playbook aplica igual: 15 min bloqueado → pregunta,
20 → pairing, 45 → se corta.

| Si a la hora… | …esto no funciona | Entonces |
|---|---|---|
| H+1:30 | Nearby no descubre peers | Revisar permisos runtime **uno por uno** — falla en silencio, sin excepción ni log. Es la causa #1 |
| **H+2:00** | **A↔B no intercambia nada** | **Plan B: hotspot local + servidor HTTP en cada teléfono (`shelf`).** Sigue siendo sin Internet, se presenta explícitamente como modo degradado. Nunca como si fuera la malla |
| H+2:30 | Ed25519 consume tiempo | Degradar a **sólo SHA-256** y declarar "integridad, no autenticidad" en el pitch. Honesto y defendible |
| H+3:00 | El backend no está listo | El gateway escribe a un JSON local y el dashboard lo lee. El claim A→B→C se mantiene intacto |
| H+3:30 | El dashboard no despliega | Correrlo en `localhost` y proyectarlo. Un deploy caído no cambia la tesis |
| H+4:00 | Cualquier cosa sigue roja | Se apaga con su feature flag y **no se menciona en el demo**. Nada a medias en pantalla |

**Regla que evita el peor final:** grabar el video de respaldo en la primera corrida que salga bien,
no en la última. La mejor corrida casi nunca es la última.

---

## 9. Después del núcleo — backlog en orden

Ninguno de estos arranca antes de las tres corridas limpias.

1. **Evidencia de movimiento** — es el mejor retorno: `sensors_plus`, umbral determinista, sin ML.
   Añade "prueba de vida" con muy poco código: el campo `evidence.motion` ya existe en `null`,
   sólo hay que escribirlo.
2. **PPG por cámara con gating por SQI** — alto impacto en el pitch, alto riesgo entre modelos.
   `getBioSummary()` devuelve `null` si el SQI no pasa — que es exactamente el estado en que el
   campo ya nace. Nunca un BPM inventado.
3. **Pack de voz offline** — barato, y demuestra muy bien el modo avión.
4. **Localización por zona de confianza** — sólo zona, nunca metros. Jamás RSSI→profundidad.
5. **WebSocket** reemplazando polling en el dashboard.
6. **Fallback BLE GATT** — sólo si sobran ≥4 h.
7. **Claude** detrás de flag, marcado `IMPUTED`, nunca en el camino del SOS.
8. UWB, acústico, Bloom filter, copy budget adaptativo.

---

## 10. Reglas de trabajo para 5 horas

- **Un dueño por carpeta.** Si necesitas tocar la carpeta de otro, se lo pides; no lo editas.
- **`main` siempre compila.** Push cada 20-30 min. Un `main` roto a la hora 4 bloquea a cinco personas.
- **Commitea `pubspec.lock`** y fijen todos la misma versión de Flutter (`flutter --version` al canal
  del equipo en el minuto 0).
- **Cero `build_runner`** en el núcleo. Modelos escritos a mano.
- **Todo log lleva `bundle_id`.** Todo bug debe ser rastreable por `bundle_id`, o no es depurable
  en vivo con tres teléfonos sobre la mesa.
- **Las features nuevas nacen apagadas.** Se encienden sólo tras probarse en hardware físico.

> **La única pregunta:** ¿esto hace más confiable la historia A→B→C→dashboard antes del próximo gate?
> Si no, va al backlog. Cortar es una feature.
