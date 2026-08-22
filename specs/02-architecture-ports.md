# 02 · Arquitectura y puertos

## Principio: arquitectura hexagonal (la puerta abierta)

El **dominio** orquesta el loop y no sabe nada de Docker, LangGraph, Claude ni Semgrep. Todo
lo externo vive tras un **puerto** (interfaz). Cada pieza que cortamos para el hackathon = un
adaptador con implementación mínima hoy y espacio para un adaptador mejor mañana (roadmap).

> Vale doble: es buena ingeniería (dominio testeable sin infra) **y** es la narrativa de
> roadmap del pitch — *"añadir X = un adaptador nuevo, no una refactorización"*.

## Stack tecnológico (decidido)

| Componente | Tecnología | Por qué |
|---|---|---|
| Lenguaje backend | **Python 3.12** | Lo que el equipo domina |
| Contratos/validación | **Pydantic v2** (`contracts/`) | Validación + JSON Schema; fuente de verdad de los schemas |
| Orquestación / dominio | **LangGraph** | State-graph; el loop T2 es un edge cíclico; streaming gratis |
| Llamadas LLM (3) | **`langchain-anthropic`** + `.with_structured_output()` | Salida Pydantic validada; Claude Sonnet/Haiku |
| API + streaming | **FastAPI** + `sse-starlette` | Async; SSE trivial; sirve `astream_events` de LangGraph |
| Extractor | **`ast` nativo + Semgrep (subprocess) + 1 LLM** | El agente objetivo es Python → sin tree-sitter en MVP |
| Sandbox / Executor | **Docker SDK** (`network_disabled`) + fallback `subprocess` | Aislamiento estándar; fallback si Docker anidado falla |
| Honeypot + Oráculo | **FastAPI mini-app + canary token** (syscall vía `strace` opcional) | Un token que llega al honeypot es verdad-fundamental |
| Enforcement | **SDK `mcp` de Python** (proxy guard) | Envuelve/filtra llamadas a tools y MCP |
| Módulos de ataque | **Funciones Python** bajo `AttackModulePort` | garak/PyRIT se envuelven como adaptador después (roadmap) |
| Estado / datos | **SQLite** (`sqlite3`/SQLModel) + artefactos JSON en `runs/<id>/` | Cero infra, arranca en minutos, cero dependencia de red en demo |
| Agente objetivo (prueba) | **Agente LangChain/LangGraph (Python)** | Realista y conocido; agregar una tool = prueba T1 |
| Loop en vivo | **SSE (Server-Sent Events)** | Más simple que WebSockets; muestra el loop corriendo |
| Dashboard | **Vite + React + TS + Tailwind + shadcn/ui + Recharts** | Owner: Miguel; consume SSE |

> **Sin Redis, sin cola, sin Kafka, sin ClickHouse.** Para una rebanada vertical de una
> corrida, un orquestador en proceso (LangGraph) que corre el pipeline y transmite por SSE es
> suficiente. Menos piezas = menos cosas que se rompen a la hora 33.

## Layout del monorepo

```
platanus-hack-26-co-team-26/
├── specs/                      # ESTE directorio (SDD)
├── backend/
│   ├── pyproject.toml          # uv / poetry
│   ├── contracts/              # Pydantic models = los schemas (fuente de verdad)
│   │   ├── architecture.py
│   │   ├── threat_analysis.py
│   │   ├── harness_spec.py
│   │   ├── finding.py
│   │   └── policy.py
│   ├── domain/                 # puertos (Protocols) + el grafo LangGraph
│   │   ├── ports.py            # todas las interfaces
│   │   └── graph.py            # el state-graph (loop T2)
│   ├── adapters/               # una carpeta por puerto
│   │   ├── extractor/          # D1
│   │   ├── analyst/            # D5  (LLM)
│   │   ├── designer/           # D2  (compilador de plantillas)
│   │   ├── sandbox/            # D3  (docker + subprocess fallback)
│   │   ├── oracle/             # D3  (canary/honeypot/syscall)
│   │   ├── attack_modules/     # D3  (cmd_injection, indirect_injection, ...)
│   │   ├── mitigator/          # D5  (LLM)
│   │   ├── enforcement/        # D5  (mcp proxy guard)
│   │   └── telemetry/          # SSE emitter
│   ├── api/                    # FastAPI: endpoints + SSE + honeypot
│   ├── storage/                # SQLite + writer de runs/<id>/
│   └── tests/
├── target-agent/               # D1: el agente LangChain vulnerable de prueba
│   ├── src/agent.py
│   └── src/tools/shell.py
├── frontend/                   # D4 (Miguel): Vite + React + Tailwind + shadcn
└── runs/                       # artefactos JSON por corrida (gitignored salvo 1 seed)
```

