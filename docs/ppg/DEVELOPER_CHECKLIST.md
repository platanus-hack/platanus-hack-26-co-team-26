# Checklist de entrega a desarrollo

## Antes de integrar

- [ ] Confirmar `applicationId`, minSdk y patrón de arquitectura de la app.
- [ ] Incorporar `ppg-core` como módulo, ajustando namespace si corresponde.
- [ ] Acordar que el módulo no crea video ni requiere almacenamiento.
- [ ] Acordar copy no diagnóstico y estados de error.

## Captura

- [ ] Cámara trasera disponible.
- [ ] Torch disponible o error explícito.
- [ ] `STRATEGY_KEEP_ONLY_LATEST`.
- [ ] `ImageProxy.close()` en `finally`.
- [ ] Timestamps monotónicos conservados.
- [ ] ROI respeta strides YUV.
- [ ] Movimiento sincronizado.
- [ ] Limpieza idempotente en todos los estados terminales.

## Señal

- [ ] Fixtures Python/Kotlin idénticos.
- [ ] Remuestreo por timestamp.
- [ ] Coeficientes de filtro congelados/versionados.
- [ ] SQI impide clasificación de señales inválidas.
- [ ] Métricas nulas se transmiten como desconocidas, nunca cero.

## IA

- [ ] Split por sujeto auditado.
- [ ] Dataset de cámara objetivo presente.
- [ ] Modelo FP32 validado.
- [ ] INT8 comparado contra FP32.
- [ ] Hash y manifiesto verificados.
- [ ] Estado del modelo = `approved` antes de influir en UI.
- [ ] Rollback probado.
- [ ] Manifest `approved`, SHA-256 y preprocesador verificados antes de cargar.
- [ ] ECG estimado permanece en shadow mode durante integración inicial.
- [ ] `allowEstimatedEcgContribution` permanece en `false` hasta aprobación independiente.

## Rendimiento y privacidad

- [ ] Sin archivos temporales de imagen/video.
- [ ] Peak RAM y latencia p95 medidos en dispositivo mínimo.
- [ ] Prueba térmica con sesiones repetidas.
- [ ] Funciona en modo avión.
- [ ] Logs de producción no contienen señal ni identificadores personales.

## Comunicación

- [ ] Golden vector del paquete v1 compartido con emisor/receptor.
- [ ] CRC probado.
- [ ] Cifrado/autenticación implementados por la capa de transporte.
- [ ] Versión incompatible se rechaza, no se interpreta parcialmente.

## Integración con la app

- [ ] La UI depende únicamente de `PpgEngine`, `PpgSessionState` y `PpgResult`.
- [ ] CameraX/LiteRT no aparecen en ViewModel o Composables.
- [ ] `onStop` y `onCleared` cancelan limpiamente.
- [ ] Los mensajes no usan terminología de clasificación clínica, diagnóstico, lesión, shock ni prioridad asistencial.
- [ ] `estimated_ecg` siempre incluye el aviso de que no es medición eléctrica.
