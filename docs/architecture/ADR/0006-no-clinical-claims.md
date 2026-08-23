# ADR-0006: Ninguna afirmación clínica — AIB es evidencia, no diagnóstico

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** Alex + Laura

## Contexto

La regla de oro del proyecto (README raíz): *"No prometemos encontrar a nadie.
Prometemos que la información que puede ayudar a encontrarte no desaparezca cuando
desaparece tu infraestructura."* Cualquier texto que prometa detección garantizada,
diagnóstico médico o predicción sísmica es un bug de severidad crítica, no una
decisión de marketing.

## Decisión

El módulo se llama **Análisis e Interpretación de Biomarcadores (AIB)** en código,
UI, documentación y material comercial — nunca "triage", "diagnóstico", "signos
vitales médicos". Todo resultado se presenta como evidencia con incertidumbre,
con el descargo: *"Estimación experimental. No es un dispositivo médico ni
sustituye evaluación profesional."* Ver `docs/glossary.md` (vocabulario obligatorio
y prohibido) y las restricciones no negociables en el `README.md` raíz.

## Consecuencias

- Linter de vocabulario clínico en CI (`arch-guard.yml`, `.pre-commit-config.yaml`)
  bloquea PRs que introduzcan términos prohibidos.
- El estado `UNCONFIRMED` existe; `INJURED`/`DEAD`/`ALIVE` **no existen** en ningún
  enum del sistema — nunca se declaran nombres en ninguna capa.
