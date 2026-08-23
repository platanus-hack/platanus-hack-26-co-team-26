# Implementación PPG→ECG estimado

## Decisión concreta

La mejor arquitectura para este proyecto no es ejecutar un Transformer-GAN grande en el teléfono. Se utilizará un sistema **teacher–student con restricciones fisiológicas**:

1. **Teacher offline:** modelo de alta capacidad entrenado con PPG–ECG simultáneos; puede usar encoder Transformer/TCN y discriminador solo durante entrenamiento.
2. **Student móvil:** Tiny-TCN bidireccional no causal con convoluciones separables, salida de ECG estimado y cabeza de incertidumbre.
3. **Destilación:** el student aprende del ECG real y de las representaciones del teacher.
4. **Gate independiente:** una señal mala o una incertidumbre alta impide presentar la reconstrucción.

Esto conserva la capacidad del modelo grande durante el entrenamiento sin introducir su RAM, latencia y tamaño en Android.

## Limitación física

La PPG mide la respuesta hemodinámica periférica y no la actividad eléctrica. Ondas P, QRS y T no están contenidas de forma única en la PPG. El sistema genera una **estimación condicionada**, no recupera un ECG que haya sido medido.

Además, 30 FPS tiene Nyquist de 15 Hz y no preserva todo el ancho de banda del QRS. Interpolar a 120 Hz no crea información nueva. Por ello se definen dos modos:

### Modo estándar

- PPG de cuadros a 30 FPS.
- Interpolación versionada a 120 Hz.
- Reconstrucción útil para sincronía de pulsos, RR y una representación ECG-like.
- Morfología fina e intervalos eléctricos se marcan como no confiables.

### Modo RS-PPG avanzado

- Aprovecha el rolling shutter y calcula intensidad por grupos de filas.
- Usa `SENSOR_ROLLING_SHUTTER_SKEW`/metadatos equivalentes cuando estén disponibles.
- Objetivo efectivo: 120–150 muestras/s.
- Se habilita solo en teléfonos validados mediante whitelist de cámara/configuración.
- Si el hardware/ISP no conserva temporalidad por filas, se vuelve al modo estándar.

La investigación publicada sobre RS-PPG ha demostrado 150 Hz efectivos a partir de sensores de 30 FPS, pero la portabilidad entre teléfonos debe validarse.

## Señal de entrada normalizada

Toda entrada se representa a 120 Hz durante 15 s:

```text
shape = [1, 1800, 5]
channels:
  ppg_normalized
  first_derivative
  second_derivative
  motion
  acquisition_bandwidth_flag
```

`acquisition_bandwidth_flag` vale de forma continua según la resolución temporal efectiva; evita que el modelo interprete PPG interpolada como PPG realmente muestreada a alta frecuencia.

## Salida

```text
estimated_ecg_mean:       [1, 1800, 1]
estimated_ecg_logvar:     [1, 1800, 1]
reconstruction_quality:   [1, 1]
```

- Frecuencia: 120 Hz.
- Derivación objetivo: Lead II normalizada.
- Amplitud: unidades normalizadas; no mV salvo calibración individual demostrada.
- Toda UI y payload usan el nombre `estimated_ecg`, nunca `ecg` a secas.

## Student móvil

```text
SeparableConv1D stem, 24 canales
Residual TCN blocks, dilations 1/2/4/8/16, 24–48 canales
FiLM conditioning por SQI/modo de adquisición
SeparableConv1D decoder
Heads: mean, log-variance y reconstruction quality
```

Presupuesto:

| Recurso | Objetivo |
|---|---:|
| Parámetros | <250.000 |
| Modelo INT8 | <1 MB |
| Activaciones pico | <8 MB |
| Inferencia p95 CPU | <40 ms en teléfono mínimo |
| Ventana | 15 s, procesamiento por lote al terminar |

## Teacher offline

El teacher puede emplear:

- encoder TCN + atención;
- decoder U-Net 1D;
- discriminador multiescala únicamente para entrenamiento;
- preentrenamiento autosupervisado con masked-signal modeling;
- consistencia ECG→PPG mediante un modelo forward congelado.

No se exporta a Android.

## Función de pérdida

```text
L = 1.00 * Huber waveform
  + 0.30 * derivative loss
  + 0.25 * multi-resolution STFT loss
  + 0.35 * R-peak / QRS timing loss
  + 0.20 * ECG→PPG cycle consistency
  + 0.30 * teacher feature distillation
  + 0.10 * calibrated heteroscedastic NLL
```

Un discriminador puede mejorar realismo durante entrenamiento, pero nunca debe ser la única razón para considerar fiel una reconstrucción: una señal visualmente realista puede ser fisiológicamente incorrecta.

## Datos y sincronización

### Preentrenamiento

- BIDMC: ECG/PPG a 125 Hz.
- MIMIC-III Waveform Matched: grandes volúmenes de ECG/PPG simultáneos.

### Adaptación obligatoria al smartphone

Recolectar por persona:

```text
camera PPG + timestamps + metadata Camera2
reference contact PPG
reference Lead II ECG >=250 Hz
accelerometer/gyroscope
device/camera/exposure/ISO/torch
```

Sincronizar con un evento común o reloj compartido y luego refinar desfase mediante correlación. El modelo debe conservar el pulse-arrival time como variable; no se debe alinear cada latido de manera que se oculte la variación real.

## Entrenamiento

1. Limpiar y sincronizar señales, conservando segmentos malos etiquetados.
2. Resamplear referencias ECG a 120 Hz para el student.
3. Split por sujeto antes de crear ventanas.
4. Preentrenar teacher con datasets clínicos.
5. Adaptar teacher con pares smartphone–ECG.
6. Entrenar student con ground truth + distillation.
7. Calibrar incertidumbre en validation.
8. Evaluar cohorte bloqueada y dispositivos no vistos.
9. Cuantizar INT8 con ventanas reales representativas.
10. Comparar FP32/INT8 y activar solo si pasa todos los gates.

## Validación específica

- MAE, RMSE, correlación y PRD de waveform.
- F1 de R-peaks con tolerancia temporal predefinida.
- Error de RR y frecuencia.
- Error de área/duración QRS.
- PR/QT reportados solo como análisis investigativo.
- Cobertura de intervalos de incertidumbre.
- Resultados por sujeto, teléfono, tono de piel, movimiento y modo 30/RS-PPG.
- Validación externa cruzada BIDMC↔MIMIC y cohorte smartphone.
- Comparar utilidad del PPG directo contra PPG+estimated ECG; si no aporta mejora externa, no influye en el IFO aunque pueda visualizarse como investigación.

## Integración Android

```text
PPG capture
  → preprocessing/SQI
  → resample or RS-PPG assembly at 120 Hz
  → EstimatedEcgReconstructor (LiteRT INT8)
  → uncertainty gate
  → estimated_ecg result
```

El reconstructor se carga una vez y reutiliza buffers preasignados. Si falta el modelo, falla su hash o la temperatura del dispositivo es severa, el módulo conserva la evaluación PPG y marca `estimated_ecg_unavailable`.

## Criterio de presentación

Presentar:

> “Representación ECG estimada a partir de señal óptica. No corresponde a una medición eléctrica y no debe interpretarse como diagnóstico.”

No presentar nombres de enfermedades, conductas terapéuticas ni prioridad clínica desde esta salida.
