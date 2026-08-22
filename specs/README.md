# Harness Compiler — Especificaciones (SDD)

> **Architecture-aware, adaptive security harnesses for autonomous AI agents.**
> Una plataforma que analiza la arquitectura de cada agente, **compila** un harness de
> evaluación y aislamiento a su medida, lo somete a explotación controlada, y **regenera**
> el harness tras cada mitigación para probar que la vulnerabilidad quedó cerrada.

Track: 🛡️ AI Security · Platanus Hack 26 · Equipo de 5 · Ventana 36h · Deadline **domingo 13:00**

---

## Cómo leer estas specs (Spec-Driven Development)

Escribimos **el contrato antes que el código**. Nadie implementa una pieza sin que su
spec esté acordada. El orden de lectura:

1. [`00-overview.md`](./00-overview.md) — visión, las dos tesis, regla de corte, pipeline.
2. [`01-data-contracts.md`](./01-data-contracts.md) — **el activo central.** Los schemas JSON que
   conectan a todos. Si esto está firmado en la hora 1, todos trabajan en paralelo.
3. [`02-architecture-ports.md`](./02-architecture-ports.md) — arquitectura hexagonal, puertos
   (interfaces TS), mapa de módulos y stack.
4. [`03-components.md`](./03-components.md) — spec por componente del pipeline, con
   responsabilidades, entradas/salidas y **criterios de aceptación**.
5. [`04-team-plan.md`](./04-team-plan.md) — reparto de los 5, cronograma, cadena crítica y checklist.
6. [`diagrams/real-case-flow.md`](./diagrams/real-case-flow.md) — el producto en un caso real
   ("Acme Support Agent"), en 3 vistas Mermaid. Base del demo.

## Stack (decidido)

Python 3.12 · **LangGraph** (orquestación, loop T2) · **FastAPI** + `sse-starlette` ·
**Pydantic v2** (contratos) · **`langchain-anthropic`** (Claude) · `ast` + Semgrep (extractor) ·
**Docker** (sandbox, fallback subprocess) · **SQLite** + JSON en `runs/<id>/` ·
agente objetivo en **LangChain** · frontend **Vite + React + Tailwind + shadcn/ui + Recharts**.

## Regla de corte (gobierna todo el alcance)

> Si una tarea **no prueba T1 o T2**, es *roadmap*, no código.

- **T1 — Architecture-aware:** cambiás la arquitectura del agente → el harness **recompila distinto**.
- **T2 — Adaptive:** exploit confirmado → mitigación generada → harness **regenera** → re-corre → **confirmado cerrado**.

## Estado de las specs

| Spec | Owner de acuerdo | Estado |
|---|---|---|
| Stack tecnológico | Todos | 🟢 decidido (Python + LangGraph + FastAPI + Vite) |
| Data contracts (schemas) | D1 ↔ D2 ↔ D5 | 🔴 por firmar en hora 1 |
| Ports & arquitectura | Dominio (Jorge/D2) | 🟡 borrador |
| Componentes | Cada dev su sección | 🟡 borrador |
| Team plan | Todos | 🟡 borrador |

> Firmar = los 3 devs de la cadena de datos (D1, D2, D5) leyeron y aceptaron los nombres de
> campos exactos de `01-data-contracts.md`. Ese acuerdo desbloquea el trabajo en paralelo.
