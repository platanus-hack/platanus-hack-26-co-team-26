# ADR-0001: Arquitectura hexagonal en `:core` y en el backend

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** equipo completo

## Contexto

Cinco personas necesitan avanzar en paralelo sobre transporte, DTN, señal/AIB, app
y backend sin bloquearse mutuamente por hardware o por disponibilidad de servicios
externos.

## Decisión

Dominio y casos de uso (`APPLICATION`) viven aislados de frameworks; toda
interacción con hardware, red o persistencia pasa por un puerto (interfaz)
declarado en `core/application/ports` (Kotlin) o `services/shared/src/api/application/ports.py`
(Python). Cada puerto tiene al menos dos implementaciones: la real y una *fake*
determinista para tests.

## Consecuencias

- El motor DTN completo se testea en JVM sin ningún teléfono (`LoopbackFake`).
- `:core:domain` no puede importar `android.*`, verificado en CI por `arch-guard`.
- Costo: más archivos (interfaz + implementación real + fake) por cada
  integración. Se acepta porque desbloquea el trabajo en paralelo de 5 personas.
