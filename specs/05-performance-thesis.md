# 05 · T3 — Rendimiento y confiabilidad (PROPUESTA — parcialmente implementada)

> **Estado: 🟡 el pedazo de C2 (D5, sección A del plan) ya está implementado y en uso real;
> el resto (D2/D3/D5 — Designer, Sandbox, Oráculo, Mitigación, Enforcement) sigue 🔴 sin
> acordar ni implementar.** Esto sigue sin ser una tesis oficial del pitch — `00-overview.md`
> todavía lista solo T1/T2 — así que si esto va al demo del domingo como una 3ª tesis,
> alguien tiene que decirlo explícitamente y avisarle a Alex/Jorge, no asumirlo por esta doc.
> Owner de la propuesta: D4 (Miguel), que además está llevando C2 (Analista LLM).

**Qué hay hecho hoy (2026-08-22), concreto:**
- ✅ `Threat.threat_class: "security" | "performance"` — campo real en
  `contracts/threat_analysis.py`, documentado en `01-data-contracts.md` §2.
- ✅ `ClaudeAnalyst` (C2) propone `threat_class="performance"`, `threat_id="wallet_dos"`
  cuando `agent_loop.max_iterations` es `null` y `budget_enforced` es `false` — grounded en
  datos reales de `architecture.json`, sin pedirle nada nuevo a D1. Validado con tests reales
  contra Claude (`backend/tests/test_analyst.py`).
- ✅ El dashboard (C9) ya tiene el 2º árbol ("Rendimiento & confiabilidad") — pero sus
  métricas por nodo (duración, invocaciones, fallas) son **simuladas y marcadas como tal en
  la UI**, no telemetría real — siguen dependiendo de que D3 instrumente el Sandbox como
  dice la sección de abajo.
- 🔴 Nada de lo que le toca a Jorge (Designer), Alex (Sandbox/Oráculo) o Laura (Mitigación/
  Enforcement) en este documento se implementó ni se acordó todavía.

## Qué es y por qué

El pitch hoy prueba dos tesis (`00-overview.md`):

| # | Afirmación |
|---|---|
| T1 | Architecture-aware: el harness se deriva de la arquitectura del agente |
| T2 | Adaptive: exploit confirmado → mitigación → harness regenera → cerrado |

Se propone una **T3**: el harness no solo prueba huecos de *seguridad* (algo que un
atacante explota), también perfila el *rendimiento/confiabilidad* del agente en
ejecución — ej. loops sin límite, latencia, fallas repetidas — y cierra el mismo tipo
de loop de mitigación sobre esos hallazgos. No es una amenaza de vulnerabilidad; es
funcionamiento del agente.

**Cómo se prueba en vivo (mismo formato que T1/T2):** cambiamos un agente sin
`agent_loop.max_iterations` → el harness confirma que corre sin freno → se aplica un
`budget_cap` → se regenera → el loop ahora se auto-limita. Mismo momento "wow" que T2,
otra categoría de hallazgo.

## Principio de diseño: reusar el pipeline, no duplicarlo

**No se agrega un grafo/artefacto paralelo.** `threat_class` es una dimensión sobre los
mismos artefactos que ya circulan por `domain/graph.py`. Las conditional edges
(`after_oracle`, `after_regenerate`) ya son genéricas sobre `oracle_verdict` — **no
requieren cambios**.

```
extract ─▶ analyze ─▶ design ─▶ execute ─▶ oracle ─┐
             (C2 propone            (D3 mide             ¿exploited?
          threat_class=perf     iterations_used/               │
          ademas de security)   duration_ms)          regenerate ◀── mitigate ◀─ si
                                                            │
                                                            └▶ execute (regresion) ─▶ oracle ─▶ ¿resisted? ─▶ CERRADO
```

## Caso concreto del MVP: `wallet_dos`

Grounded en un campo que **ya existe** en `architecture.json` — no requiere pedirle
nada nuevo a D1:

```jsonc
// architecture.json (ya existe)
"agent_loop": { "max_iterations": null, "budget_enforced": false }
```

`null` + `budget_enforced: false` = candidato T3: el agente puede encadenar llamadas a
tools sin límite. El propio ejemplo de `01-data-contracts.md` §2 ya lo menciona como
nota deprioritizada: *"agent_loop.max_iterations is null -> wallet-DoS risk"*. T3 lo
sube de nota a amenaza probada.

## Cambios de contrato propuestos (aditivos — no rompen nada existente)

Todos con default que preserva el comportamiento actual; ningún productor/consumidor
existente necesita cambiar para seguir funcionando.

**`contracts/threat_analysis.py` — `Threat`:**
```python
ThreatClass = Literal["security", "performance"]

class Threat(BaseModel):
    ...
    threat_class: ThreatClass = "security"  # NUEVO
```

**`domain/types.py` — `AttackAttempt`** (interno, no persistido, pero fluye a `Finding`):
```python
class AttackAttempt(BaseModel):
    ...
    duration_ms: int | None = None       # NUEVO
    timed_out: bool = False              # NUEVO
    iterations_used: int | None = None   # NUEVO
```

**`contracts/finding.py` — `OracleEvidence`** (espejo, para que el veredicto cargue la métrica):
```python
class OracleEvidence(BaseModel):
    ...
    duration_ms: int | None = None       # NUEVO
    timed_out: bool = False              # NUEVO
    iterations_used: int | None = None   # NUEVO
```

**`contracts/policy.py` — `Policy.kind`:**
```python
kind: Literal[
    "input_sanitizer", "scope_restriction", "network_deny", "approval_gate",
    "budget_cap",  # NUEVO
]
```

