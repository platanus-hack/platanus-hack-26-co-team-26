# :core

**Propósito:** lógica de dominio pura del proyecto — motor DTN, BundleStore,
criptografía, DSP de señal (PPG/movimiento), políticas y casos de uso. Kotlin
Multiplatform con un único target activo (`androidMain`); `iosMain` declarado y
vacío hasta la Fase 2.

**Puertos que expone:** ver `src/commonMain/kotlin/co/helius/core/application/ports/`
(`TransportPort`, `BundleStorePort`, `LocationPort`, `MotionPort`, `PpgCaptureIPort`,
`BiomarkerInferencePort`, `IdentityPort`, `PowerPolicyPort`, `CloudSyncPort`,
`AlertReceiverPort`, `ClockPort`).

**Regla no negociable:** `:core:domain` no importa `android.*`, `androidx.*`,
`io.ktor.*`, ni ningún SDK — verificado en cada PR por `arch-guard` (Konsist +
`.importlinter`). Todo lo que toca hardware/plataforma se declara `expect` aquí y
se implementa como `actual` en `androidMain`.

**Dueño:** Helmut (motor DTN, transporte, criptografía) — compartido con Alex
(señal/AIB) y Miguel (backend consumidor). Ver `docs/team/DIVISION-DE-TRABAJO.md`.

**Etiqueta de madurez:** `ENGINEERING` (esqueleto generado, implementación en curso).
