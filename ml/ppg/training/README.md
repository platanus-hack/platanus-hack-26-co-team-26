# ml/ppg/training

Paquete Python de entrenamiento integrado desde el blueprint de Laura (ver
`docs/ppg/README.md`). Arquitectura Tiny-TCN (<100k parámetros) con exportación
a LiteRT INT8, más un modelo teacher–student para `estimated_ecg`
(`ecg_student_model.py`).

```
src/model.py              build_tiny_tcn() — clasificador de patrón fisiológico
src/ecg_student_model.py  modelo student para reconstrucción PPG→ECG estimado
src/preprocess.py         ventanas deterministas (equivalencia numérica con Kotlin)
src/split_subjects.py     split por sujeto (GroupShuffleSplit) — nunca por muestra
src/train.py              entrenamiento
src/evaluate.py           métricas balanceadas por subgrupo
src/export_int8.py        cuantización y manifiesto SHA-256 (services/ppg_model_registry)
tests/                    pytest — imports como `from src.model import ...`
```

Correr desde este directorio: `pip install -e .[dev] && pytest`.

No se incluyen pesos entrenados ni datasets (`data/`, `datasets/` en `ml/ppg/`
están en `.gitignore` — ver `docs/ppg/VALIDATION.md` para el protocolo de
recolección con población objetivo y consentimiento).

**Dueño:** Alex.
