# core/src/iosMain — vacío (Fase 2)

Este source set queda **declarado y desactivado** a propósito (ver `core/build.gradle.kts`,
target `iosX64/iosArm64/iosSimulatorArm64` comentado).

No añadir código aquí hasta que se cumplan las precondiciones de
`docs/roadmap/VERTICAL-SLICES.md § 19bis — Plan de entrada de iOS`:

1. `core/commonMain` sin un solo import de Android (verificado en cada PR por `arch-guard`).
2. `iosMain` declarado en Gradle pero vacío y comentado (este archivo).
3. Todos los `expect` documentados con la nota de cómo se implementarían en iOS.
4. Solicitud de entitlement de Wi-Fi Aware y de Critical Alerts iniciada con antelación.
5. El protocolo no asume capacidades exclusivas de Android en el handshake.

**Disparador:** Slice 4 demostrado, o alianza institucional que lo exija.

Dueño de esta precondición: Helmut (revisar en cada PR que nada de Android se filtre a `commonMain`).
