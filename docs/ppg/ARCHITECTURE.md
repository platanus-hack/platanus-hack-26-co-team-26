# Arquitectura técnica

## 1. Principios

1. **Offline-first:** ninguna medición urgente depende de FastAPI o Internet.
2. **Quality-first:** si la señal no es confiable, la única salida permitida es `UNRELIABLE_MEASUREMENT`.
3. **No video at rest:** no se crea MP4/JPEG. Los cuadros se procesan y cierran inmediatamente.
4. **Fail closed:** un error de cámara, modelo o preprocesamiento no genera una clase fisiológica.
5. **Separación científica:** PPG real, rasgos derivados y ECG estimado nunca se confunden.
6. **Versionado:** resultado, configuración, preprocesador y modelo llevan versiones explícitas.

## 2. Componentes

### Android

- `CameraXFrameSource`: lifecycle, cámara trasera, torch, resolución y backpressure.
- `RgbFrameAnalyzer`: ROI y estadísticas RGB sin construir bitmaps.
- `MotionSampler`: acelerómetro/giroscopio a 30–50 Hz.
- `PpgSessionController`: máquina de estados y timeout.
- `PpgSignalProcessor`: remuestreo, filtrado y extracción de pulsos.
- `SignalQualityEvaluator`: gates independientes del clasificador.
- `SafetyFirstClassifier`: baseline transparente.
- `TinyTcnClassifier`: adaptador LiteRT futuro.
- `PpgPacketCodec`: payload binario compacto con CRC.

### Python/FastAPI

- Ingesta de datasets y registro de procedencia.
- Generación determinista de ventanas.
- Entrenamiento por grupos de sujeto.
- Calibración, validación y cuantización.
- Registro de modelos aprobados y manifiesto SHA-256.
- FastAPI puede distribuir versiones, pero Android conserva una versión funcional empacada.

## 3. Máquina de estados

```text
IDLE → PREPARING → STABILIZING → ACQUIRING → PROCESSING → COMPLETED
                    ↘             ↘            ↘
                      FAILED / CANCELLED / QUALITY_REJECTED
```

Reglas:

- El torch solamente puede estar activo entre `STABILIZING` y el final de `ACQUIRING`.
- Toda transición terminal ejecuta limpieza idempotente.
- `ACQUIRING` termina al reunir muestras válidas, no solamente por tiempo de reloj.
- Timeout recomendado total: 25 s para obtener una ventana rápida de 15 s.

## 4. Adquisición

Configuración inicial:

```text
Lens: BACK
Image format: YUV_420_888
Resolution target: 640×480 o la más cercana
Backpressure: KEEP_ONLY_LATEST
Torch: ON
Audio: OFF
Persistent storage: OFF
```

ROI inicial: cuadrado central equivalente al 35–50 % del lado menor. Se muestrea cada dos píxeles para reducir CPU. La implementación debe respetar `rowStride` y `pixelStride` de los planos YUV.

Durante los primeros 1.5 s se permite autoexposición. Después se intenta estabilizar AE mediante Camera2Interop cuando el hardware lo soporte. Si no se soporta, se registra el modo y el SQI absorbe la variación.

## 5. Señal

Cada cuadro produce:

```text
timestampNs, meanR, meanG, meanB, lumaStd, saturatedFraction,
coverageScore, motionMagnitude
```

No se asume FPS perfecto. La serie se ordena por timestamp, se eliminan duplicados y se reinterpola linealmente a 30 Hz.

Preprocesamiento versionado `ppg-pre-v1`:

1. Selección/fusión de canal según SNR y saturación.
2. Winsorización robusta por mediana/MAD.
3. Remoción de tendencia local.
4. Baseline de detrending + low-pass cero-fase aproximado a 4 Hz. Antes de validación final puede sustituirse por un filtro Butterworth/SOS 0.5–4 Hz, siempre que Python y Kotlin mantengan equivalencia numérica.
5. Normalización robusta por mediana/MAD.
6. Primera y segunda derivadas.
7. Detección de picos con periodo fisiológico restringido.

