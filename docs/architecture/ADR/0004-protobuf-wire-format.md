# ADR-0004: Protocol Buffers como fuente única de verdad del wire format

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** Helmut

## Contexto

Tres lenguajes (Kotlin, Python, TypeScript) necesitan acordar el mismo formato de
bytes para el mismo objeto lógico (`Bundle`). Definirlo tres veces a mano garantiza
*drift* — "funciona en mi máquina" se convierte en "el bundle llega corrupto al
backend".

## Decisión

`protocol/proto/sismomesh/v1/*.proto` (proto3) es la única fuente. Kotlin, Python
y TypeScript se generan con `make proto`; nadie edita el código generado a mano.
El descubrimiento (beacon BLE) usa un formato binario compacto a medida —no
protobuf— por presupuesto de 26 bytes; documentado en `protocol/beacon/BEACON_FORMAT.md`.

## Consecuencias

- CI (`protocol-ci.yml`) falla si hay *drift* entre `.proto` y el código commiteado.
- Se requieren al menos 5 vectores dorados (uno por tipo de payload) con test de
  *round-trip* Kotlin↔Python — elimina la clase de bug más cara del proyecto.
- Cambios incompatibles requieren este mismo tipo de ADR.
