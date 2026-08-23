# Evaluación fisiológica / PPG

**Estado: PARCIAL + DEMO local.** `:android:ppg` tiene adquisición CameraX, flash, muestreo RGB, control de sesión y una implementación avanzada `CameraXPpgEngine`. El pipeline local de respaldo en `co.helius.core.signal.ppg.PpgPipeline` aplica detrend, DFT con ventana, calidad de señal y dos pasadas.

Una lectura baja o anómala solicita una segunda verificación. Si se repite, se presenta como patrón observado, no como bradicardia confirmada ni diagnóstico. ECG estimado y modelos LiteRT no deben mostrarse como producción.

