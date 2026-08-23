# ADR-0002: Android-only ahora, Kotlin nativo, iOS en standby

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** equipo completo

## Contexto

La malla es un sistema cuyo valor crece con la **densidad de nodos por metro
cuadrado de escombro**, no con el número total de descargas. iOS aportaría poca
densidad a cambio de duplicar la complejidad del proyecto: entitlement de Wi-Fi
Aware, entitlement de Critical Alerts, ejecución en background severamente
restringida, CoreBluetooth con *state restoration*, y una segunda UI.

Android habilita capacidades que iOS no concede en 2026: foreground service con
notificación persistente (el motor DTN corre de verdad, no cuando el sistema lo
permite), Wi-Fi Aware y Wi-Fi Direct sin proceso de aprobación externo, BLE
advertising continuo con control real del ciclo de trabajo, y acceso directo a
frames de cámara para PPG sin pelear con el pipeline de imagen de iOS.

## Decisión

App nativa **Kotlin + Jetpack Compose**, mínimo API 26, objetivo API 35. Lógica de
dominio y DTN en Kotlin Multiplatform (`commonMain`) con un único target activo
(`androidMain`). iOS queda en standby — plan de entrada documentado en
`docs/roadmap/VERTICAL-SLICES.md` § 19bis.

## Alternativas consideradas

Flutter (v1.0 del proyecto): descartado por el riesgo de vivir el motor DTN en
Dart y por las mismas restricciones de background en iOS, sin ganar nada a cambio.

## Consecuencias

- Se revisa cuando: (a) el Slice 4 (demo extremo a extremo) esté demostrado, o
  (b) exista una alianza institucional que exija soporte iOS.
- Comunicación pública honesta mientras tanto: "Disponible para Android. iOS en
  desarrollo." — nunca "multiplataforma" (ver `docs/glossary.md`).
