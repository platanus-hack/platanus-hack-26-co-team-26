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

## C2 · Analista LLM  — owner nominal D5 (Laura), implementado por D4 (Miguel)

> **🟢 Implementado.** `backend/adapters/analyst/claude_analyst.py`. En la práctica lo
> construyó Miguel (D4) además de C9 — ver `04-team-plan.md`. Corre contra Claude real, con
> tests en `backend/tests/test_analyst.py` (se saltan sin `ANTHROPIC_API_KEY`).

- **Responsabilidad:** razonar sobre el plano y proponer amenazas priorizadas (Reviewer).
- **Entrada → salida:** `AgentArchitecture` → `threat_analysis.json` ([schema 01·2](./01-data-contracts.md)).
- **Cómo:** `langchain-anthropic` (`claude-sonnet-5`) + `.with_structured_output(ThreatAnalysis)`.
  System prompt: solo JSON, razonar cadenas multi-paso, referenciar evidencia real, priorizar,
  **y toda la prosa (`reasoning`/`attack_hypothesis`/`notes`) en español** — el dashboard es
  español-only. Los identificadores (`threat_id`, códigos de `taxonomy`, nombres de
  módulos/oráculos) nunca se traducen.
- **Regla:** el LLM **propone**, no juzga verdad. La confirmación es del oráculo.
- **T3 (propuesta, ver `05-performance-thesis.md`):** además de amenazas de seguridad, ya
  propone `threat_class="performance"`, `threat_id="wallet_dos"` cuando
  `agent_loop.max_iterations` es `null` y `budget_enforced` es `false` — grounded 100% en
  campos que ya trae `architecture.json`, sin pedirle nada nuevo a D1. Esta parte del C2 está
  hecha; lo que falta de T3 (Designer/Sandbox/Oráculo/Mitigación) sigue sin acordarse con
  D2/D3/D5.

**Criterios de aceptación:**
- ✅ Devuelve ≥2 amenazas: 1 `cmd_injection` single-surface + 1 cadena multi-paso (exfil).
- ✅ `evidence_refs` apuntan a IDs reales del `architecture.json`.
- ✅ `recommended_modules`/`recommended_oracle` usan nombres que D2/D3 implementan.
- ✅ `priority` es orden total (sin empates). Reintenta 1 vez con el `ValidationError` si falla.
- ✅ Si `agent_loop` no tiene límite, agrega la amenaza `wallet_dos` (T3).

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

> **🟡 2 de 4 pantallas implementadas** (Análisis, Loop en vivo) — `frontend/`, corriendo
> contra el backend real (no mockeado: usa el `ClaudeAnalyst` real de C2 y el SSE real del
> `StateGraph`). Faltan Arquitectura y una pantalla dedicada de Mitigación (hoy esa
> transición se ve dentro de Loop en vivo, no en pantalla propia).

- **Responsabilidad:** transmitir el loop en vivo y contar la historia en el demo (4 pantallas).
- **Cómo:** Vite + React + TS + Tailwind v4 + shadcn/ui. Cambios sobre el stack decidido en
  `02-architecture-ports.md` — ver esa tabla actualizada. Se suscribe a
  `GET /runs/{run_id}/events` (SSE) y a los endpoints REST nuevos
  `GET /runs/{run_id}/{architecture,threat_analysis,findings}` (el SSE manda conteos/refs
  livianos, no el artefacto completo — estos endpoints sirven el JSON entero para que el
  dashboard renderice detalle real).
- **Las 4 pantallas (spec original) — estado real:**
  1. **Arquitectura** — 🔴 no implementada todavía.
  2. **Análisis** — 🟢 implementada. Dos "threat forests" (árboles de dependencias reales,
     no listas planas) en tabs: **Vulnerabilidades** (agrupa `Threat[]` por superficie
     compartida — un threat single-surface y uno multi-paso que usan la misma tool cuelgan
     del mismo nodo padre) y **Rendimiento & confiabilidad** (T3 — cadena real desde
     `architecture.data_flows[].path` + el threat `wallet_dos` real; las métricas por nodo
     — duración, invocaciones, tasa de fallas — son **simuladas y marcadas como tal en la
     UI**, placeholder hasta que D3 instrumente el Sandbox, ver `05-performance-thesis.md`).
     Layout vertical, panel de detalle al costado con gauges (Bklit UI). Al abrir cada árbol,
     un efecto de entrada en Three.js (`InstancedMesh` + adapter de anime.js) — puramente
     decorativo, la interacción real siempre pasa por el DOM/SVG 2D, nunca por el canvas.
  3. **Loop en vivo** — 🟢 implementada. Diagrama del pipeline (cajas sin relleno, solo
     borde) que avanza con el SSE real: un segmento a la vez se revela (cola secuencial,
     nunca simultáneo aunque lleguen varios eventos del backend en el mismo instante), las
     cajas se iluminan solo cuando la luz realmente llega. Log de eventos abajo.
  4. **Mitigación → CERRADO** — 🟡 no es pantalla propia; la transición `exploited →
     mitigado → resisted` se ve dentro de Loop en vivo (badge "CERRADO" + caja final).
- **Persistencia:** cada pantalla guarda su última corrida en `sessionStorage` (no
  `localStorage` — no sobrevive a cerrar el navegador) para que cambiar de pestaña y volver,
  o un F5, no pierda el resultado. Nunca hay una corrida "a medias" restaurada (la conexión
  SSE no sobrevive a salir de la pantalla).
- **Idioma:** toda la UI en español, incluida la salida del LLM (ver nota de C2).

**Criterios de aceptación:**
- ✅ Renderiza el estado del run en vivo desde SSE sin recargar.
- ✅ Muestra claramente la transición `exploited → resisted` (el momento "wow" de T2).
- 🔴 Muestra el diff de recompilación cuando cambia la arquitectura (T1) — no aplica todavía
  porque D1 sigue con `FakeExtractor`; no hay una arquitectura real que cambie para mostrar
  el diff.
- 🟡 "Funciona con datos mockeados" ya no describe cómo se construyó — se armó directo
  contra el backend real (C2 real, SSE real) en vez de mocks del lado del frontend.

---

## Telemetría (transversal)

Todo nodo del grafo emite `HarnessEvent` ([contrato en 02](./02-architecture-ports.md)) vía
`TelemetryPort` → SSE. Es el pegamento entre backend y dashboard, y permite a D4 trabajar
contra el contrato de eventos antes de que el backend esté completo.