## Los puertos (interfaces del dominio)

Se definen como **`typing.Protocol`** en `domain/ports.py`. El dominio depende solo de estos;
los adaptadores los implementan. Firmas indicativas (los tipos vienen de `contracts/`):

```python
from typing import Protocol
from contracts import (
    AgentArchitecture, ThreatAnalysis, HarnessSpec,
    Finding, Policy, RegressionSpec,
)

class ArchitectureExtractorPort(Protocol):
    def extract(self, repo_path: str) -> AgentArchitecture: ...          # D1

class SecurityAnalystPort(Protocol):
    def analyze(self, arch: AgentArchitecture) -> ThreatAnalysis: ...    # D5 (LLM)

class HarnessDesignerPort(Protocol):
    def design(self, analysis: ThreatAnalysis) -> HarnessSpec: ...       # D2
    def regenerate(self, finding: Finding, policy: Policy) -> RegressionSpec: ...  # D2 (T2)

class SandboxPort(Protocol):
    def run(self, agent_ref: str, spec: HarnessSpec) -> "ExecutionTrace": ...      # D3

class AttackModulePort(Protocol):
    id: str
    def applies_to(self, surface: "Surface") -> bool: ...                # D3
    def attack(self, ctx: "AttackContext") -> "AttackAttempt": ...       # D3

class OraclePort(Protocol):
    def evaluate(self, trace: "ExecutionTrace") -> Finding: ...          # D3

class MitigationPort(Protocol):
    def propose(self, finding: Finding) -> Policy: ...                   # D5 (LLM)

class EnforcementPort(Protocol):
    def apply(self, policy: Policy) -> None: ...                         # D5

class TelemetryPort(Protocol):
    def emit(self, event: "HarnessEvent") -> None: ...                   # SSE
```

### Adaptadores: MVP vs. futuro (la tabla del roadmap)

| Puerto | Adaptador MVP (se construye) | Adaptadores futuros (pitch) |
|---|---|---|
| ArchitectureExtractor | `PyAstExtractor` (`ast` + 1 regla Semgrep + 1 LLM) | tree-sitter multi-lenguaje, Go/TS |
| SecurityAnalyst | `ClaudeAnalyst` (Sonnet) | otros modelos, ensemble |
| HarnessDesigner | `TemplateComposer` (mapa determinista) | `LlmDesigner` |
| Sandbox | `DockerSandbox` (fallback `SubprocessSandbox`) | gVisor, firecracker |
| AttackModule | `CmdInjection`, `IndirectInjection`, `McpRugPull` | garak-wrapper, PyRIT, CLI-fuzzer |
| Oracle | `CanaryHoneypotOracle` (+ `SyscallOracle` opcional) | LLM-judge |
| Mitigation | `LlmMitigator` / `RuleMitigator` | policy engine avanzado |
| Enforcement | `McpProxyGuard` mínimo | motor de políticas fuera de proceso |
| Telemetry | `SseTelemetry` → UI | ingest de trazas reales de prod |

## El grafo LangGraph (dominio)

El pipeline es un `StateGraph`. El estado es un `TypedDict`/Pydantic con los artefactos
acumulados. El **loop T2** es un edge condicional: si hay findings `exploited`, va a
`mitigate → regenerate → execute` de nuevo; si no, `end`.

```
extract ─▶ analyze ─▶ design ─▶ execute ─▶ oracle ─┐
                         ▲                          │
                         │                   ¿exploited?
                     regenerate ◀── mitigate ◀──── sí
                         │
                         └────────▶ execute (regresión) ─▶ oracle ─▶ ¿resisted? ─▶ END (CERRADO)
                                                                          │ no
                                                                          └▶ (re-mitigar, máx N)
```

- Cada nodo `emit()` eventos de telemetría → SSE → dashboard.
- `budget` (`max_steps`, `max_tokens`) corta el loop; nunca infinito.
- Nodos deterministas: `extract` (mayormente), `design`, `execute`, `oracle`, `regenerate`,
  `enforce`. Nodos LLM: `analyze`, `mitigate`. Solo 2 nodos tocan el modelo.

## Contrato de eventos de telemetría (SSE)

Todo nodo emite eventos con forma estable para el dashboard:

```jsonc
{ "run_id": "run-a1b2", "step": "oracle", "status": "done",
  "artifact_ref": "finding.1", "verdict": "exploited", "ts_ms": 172... }
```

El frontend (D4) se suscribe a `GET /runs/{run_id}/events` (SSE) y renderiza el loop en vivo.
