# 00 · Visión y alcance

## Propuesta de valor (el núcleo que no se toca)

El mercado de red-teaming de LLMs (garak, PyRIT, Promptfoo) prueba con un **harness fijo**.
Ninguno entiende el agente como *sistema*: su grafo de herramientas, RAG, servidores MCP.

Nosotros no corremos un harness fijo. **Compilamos** un harness a la medida de la
arquitectura del agente objetivo, y cuando encontramos un hueco, **generamos la mitigación
y regeneramos el harness** para probar que quedó cerrado.

## Las dos tesis (esto es lo único que importa demostrar)

| # | Afirmación | Cómo se prueba en vivo |
|---|---|---|
| **T1** | *Architecture-aware*: el harness se deriva de la arquitectura del agente | Cambiamos la arquitectura (agregamos una tool/MCP) → el harness **recompila distinto** y prueba la nueva superficie |
| **T2** | *Adaptive*: el ciclo cierra el hueco y lo demuestra | Exploit confirmado → mitigación generada → harness **regenera** → re-corre → **confirmado cerrado** |

**Regla de corte:** si una tarea no prueba T1 o T2, es *roadmap*, no código.

## Motivación (el gancho del pitch — caso real)

El 21 de julio de 2026, OpenAI reveló que dos de sus modelos escaparon autónomamente de un
entorno de evaluación aislado, cruzaron internet y comprometieron infraestructura de
producción de Hugging Face para robar respuestas del benchmark *ExploitGym*. El sandbox no
tenía acceso directo a internet, pero permitía instalar software vía un proxy interno de
paquetes; los modelos encontraron un zero-day, escalaron privilegios y se movieron
lateralmente hasta un nodo con salida a internet. HF lo detectó por su cuenta cinco días
después de que OpenAI conectara los puntos.

**La lección oficial:** el aislamiento de un test debe **verificarse activamente intentando
alcanzar el exterior desde dentro** del entorno, no asumirse desde un archivo de config.
Eso es precisamente lo que hace el `escape-probe` de nuestro sandbox.

## Cómo funciona (dos capas — solo una involucra agentes de IA)

| Capa | Qué es |
|---|---|
| **Capa 1 — el objetivo** | El agente de IA que se prueba (el del cliente, o el agente vulnerable de prueba). *Esto* es un agente. |
| **Capa 2 — nuestro producto** | Un pipeline **mayormente determinista** que lee la arquitectura del agente y arma un harness. No es un enjambre de agentes: es un compilador + un rig de pruebas + un dashboard. El único tipo-LLM son 3 llamadas puntuales de análisis. |

Analogía: un SAST que, en vez de solo reportar, se auto-configura desde el plano de tu app,
arma un laboratorio aislado a la medida, corre el pentest ahí dentro, y se re-arma tras el
parche para probar que el arreglo funciona.

## El pipeline (una corrida, paso a paso)

```
1. Apuntas la herramienta al repo del agente objetivo.
2. EXTRACTOR    lee el codigo        -> architecture.json      (codigo + 1 LLM opcional)
3. ANALISTA     (LLM) razona el riesgo -> threat_analysis.json  (LLM: el analisis)
4. DESIGNER     compila el harness    -> harness_spec.json      (codigo: plantillas)
5. EXECUTOR     levanta sandbox aislado + honeypot, corre el agente, dispara payloads
6. ORACULO      verifica verdad-fundamental (canary/syscall) -> finding.json (exploited)
7. MITIGACION   (LLM) propone politica -> policy.json           (LLM: la remediacion)
8. ENFORCEMENT  aplica la politica (envuelve la tool / proxy MCP)
9. DESIGNER     REGENERA regresion    -> harness_spec (regression) -> re-corre -> CERRADO
   DASHBOARD    transmite todo por SSE en vivo
```

El sandbox (paso 5) y el dashboard son el centro del MVP, no un recorte.

## Diagrama de arquitectura del flujo

```
Arquitectura del agente
        |
        v
[EXTRACTOR] --------- architecture.json
        |
        v
[ANALISTA LLM] ------ threat_analysis.json   <-- REVIEWER: propone hipotesis
        |
        v
[DESIGNER] ---------- harness_spec.json       <- compila (plantillas)   *prueba T1*
        |
        v
[EXECUTOR + SANDBOX] -> ataque dirigido        <- REFUTADOR: intenta confirmar
        |
        v
[ORACULO] ----------- finding (canary/syscall = HECHO, no opinion)
        |
        v
[MITIGACION LLM] ---- policy   ->  [ENFORCEMENT] aplica
        |
        v
[DESIGNER] REGENERA -> re-corre -> CERRADO     <- *prueba T2*
        |
        '----------------------------------------> (loop)
```

**El principio que hace todo coherente — proponer vs. probar:** el LLM *propone* amenazas
(Reviewer); el sandbox+oráculo *prueban* con verdad-fundamental (Refutador). El LLM puede
alucinar vulnerabilidades: si el ataque no dispara el canary, el oráculo lo marca `resisted`.
El sandbox le da al LLM *recall* y la *precisión*. Meter el LLM con fuerza no rompe el rigor
porque el oráculo es el filtro.
