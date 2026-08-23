# core/signal

**Propósito:** DSP puro (Kotlin, sin Android) para PPG y evidencia de movimiento —
normalización, detrending, band-pass, FFT/PSD, detección de picos, SQI, features de
acelerómetro (RMS, energía, ZCR, entropía espectral, patrón intencional). Testeable
con grabaciones reproducidas, sin ningún teléfono.

**Puertos relacionados:** `BiomarkerInferencePort`, `MotionPort` (implementaciones
de apoyo — el puerto en sí vive en `core/application/ports`).

**Dueño:** Alex. **Revisor obligatorio:** Laura (integración con `:android:ppg`).

**Etiqueta de madurez:** `ENGINEERING` (frecuencia de pulso) / `EXPERIMENTAL` (PRV,
respiración, perfusión) — ver `docs/architecture/OVERVIEW.md` § AIB y el estado del
arte de PPG en el `README.md` raíz.
