# ADR-0005: Dashboard en React + deck.gl, no Compose Web

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** Miguel

## Contexto

Al ser Android-only (ADR-0002), desaparece el argumento de "un solo lenguaje" para
justificar Compose Web. El mapa de operaciones necesita renderizar miles de nodos,
heatmaps de verosimilitud y grafos de encuentros con buen desempeño.

## Decisión

`web/` es TypeScript + React + Vite. Visualización geoespacial con **deck.gl sobre
MapLibre GL** — sensiblemente más maduro para esto que cualquier alternativa en
Kotlin/Wasm hoy.

## Consecuencias

Un tercer lenguaje en el monorepo (Kotlin, Python, TypeScript), mitigado por
protobuf como contrato único (ADR-0004): el dashboard nunca inventa su propio
parser de bundles.
