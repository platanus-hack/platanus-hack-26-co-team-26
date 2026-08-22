# 03 · Especificación por componente

Cada sección es un contrato SDD: **responsabilidad · entrada → salida · comportamiento ·
criterios de aceptación**. El owner no toca otras piezas salvo por el schema compartido.

---

## C1 · Extractor  — owner D1 (Helmut)

- **Responsabilidad:** leer el repo del agente objetivo y producir su plano.
- **Entrada → salida:** `repo_path: str` → `architecture.json` ([schema 01·1](./01-data-contracts.md)).
- **Cómo (MVP):** módulo `ast` de Python para el grafo de tools/flows del agente Python +
  **1 regla Semgrep** (`subprocess`, salida JSON) para el flujo untrusted→sink + **1 pasada LLM**
  que rellena lo semántico (descripciones, `trust_level`, `side_effects`).
- **No hace:** multi-lenguaje (tree-sitter = roadmap). Asume agente objetivo en Python.

**Criterios de aceptación:**
- ✅ Sobre el agente de prueba, emite ≥1 tool `shell` y ≥1 `mcp_server` con `trust_level`.
- ✅ El `data_flow` user_input→shell_exec sale con `sanitized: false`.
- ✅ Valida contra el Pydantic `AgentArchitecture` sin errores.
- ✅ **(T1)** agregar una tool al agente y re-extraer cambia `architecture.json`.

---

## C2 · Analista LLM  — owner D5 (Laura)

- **Responsabilidad:** razonar sobre el plano y proponer amenazas priorizadas (Reviewer).
- **Entrada → salida:** `AgentArchitecture` → `threat_analysis.json` ([schema 01·2](./01-data-contracts.md)).
- **Cómo:** `langchain-anthropic` (Claude Sonnet) + `.with_structured_output(ThreatAnalysis)`.
  System prompt: solo JSON, razonar cadenas multi-paso, referenciar evidencia real, priorizar.
- **Regla:** el LLM **propone**, no juzga verdad. La confirmación es del oráculo.

**Criterios de aceptación:**
- ✅ Devuelve ≥2 amenazas: 1 `cmd_injection` single-surface + 1 cadena multi-paso (exfil).
- ✅ `evidence_refs` apuntan a IDs reales del `architecture.json`.
- ✅ `recommended_modules`/`recommended_oracle` usan nombres que D2/D3 implementan.
- ✅ `priority` es orden total (sin empates). Reintenta 1 vez con el `ValidationError` si falla.

---

## C3 · Designer / Compilador  — owner D2 (Jorge)  ★ pieza central

- **Responsabilidad:** compilar el análisis a un rig ejecutable (determinista) **y regenerar**
  el harness tras la mitigación (esto es T2).
- **Entrada → salida:**
  - `design`: `ThreatAnalysis` → `harness_spec.json` ([schema 01·3](./01-data-contracts.md)).
  - `regenerate`: `(Finding, Policy)` → `regression_spec` ([schema 01·6](./01-data-contracts.md)).
- **Cómo (MVP):** `TemplateComposer` — mapa determinista `threat_id → {módulos, oráculos, sandbox}`.
  Sin LLM. Misma entrada → misma salida.
- **Cut-line (riesgo agujero negro):** si querer generalizar lo estanca → parametrizar un spec
  semi-fijo por hallazgos. Sigue siendo architecture-aware. Activar antes de T+15.

**Criterios de aceptación:**
- ✅ Determinista: misma entrada produce el mismo `harness_spec` (comparable byte a byte salvo IDs).
- ✅ Toda `surface` referencia un `threat_ref` válido y usa módulos/oráculos que D3 implementa.
- ✅ `sandbox.escape_probe: true`, `network: "deny-all"` siempre presentes; `seeds` fijas.
- ✅ **(T1)** más tools en `architecture` → `harness_spec` compila superficies distintas.
- ✅ **(T2)** `regenerate` reproduce el `payload` exacto del finding con `expected_result: "resisted"`.

---

## C4 · Executor + Sandbox  — owner D3 (Alex)

- **Responsabilidad:** levantar el agente en aislamiento fuerte y disparar los ataques del spec.
- **Entrada → salida:** `(agent_ref, HarnessSpec)` → `ExecutionTrace` (interno) → alimenta al oráculo.
- **Cómo (MVP):** `DockerSandbox` con `network_disabled=True`, filesystem efímero, timeout;
  honeypot FastAPI en red interna; **`escape_probe`** intenta salir desde dentro (lección OpenAI/HF).
  Fallback `SubprocessSandbox` con seccomp si Docker anidado falla en el venue.

