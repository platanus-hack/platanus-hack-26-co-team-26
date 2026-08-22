# 04 · Plan de equipo y cronograma

**Equipo de 5 · Ventana 36h · Deadline domingo 13:00 · Freeze domingo 09:00.**

## Reparto (quién se encarga de qué)

| Dev | Persona | GitHub | Rol | Es dueño de | Specs / componentes |
|---|---|---|---|---|---|
| **D1** | Helmut Chaparro | @hchaps404 | Extractor | `architecture.json` + agente vulnerable de prueba | [C1](./03-components.md#c1--extractor--owner-d1-helmut), `target-agent/` |
| **D2** | **Jorge Bustamante** | @jorgeb-py | **Designer / Compilador** | `harness_spec` + regeneración (T2) + el dominio/grafo | [C3](./03-components.md#c3--designer--compilador--owner-d2-jorge), `domain/` |
| **D3** | Alex Barraza | @alexbzal | Sandbox / Executor | sandbox + executor + oráculo + honeypot + módulos de ataque | [C4](./03-components.md#c4--executor--sandbox--owner-d3-alex), [C5](./03-components.md#c5--módulos-de-ataque--owner-d3-alex), [C6](./03-components.md#c6--oráculo--owner-d3-alex) |
| **D4** | Miguel Aguilar | @EclipseIDEHater | Frontend / Dashboard | 4 pantallas + SSE + reproducción visual + ensayo del demo | [C9](./03-components.md#c9--dashboard--owner-d4-miguel), `frontend/` |
| **D5** | Laura Martínez | @laura-martinez-galindo | Analista + Mitigación LLM | prompts Analista + Mitigación + enforcement + telemetría | [C2](./03-components.md#c2--analista-llm--owner-d5-laura), [C7](./03-components.md#c7--mitigación-llm--owner-d5-laura), [C8](./03-components.md#c8--enforcement--owner-d5-laura) |

> D1 y D2 conocen ambos la cadena Extractor→Analista→Designer (redundancia sobre la parte más riesgosa).

## Cadena crítica (serial — no la paralelicen)

```
Extractor(D1) → Analista(D5) → Designer(D2) → Sandbox(D3) → loop
```

Meter más gente aquí no acelera; emparejar aquí es para que el sueño no mate la cadena. El
**dashboard (D4)** es lo más paralelizable: arranca contra datos mockeados y el contrato SSE.

## Cronograma (planeado hacia atrás desde el deadline)

> Turnos de sueño rotativos: **siempre 3+ despiertos**, nadie de la cadena crítica dormido a la vez.

| Bloque | Objetivo | Checkpoint |
|---|---|---|
| **T+0 → T+3** | `docker compose`/`uv` en las 5 máquinas · **puertos e interfaces definidos** · agente vulnerable v0 · **los 3 schemas Pydantic acordados** · demo-script firmado | Skeleton compila, dominio con puertos mockeados |
| **T+3 → T+9** | Extractor produce `architecture.json` **real** · Analista LLM produce `threat_analysis` · Designer compone `harness_spec` · Sandbox corre el agente | Walking skeleton: arch → analysis → spec → run |
| **T+9 → T+15** | Oráculo canary dispara · `cmd_injection` confirma 1 exploit end-to-end | **Un exploit confirmado por oráculo** |
| ⚠️ **Cut-line T+15** | Si el Designer no compone desde plantillas → degradar a spec semi-fijo **parametrizado por hallazgos** (sigue architecture-aware). Activar antes de T+15 si el skeleton de T+9 no compiló limpio. | — |
| **T+15 → T+21** | Mitigación LLM genera `policy` · Enforcement la aplica · Designer **regenera** regresión · re-corre · **CERRADO** | **T2 completo: el loop da una vuelta** |
| **T+21 → T+25** | Módulo MCP · agregar 2ª tool al agente → **harness recompila distinto** · frontend integra todo | **T1 completo: arquitectura cambia → harness cambia** |
| **Dom 09:00 · FREEZE** | Solo P0 · seed data · feature flags · **2 ensayos cronometrados · video de respaldo grabado** | Demo end-to-end estable |
| **Dom 09:00 → 12:00** | Pulido visual · README · slides de roadmap-como-adaptadores | — |
| **Dom 12:00 → 13:00** | Buffer + ensayo final | 🎤 Presentación |

## Guion del demo (4 minutos)

```
0:00  "Este agente tiene una tool de shell y un MCP de Notion. Se ve bien."
0:20  T1 - Corremos el compilador. El Analista LLM lee la arquitectura y encuentra
      la cadena de riesgo; el Designer COMPILA un harness_spec a la medida.
1:00  Executor en sandbox aislado con escape-probe. Ataque dirigido de cmd_injection.
      El canary llega al honeypot -> exploit confirmado. "No es opinion de un LLM: es hecho."
1:45  T2 - El sistema genera la mitigacion, la aplica, y el DESIGNER REGENERA el test.
      Re-corremos: exploit ahora BLOQUEADO. Regresion cerrada. El loop cierra.
2:45  T1 de nuevo - Agregamos una tool al agente. Recompilamos: harness_spec CAMBIA,
      aparece una nueva superficie y un nuevo ataque.
3:15  Motivacion - el caso OpenAI/Hugging Face: escape de un sandbox mal aislado.
      La leccion: verificar el aislamiento activamente. Es lo que hace escape-probe.
3:35  Roadmap - arquitectura hexagonal: cada pieza que cortamos es un adaptador.
      "La puerta queda abierta por diseno."
3:55  Cierre: "Compilamos seguridad desde la arquitectura del agente, y cerramos
      el loop con pruebas reales."
```

## Git / flujo de trabajo

- **Trunk-based con PRs cortos.** `main` siempre compila. Nadie pushea roto a `main`.
- Rama por dev: `d1-extractor`, `d2-designer`, `d3-sandbox`, `d4-frontend`, `d5-llm`.
- **El contrato (`contracts/` Pydantic) se toca solo con aviso** en el canal — es la interfaz de todos.
- Deploy (Vercel/Render) desde repo personal espejo (ver README del repo raíz).

## Checklist de arranque (primeras 3 h)

- [ ] Monorepo `uv`/`pyproject` + `frontend/` Vite en las 5 máquinas
- [ ] `domain/ports.py` con los 9 puertos (mockeados) → desbloquea a los 5 en paralelo
- [ ] Agente vulnerable de prueba v0 (shell tool + 1 MCP + flujo user→shell)
- [ ] Los 3 schemas Pydantic (`architecture`, `threat_analysis`, `harness_spec`) acordados por D1↔D2↔D5
- [ ] Honeypot FastAPI + un canary token plantable
- [ ] Prompt del Analista LLM + `.with_structured_output` validando `ThreatAnalysis`
- [ ] Contrato de eventos SSE firmado → D4 arranca con mocks
- [ ] `demo-script.md` firmado por los 5
- [ ] Turnos de sueño asignados (cadena crítica nunca sin cobertura)
- [ ] Slide de motivación con el caso OpenAI/Hugging Face listo

## Riesgos y mitigaciones

| Riesgo | Prob. | Mitigación |
|---|---|---|
| El Designer se vuelve agujero negro por generalizar | Alta | Cut-line T+15 → spec semi-fijo parametrizado. Sigue probando T1 |
| Docker anidado falla en el venue | Media | `SubprocessSandbox` como adaptador de respaldo (mismo puerto) |
| El LLM devuelve JSON inválido | Media | `.with_structured_output` + reintento con `ValidationError`; cachear el análisis |
| El loop no cierra a tiempo | Media | La regeneración puede ser una regla simple; lo que importa es el spec CAMBIA y el ataque falla |
| "Adaptivo" no se ve en el demo | Media | Comprimir a UNA vuelta visible; ensayarla hasta que salga sola |
| Frontend inconsistente al final | Media | shadcn/ui sin personalizar, 4 pantallas, D4 protegido para el final |