Para portabilidad exacta, entrenamiento y Android deben compartir fixtures numéricos y tolerancias. No basta con implementar filtros “parecidos”.

## 6. SQI y orden de gates

Los gates se ejecutan en este orden:

1. Integridad temporal: FPS efectivo, gaps y duración.
2. Cobertura: intensidad roja y diferencia respecto a cámara descubierta.
3. Saturación: píxeles recortados altos/bajos.
4. Movimiento: acelerómetro y discontinuidades ópticas.
5. Pulsatilidad: energía en 0.5–4 Hz frente a energía total.
6. Consistencia: intervalos y morfología entre pulsos.

El SQI final es 0–100. Umbrales iniciales de ingeniería:

- `>=70`: utilizable.
- `50–69`: repetir si es posible; no emitir clase crítica.
- `<50`: rechazar.

Estos umbrales deben calibrarse con datos; no son valores clínicos.

## 7. Modelo Tiny-TCN

Entrada fija:

```text
shape = [1, 450, 4]
channels = normalized_ppg, d1, d2, motion
window = 15 seconds at 30 Hz
```

Arquitectura:

```text
SeparableConv1D(24, k=7)
3 residual TCN blocks, dilations 1/2/4, channels 24/32/48
GlobalAveragePooling1D
Dense(32)
Heads:
  physiology_logits[6]
  quality_probability[1]
```

La clase `UNRELIABLE_MEASUREMENT` no debe aprenderse solamente como una clase común: el gate SQI externo domina y el segundo head actúa como verificación.

Pérdida:

```text
L = focal_loss(physiology) + 0.35 * BCE(quality) + regularización
```

La arquitectura debe permanecer por debajo de 100k parámetros. Exportar primero FP32 para equivalencia y luego INT8 con un conjunto representativo que incluya dispositivos, tonos de piel y artefactos.

## 8. Motor de decisión

```text
if hardQualityGateFails:
    UNRELIABLE_MEASUREMENT
else:
    features = deterministicEstimator(ppg)
    ai = tinyTcn(ppg, d1, d2, motion)
    result = safetyPolicy(features, ai, calibratedThresholds)
```

Las reglas deterministas pueden elevar cautela, pero nunca convertir una medición mala en válida. La aplicación debe mostrar las métricas observadas y la confianza calibrada, no una certeza clínica.

## 9. Componente PPG→ECG estimado

La rama PPG→ECG forma parte de la arquitectura, pero queda detrás de un gate de aprobación independiente:

- Entrenar únicamente con PPG y ECG simultáneos y sincronizados.
- Evaluar por sujeto y dataset externo.
- Medir error morfológico de QRS/PR/QT además de RMSE.
- Prohibir diagnóstico, prioridad clínica o conducta médica basada en la reconstrucción.
- Etiquetar siempre `estimated_ecg`.
- Reportar modo de adquisición, incertidumbre y ancho de banda efectivo.
- No transmitirla por defecto, porque aumenta payload y riesgo de interpretación; usar un paquete versionado independiente.

La implementación seleccionada es teacher–student: un modelo grande se entrena offline y transfiere conocimiento a un Tiny-TCN/decoder convolucional cuantizado para Android. La especificación completa está en `docs/PPG_TO_ECG.md`.

## 10. Seguridad y privacidad

- Sin permiso de almacenamiento.
- Sin logs de RGB/PPG en producción salvo consentimiento explícito de estudio.
- Zeroización o liberación inmediata de buffers al terminar.
- Cifrado autenticado en la capa de transporte externa.
- Payload con `sessionId` aleatorio, no identificador personal.
- Manifest de modelo con hash, versión y fecha de aprobación.
- Rechazar modelos cuyo hash no coincida.

## 11. Observabilidad local

Registrar solamente métricas no sensibles:

- versión de módulo/modelo;
- dispositivo y nivel Camera2 anonimizado;
- duración, FPS y SQI;
- código terminal;
- latencia, RAM aproximada y temperatura/thermal status;
- nunca frames ni waveform sin modo de investigación consentido.
