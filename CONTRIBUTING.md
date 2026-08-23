# Contribuir a SismoMesh

## Arranque rápido

```bash
make bootstrap   # Gradle wrapper, venv de servicios, node_modules web
make proto       # regenera contratos Kotlin/Python/TypeScript desde protocol/
make up          # levanta Postgres/PostGIS, Redis, MinIO, API
make test        # core (JVM) + servicios (pytest) + web (vitest)
make lint        # ktlint+detekt, ruff, eslint
make arch-check  # arch-guard: Konsist + import-linter + vocabulario prohibido
```

## Reglas de arquitectura (no negociables)

- `:core:domain` no importa `android.*`, `androidx.*`, `io.ktor.*`, ni ningún SDK — verificado por `arch-guard` en cada PR.
- Todo puerto nuevo → interfaz en `application/ports` + adaptador real + *fake* determinista.
- Ningún cambio manual en código generado desde `protocol/*.proto` (`make proto` regenera).
- Vocabulario clínico prohibido (ver `docs/glossary.md`) — el linter de CI bloquea el PR.

## Definition of Done (por PR)

- [ ] `:core` no importa Android ni frameworks (verificado por `arch-guard`/Konsist).
- [ ] Puerto nuevo → interfaz + adaptador real + adaptador fake.
- [ ] Vectores de test actualizados si cambió el protocolo.
- [ ] Tests unitarios y al menos un test de integración o de DTN.
- [ ] `README.md` del módulo actualizado con etiqueta de madurez.
- [ ] Sin vocabulario clínico prohibido (linter de términos en CI).
- [ ] Sin PII en logs (linter de logging).
- [ ] Impacto en batería medido si toca radios o sensores.
- [ ] Si toca transporte: probado en al menos 3 fabricantes distintos (ver `docs/validation/`).
- [ ] Si toca radios/hardware/cripto: pasa los 4 niveles de `docs/validation/PHONE-READINESS.md` (L0 compila, L1 tests JVM, L2 instrumented test, L3 campo) — no basta con "revisado por inspección".

## Estrategia de ramas y commits

Ver `docs/team/DIVISION-DE-TRABAJO.md` § Estrategia de ramas. Conventional Commits
(`feat(transport): ...`, `fix(dtn): ...`, `docs(protocol): ...`). Mínimo 1
aprobación, CI verde obligatoria, `CODEOWNERS` por carpeta. Cambios en `protocol/`
o en `core/domain` requieren un ADR aprobado (`docs/architecture/ADR/`, plantilla
en `0000-template.md`).

## Ritmo de trabajo

- Sincronización diaria de 15 minutos: qué bloquea el Vertical Slice actual (`docs/roadmap/VERTICAL-SLICES.md`).
- Demo obligatoria cada 48 horas.
- Congelación de contratos los lunes; cambios de protocolo solo en ventana acordada.

## Riesgos principales y respuesta

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Fabricantes matan el foreground service | Alto | Matriz por fabricante, guía de onboarding, reinicio del servicio, honestidad sobre el degradado. |
| Fragmentación de Wi-Fi Aware | Medio | Cascada de transportes; el sistema funciona solo con BLE. |
| Escombro real bloquea RF más de lo esperado | Alto | Es un resultado válido: se mide, se publica y se ajusta la promesa. La palanca es la densidad de nodos, no la potencia. |
| Ausencia de iOS reduce densidad de malla | Medio | Portal cautivo del rescatista cubre a personas conscientes con iPhone; despliegue focalizado por comunidad/edificio. |
| Dataset PPG insuficiente | Medio | `HeuristicFallback` garantiza funcionalidad sin ML. |
| Alcance excesivo con 5 devs | Alto | Slices verticales + lista "fuera del MVP" firmada. |
| Rechazo en Play Store por permisos | Medio | Justificación preparada desde el inicio, contacto previo a la publicación. |
| Uso indebido de datos por terceros | Alto | Tres vistas, cifrado break-glass, auditoría. |