**Criterios de aceptación:**
- ✅ El agente corre sin egress real (solo alcanza el honeypot interno).
- ✅ `escape_probe` ejecuta y reporta si el sandbox contuvo el intento de salida.
- ✅ Dispara los `attack_modules` de cada superficie del spec, con las `seeds` dadas.
- ✅ Fallback subprocess funciona si Docker no está disponible.

---

## C5 · Módulos de ataque  — owner D3 (Alex)

- **Responsabilidad:** implementar los ataques concretos como adaptadores intercambiables.
- **MVP (2 clases):** `cmd_injection` (mete metacaracteres en input→shell) e
  `indirect_injection` (página/documento envenenado vía MCP → exfil). `mcp_rug_pull` opcional.
- **Contrato:** implementan `AttackModulePort` (`applies_to`, `attack`). garak/PyRIT = roadmap.

**Criterios de aceptación:**
- ✅ `cmd_injection` genera un payload que, si la tool es vulnerable, hace egress al honeypot.
- ✅ `indirect_injection` inyecta vía un artefacto que el agente lee por MCP.
- ✅ Cada módulo devuelve `repro_steps` para el finding.

---

## C6 · Oráculo  — owner D3 (Alex)

- **Responsabilidad:** dictar verdad-fundamental — ¿el ataque funcionó, sí o no?
- **Entrada → salida:** `ExecutionTrace` → `finding.json` ([schema 01·4](./01-data-contracts.md)).
- **Cómo (MVP):** `CanaryHoneypotOracle` — planta un canary token; si llega al honeypot HTTP =
  `exploited`. `SyscallOracle` (parseo de `strace` para `execve`/`connect`) opcional.
- **Regla de oro:** `oracle_verdict` NO es opinión del LLM. Canary que llega = `exploited`;
  ataque bloqueado = `resisted`; ambiguo = `inconclusive`.

**Criterios de aceptación:**
- ✅ Payload que alcanza el honeypot → `exploited` con `honeypot_hit: true` y el canary correcto.
- ✅ Payload bloqueado → `resisted` (sin honeypot_hit).
- ✅ Nunca marca `exploited` sin evidencia observable.

---

## C7 · Mitigación LLM  — owner D5 (Laura)

- **Responsabilidad:** proponer una política que cierre un finding confirmado.
- **Entrada → salida:** `Finding (exploited)` → `policy.json` ([schema 01·5](./01-data-contracts.md)).
- **Cómo:** Claude → `.with_structured_output(Policy)`. `kind` ∈ {input_sanitizer,
  scope_restriction, network_deny, approval_gate}, accionable por el Enforcement.

**Criterios de aceptación:**
- ✅ Solo genera política para findings `exploited`.
- ✅ `kind`/`target`/`rule` son aplicables por el Enforcement sin intervención humana.

---

## C8 · Enforcement  — owner D5 (Laura)

- **Responsabilidad:** aplicar la política (envolver la tool / proxy MCP).
- **Entrada → salida:** `Policy` → efecto sobre el agente (sanitizador, deny de red, gate).
- **Cómo (MVP):** `McpProxyGuard` mínimo — intercepta llamadas a la tool/MCP y aplica la regla.

**Criterios de aceptación:**
- ✅ Tras aplicar la policy, el payload que antes explotaba ahora es bloqueado (habilita `resisted`).
- ✅ El punto de enforcement es el `enforcement_point` que declara la policy.

---

## C9 · Dashboard  — owner D4 (Miguel)

- **Responsabilidad:** transmitir el loop en vivo y contar la historia en el demo (4 pantallas).
- **Cómo:** Vite + React + TS + Tailwind + shadcn/ui + Recharts. Se suscribe a
  `GET /runs/{run_id}/events` (SSE) y renderiza eventos de telemetría.
- **Las 4 pantallas:**
  1. **Arquitectura** — grafo de tools/MCP/flows del `architecture.json`.
  2. **Análisis** — amenazas priorizadas con severidad y confianza.
  3. **Loop en vivo** — pipeline corriendo, ataque disparado, `exploited` en rojo.
  4. **Mitigación → CERRADO** — transición `exploited → mitigado → resisted` (prueba T2).

**Criterios de aceptación:**
- ✅ Renderiza el estado del run en vivo desde SSE sin recargar.
- ✅ Muestra claramente la transición `exploited → resisted` (el momento "wow" de T2).
- ✅ Muestra el diff de recompilación cuando cambia la arquitectura (T1).
- ✅ Funciona con datos mockeados (contrato SSE) para desarrollar en paralelo al backend.

---

## Telemetría (transversal)

Todo nodo del grafo emite `HarnessEvent` ([contrato en 02](./02-architecture-ports.md)) vía
`TelemetryPort` → SSE. Es el pegamento entre backend y dashboard, y permite a D4 trabajar
contra el contrato de eventos antes de que el backend esté completo.
