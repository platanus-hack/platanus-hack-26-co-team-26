# Model directory

Production layout:

```text
models/<version>/ppg_tiny_tcn_int8.tflite
models/<version>/APPROVED
```

`APPROVED` must be created only by the model-governance release process after
all validation gates in `docs/ppg/VALIDATION.md` pass. Never approve merely
because export succeeded — ver `docs/ppg/TEST_AND_RELEASE_MATRIX.md`.
