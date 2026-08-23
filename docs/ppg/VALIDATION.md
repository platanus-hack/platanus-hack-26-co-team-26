# Protocolo de validación

## 1. No confundir tres validaciones

1. **Analítica:** ¿la cámara recupera pulso/forma PPG frente a un sensor de referencia?
2. **Algorítmica:** ¿el clasificador reconoce las etiquetas definidas?
3. **De uso:** ¿una persona en condiciones realistas obtiene una medición válida rápidamente?

Ninguna sustituye a las otras.

## 2. Datos

### Preentrenamiento

- BIDMC: ECG y PPG simultáneos, 53 registros de 8 min a 125 Hz.
- MIMIC-III Waveform Matched: ECG/PPG/ABP/respiración en población hospitalaria.

Uso permitido: representación fisiológica y pruebas de pipeline. Limitación: la PPG clínica no tiene el mismo dominio que RGB de smartphone.

### Dataset objetivo indispensable

Recolectar simultáneamente:

- RGB de cámara y timestamps;
- PPG/pulsioxímetro de referencia;
- ECG de referencia cuando se investigue PPG→ECG;
- acelerómetro/giroscopio;
- dispositivo/cámara y parámetros de captura;
- temperatura periférica si es posible;
- protocolo/condición y etiquetas de referencia;
- metadatos demográficos necesarios para análisis de sesgo, con consentimiento.

Los estados como dolor, lesión o ansiedad no deben etiquetarse inferidos por pulso. Requieren protocolo y referencia independiente.

## 3. División de datos

- Split por `subject_id`; nunca ventanas del mismo sujeto en train y test.
- Mantener un conjunto externo por dispositivos no vistos.
- Si hay sitios distintos, reservar al menos un sitio para validación externa.
- Separar cronológicamente una cohorte prospectiva final.
- Todas las decisiones de arquitectura/umbral se cierran antes de abrir el test final.

Esquema recomendado:

```text
70 % sujetos train
15 % sujetos validation/calibration
15 % sujetos locked test
+ external device/site cohort
```

## 4. Baselines

Comparar Tiny-TCN contra:

1. Reglas deterministas de BPM/SQI.
2. Regresión logística sobre rasgos.
3. Gradient boosting pequeño sobre rasgos.
4. CNN 1D simple con presupuesto de parámetros equivalente.

Tiny-TCN solo se adopta si mejora sensibilidad/calibración de forma reproducible sin romper presupuesto móvil.

## 5. Métricas

### Frecuencia de pulso

- MAE y RMSE en BPM.
- Sesgo y límites de acuerdo Bland–Altman.
- Porcentaje dentro de ±5 BPM y ±10 BPM.

### Clasificación

- Sensibilidad por clase, especificidad, macro-F1 y balanced accuracy.
- AUROC/AUPRC one-vs-rest.
- Matriz de confusión por sujeto.
- Intervalos de confianza bootstrap agrupados por sujeto.

### Calidad/rechazo

- Sensibilidad para detectar mediciones inválidas.
- False-accept rate de señal mala: métrica de seguridad primaria.
- Tasa de mediciones válidas al primer intento.
- Tiempo hasta medición válida.

### Calibración

- Brier score.
- Expected Calibration Error.
- Curva de confiabilidad.
- Temperature scaling aprendido solo en validation.

### Equidad/robustez

Reportar por:

- tono de piel medido con escala/protocolo definido;
- sexo/edad cuando sea éticamente apropiado;
- modelo de teléfono y nivel Camera2;
- mano/dedo;
- movimiento, frío, luz ambiente y batería;
- condición fisiológica.

## 6. Pruebas de estrés

- Mano temblando y teléfono vibrando.
- Flash parcialmente cubierto.
- Presión baja/alta.
- Dedo frío y perfusión reducida.
- 15, 24 y 30 FPS con jitter y pérdida de cuadros.
- Cambio de exposición durante la captura.
- Interrupción por llamada, background o permiso revocado.
- Thermal throttling y batería baja.

## 7. Equivalencia móvil

Para 1000 ventanas bloqueadas comparar Python vs Android:

- señal preprocesada: error máximo absoluto acordado;
- rasgos: tolerancia por rasgo;
- logits FP32: tolerancia numérica;
- clases INT8: acuerdo >=99.5 %, investigando cada discordancia;
- medir latencia p50/p95, RAM pico y energía.

## 8. Gates de liberación propuestos

No son afirmaciones clínicas; son criterios internos que deben ajustarse con expertos:

- Cero fugas de sujeto auditadas.
- False-accept de señales claramente inválidas <1 % en test de estrés.
- MAE de pulso <=5 BPM en cohorte objetivo y sin subgrupo con degradación grave.
- Sensibilidad de observaciones fisiológicas previamente acordada >=90 %, con IC reportado.
- ECE <=0.05 después de calibración.
- Caída macro-F1 INT8 vs FP32 <1 punto porcentual.
- APK/modelo dentro del presupuesto y p95 de inferencia <25 ms en dispositivo mínimo.
- Validación externa terminada antes de habilitar decisiones basadas en IA.

Si un gate falla, se conserva el baseline o se muestra solo pulso + calidad.

## 9. Gobierno de modelos

Cada release debe incluir:

```text
model_version
preprocessor_version
training_data_manifest_hash
code_commit
input/output schema
metrics and subgroup report
calibration parameters
tflite sha256
approval status
rollback version
```

Estados: `research`, `shadow`, `approved`, `revoked`. Solo `approved` puede influir en la observación mostrada.
