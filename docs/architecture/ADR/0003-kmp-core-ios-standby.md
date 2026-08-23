# ADR-0003: `:core` es Kotlin Multiplatform aunque solo compile Android

**Estado:** aceptada
**Fecha:** 2026-08-22
**Dueño:** Helmut

## Contexto

Escribir `:core` en Kotlin "normal" (JVM/Android puro) sería más simple hoy, pero
forzaría reescribir ~60% del código crítico (motor DTN, criptografía, protocolo,
políticas, máquina de estados de encuentro) cuando entre iOS en Fase 2.

## Decisión

Todo lo que es lógica pura vive en `commonMain`, sin un solo `import android.*`.
Lo que toca radios, sensores, cámara o almacén seguro se declara `expect` en
`commonMain` y se implementa como `actual` en `androidMain`. `iosMain` se declara
en `build.gradle.kts` y se deja vacío y comentado.

**Regla de oro:** si un archivo de `commonMain` necesita importar algo de
`android.*`, ese código está en el módulo equivocado. La CI (`arch-guard.yml`) lo
verifica en cada PR.

## Consecuencias

Cuesta unas horas de disciplina hoy (mantener la frontera `expect`/`actual`
limpia); evita una reescritura de meses en Fase 2.
