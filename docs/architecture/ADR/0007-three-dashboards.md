# ADR-0007: Tres vistas, tres niveles de exposición de datos

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** Miguel (vistas) + Helmut (cifrado break-glass)

## Contexto

En Colombia los datos de salud son datos sensibles bajo la Ley 1581; existe la
excepción de urgencia vital, pero eso **no** equivale a publicarlos en Internet.
Riesgos identificados: saqueo dirigido, acoso, fraude, suplantación, tratamiento
ilegal de datos de salud.

## Decisión

Tres vistas con niveles de acceso estrictamente distintos (`web/src/routes/`):

- **Pública** (`/mapa`, sin auth): área afectada, conteos agregados. Cero PII.
- **Familiar** (`/familia`, auth por vínculo consentido): estado con granularidad
  consentida por el usuario.
- **Respondiente** (`/ops`, auth por rol + organización): identidad, ubicación
  exacta, evidencia de movimiento/biomarcadores, datos crudos.

No se publica nombre, coordenada exacta, condición ni pulso en la vista pública,
sin excepción.

## Consecuencias

Cada endpoint del backend que devuelve PII debe escribir en `audit_log` **antes**
de responder (Sección 12.3) — verificado en revisión de PRs que tocan
`services/shared/src/api/adapters/http`.
