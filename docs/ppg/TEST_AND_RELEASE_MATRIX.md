# Matriz de pruebas y liberación

## Pruebas unitarias

| Componente | Casos mínimos |
|---|---|
| RGB/YUV | strides distintos, ROI pequeña, saturación, buffer incompleto |
| Resampling | jitter, frames duplicados, gaps, 24/30/60 FPS |
| Filtros | fixtures Python/Kotlin, bordes, señal constante, NaN rechazado |
| Peaks/BPM | 45, 70, 120, 180 BPM sintéticos; ectópicos simulados |
| SQI | sin dedo, presión, movimiento, saturación, baja pulsatividad |
| ECG input | forma 1800×5, flag de ancho de banda, límites |
| ECG adapter | outputs inválidos, incertidumbre, quality gate |
| IFO | señal mala domina; ECG deshabilitado por defecto |
| Codec | golden vectors, CRC, endianness, valores desconocidos |

## Pruebas instrumentadas Android

- Permiso concedido/denegado/revocado.
- Cámara trasera ocupada por otra app.
- Dispositivo sin torch.
- Background durante estabilización/adquisición/procesamiento.
- Rotación de pantalla y recreación de Activity.
- Cancelación repetida e idempotente.
- Dos intentos de inicio simultáneo.
- Llamada entrante/interrupción del lifecycle.
- Memoria baja y thermal throttling.
- 20 sesiones consecutivas: cero torch/camera leak.

## Matriz de hardware

| Nivel | Mínimo |
|---|---:|
| Camera2 LEGACY | 2 modelos |
| LIMITED | 3 modelos |
| FULL/LEVEL_3 | 3 modelos |
| Fabricantes | Samsung, Xiaomi/Motorola, Pixel u otros tres principales objetivo |
| Android | versión mínima, intermedia y actual |

## Benchmark

Medir mediante Macrobenchmark/Perfetto:

- tiempo de inicialización;
- FPS efectivo y gaps;
- CPU promedio/pico;
- RAM PSS pico;
- latencia DSP p50/p95;
- latencia de cada modelo p50/p95;
- energía/temperatura después de sesiones repetidas;
- tamaño incremental del APK/AAB.

## Gates de software

- Unit tests 100 %.
- Instrumented lifecycle tests 100 %.
- Sin crash/ANR en matriz objetivo.
- Cero persistencia de frames.
- Cero cámara/torch activo tras estados terminales.
- Hash inválido siempre bloqueado.
- Señal rechazada nunca produce IFO disponible.
- Estimated ECG no rotulado nunca llega a UI.

## Modos de liberación

```text
baseline     PPG/SQI/reglas; sin IA
shadow       IA ejecuta, no se muestra ni influye
research     visible solo con consentimiento y etiqueta investigativa
approved     modelo puede mostrarse según intended-use aprobado
revoked      bloqueado y rollback automático
```

No promover directamente de `shadow` a `approved`; debe pasar por reporte de validación bloqueado y revisión de riesgos.