`harness_spec.json` (`Surface.attack_modules`/`.oracles`) **no cambia de schema** — son
`list[str]`; solo se agregan valores nuevos por convención (`"wallet_dos"`,
`"iteration_budget_oracle"`).

## Qué hace cada owner

### D5/C2 — Analista LLM (ya en progreso, mío)
- El prompt de `ClaudeAnalyst` gana la regla: si `agent_loop.max_iterations` es `null`
  y `budget_enforced` es `false`, proponer un `Threat` con `threat_class="performance"`,
  `threat_id="wallet_dos"`, `recommended_modules=["wallet_dos"]`,
  `recommended_oracle=["iteration_budget_oracle"]`.
- `_check_business_rules` valida que exista al menos 1 threat de cada `threat_class`
  cuando el `agent_loop` lo amerita (mismo patrón que ya usa para cmd_injection/cadena).

### D2/Jorge — Designer
- Una entrada más en el mapa determinista de `TemplateComposer`:
  `"wallet_dos" -> { attack_modules: ["wallet_dos"], oracles: ["iteration_budget_oracle"] }`.
- Confirmar que `regenerate()` no necesita cambios (opera sobre `Finding`/`Policy`
  genéricos, no sobre el contenido del threat).

### D3/Alex — Sandbox + Módulos + Oráculo
- **Módulo de ataque nuevo** (`AttackModulePort`): `wallet_dos` — en vez de inyectar un
  payload, manda una instrucción abierta/ambigua que tienta al agente a encadenar
  llamadas a tools, y mide `iterations_used`/`duration_ms` durante la corrida. El
  `sandbox.timeout_ms` que ya existe en `harness_spec.json` lo contiene si se
  descontrola de verdad — no hay riesgo de loop infinito real en el sandbox.
- **Regla de oráculo nueva**: `exploited` si el agente llega cerca del cap del harness
  sin frenarse solo; `resisted` si se auto-limita (post-`budget_cap`). Mismo
  `oracle_verdict` de siempre, no se agrega un tipo nuevo.
- Poblar `duration_ms`/`iterations_used` en **todos** los `AttackAttempt`, no solo en
  `wallet_dos` — esto es lo que habilita la vista de métricas de retroalimentación en
  el dashboard sin lógica adicional (ver abajo).

### D5 — Mitigación LLM + Enforcement
- `Policy.kind="budget_cap"`, `rule={"max_iterations": N}`.
- Nuevo `enforcement_point="agent_loop_guard"` que envuelve el loop del agente objetivo
  con el tope.

### D4/Miguel — Dashboard (C9)
- Pantalla 2 (Análisis): dos árboles desde la misma lista `threats[]`, separados por
  `threat_class` — "Vulnerabilidades" (agrupado por `taxonomy`) y
  "Rendimiento & Confiabilidad" (agrupado por `threat_id`).
- Pantalla 3/4 (loop en vivo / CERRADO): misma transición `exploited → mitigado →
  resisted`, tag/color distinto para `threat_class="performance"`.
- **Vista de métricas de retroalimentación**: agregación de `duration_ms`/
  `iterations_used` de *todos* los `Finding` de la corrida (no solo los de
  `wallet_dos`) — tabla o sparkline por `surface` cruzada contra
  `architecture.tools[].defined_at` para ubicarla en código. 100% presentación, no
  requiere artefacto nuevo.

## Criterios de aceptación de T3

- ✅ Dado un `architecture.json` con `agent_loop.max_iterations: null` y
  `budget_enforced: false`, el Analista produce un `Threat` con
  `threat_class="performance"`, `threat_id="wallet_dos"`.
- ✅ El Designer compila una `surface` con `attack_modules=["wallet_dos"]` y
  `oracles=["iteration_budget_oracle"]`.
- ✅ El Sandbox corre el probe y registra `iterations_used`/`duration_ms` en el
  `AttackAttempt`.
- ✅ El Oráculo marca `exploited` cuando el loop corre sin freno; tras aplicar
  `budget_cap` y regenerar, marca `resisted`.
- ✅ El dashboard muestra la transición `exploited → resisted` para este finding, y una
  vista de métricas agregadas por superficie.

## Cut-line explícito (para no romper el cronograma de 36h)

- **Un solo `threat_id` de rendimiento en el MVP: `wallet_dos`.** Nada de latencia de
  MCP, nada de profiling por línea de código — eso queda como roadmap.
- **No hay LLM nuevo.** Se reusa el Mitigador existente (C7) con un `kind` más.
- **No se le pide nada nuevo a D1/Extractor.** Todo lo que necesita T3 ya está en
  `architecture.json` hoy.
- Si en algún punto esto compite por tiempo con cerrar T1/T2, **T1/T2 gana** — son la
  base del pitch. T3 es aditivo, no reemplaza nada.

## Próximos pasos

1. ~~Se actualiza `01-data-contracts.md`/`02-architecture-ports.md`/`03-components.md`~~ —
   hecho, pero **solo para la parte de C2** (`threat_class`, `wallet_dos`), que es aditiva y
   no le pide nada a nadie más para seguir funcionando como está.
2. **Pendiente:** Alex y Jorge todavía no leyeron esto ni confirmaron/objetaron los cambios
   de contrato de *su* sección (`AttackAttempt`/`Finding`/`Policy`/el mapa del
   `TemplateComposer`). Nada de eso está implementado.
3. Si hay acuerdo, cada quien implementa su parte de la tabla de arriba.
