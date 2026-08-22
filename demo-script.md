# Guion del demo — Harness Compiler (4 minutos)

> Extraído de `specs/04-team-plan.md` a un documento propio para que el equipo lo revise,
> ensaye y firme (checklist de arranque, `specs/04-team-plan.md`). El contenido del guion
> no cambia respecto al acordado — este archivo lo separa para poder firmarlo y trackear
> el ensayo sin mezclarlo con el resto del plan.

**Las dos tesis que el guion tiene que probar en vivo** (`specs/00-overview.md`):
- **T1** — architecture-aware: cambiar la arquitectura del agente hace que el harness recompile distinto.
- **T2** — adaptive: un exploit confirmado se mitiga y se re-prueba hasta cerrar.

**Caso usado en todo el guion:** el "Acme Support Agent" (`specs/diagrams/real-case-flow.md`) —
`run_shell` sin sanitizar, MCP de Notion (third-party), `send_email`, API key en contexto.
Implementado en `target-agent/`.

---

## Minutado

| Min | Beat | Qué se muestra | Componente(s) que lo sostienen |
|---|---|---|---|
| 0:00 | Setup | "Este agente tiene una tool de shell y un MCP de Notion. Se ve bien." | `target-agent/` (D1) |
| 0:20 | **T1** | Corremos el compilador. El Analista LLM lee la arquitectura y encuentra la cadena de riesgo; el Designer COMPILA un `harness_spec` a la medida. | Extractor (D1) ✅ · Analista (D5) · Designer (D2) |
| 1:00 | Ataque | Executor en sandbox aislado con escape-probe. Ataque dirigido de `cmd_injection`. El canary llega al honeypot → exploit confirmado. *"No es opinión de un LLM: es hecho."* | Sandbox/Executor/Oráculo (D3) |
| 1:45 | **T2** | El sistema genera la mitigación, la aplica, y el Designer REGENERA el test. Re-corremos: exploit ahora BLOQUEADO. Regresión cerrada. El loop cierra. | Mitigación LLM + Enforcement (D5) · Designer regenera (D2) |
| 2:45 | **T1 de nuevo** | Agregamos una tool al agente. Recompilamos: `harness_spec` CAMBIA, aparece una nueva superficie y un nuevo ataque. | Extractor (D1) ✅ re-extrae · Designer (D2) recompila |
| 3:15 | Motivación | El caso OpenAI/Hugging Face: escape de un sandbox mal aislado. La lección: verificar el aislamiento activamente — es lo que hace `escape-probe`. | Slide de motivación (pendiente, checklist de arranque) |
| 3:35 | Roadmap | Arquitectura hexagonal: cada pieza que cortamos es un adaptador. *"La puerta queda abierta por diseño."* | — |
| 3:55 | Cierre | *"Compilamos seguridad desde la arquitectura del agente, y cerramos el loop con pruebas reales."* | — |

## El beat 2:45 (T1 en vivo) — ya tiene un procedimiento probado

La parte de D1 para ese beat está lista y ensayada en código, no solo en el guion:
`target-agent/README.md` documenta el paso a paso exacto para agregar `query_database`
(tool `sql`) en vivo, y `backend/tests/test_extractor.py::test_t1_adding_a_tool_changes_architecture`
prueba en CI que re-extraer después de ese cambio efectivamente hace aparecer la tool nueva
en `architecture.json` — así que si el demo en vivo falla, ya sabríamos por qué (no es la
primera vez que se corre ese flujo).

## Estado real de cada beat (al 2026-08-22, para no prometer de más)

| Beat | Estado |
|---|---|
| 0:00 / 0:20 (Extractor) | ✅ Real — `PyAstExtractor`, PR #2 |
| 0:20 (Analista) | ⏳ Pendiente (D5) |
| 0:20 / 1:45 / 2:45 (Designer) | ⏳ Pendiente (D2) |
| 1:00 (Sandbox/Oráculo) | ⏳ En curso (D3, Alex) |
| 1:45 (Mitigación/Enforcement) | ⏳ Pendiente (D5) |
| 2:45 (T1 con tool nueva) | ✅ Extractor listo · ⏳ Designer pendiente para que "recompile distinto" de verdad |
| 3:15 (slide motivación) | ⏳ Pendiente (checklist de arranque) |

## Riesgos del demo

Ver tabla completa en `specs/04-team-plan.md` (sección "Riesgos y mitigaciones") — no se
duplica acá para no tener dos fuentes de verdad desalineándose.

## Firmas (revisado y de acuerdo con el guion tal como está)

- [ ] D1 — Helmut Chaparro
- [ ] D2 — Jorge Bustamante
- [ ] D3 — Alex Barraza
- [ ] D4 — Miguel Aguilar
- [ ] D5 — Laura Martínez

## Ensayos cronometrados

*(vacío hasta el freeze del domingo — llenar con fecha, duración real, y qué falló)*

| Fecha | Duración | Notas |
|---|---|---|
| — | — | — |
