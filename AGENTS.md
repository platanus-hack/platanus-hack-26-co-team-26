# Instrucciones para agentes de HELIOS

- Read `PROJECT_CONTEXT.md` and `DESIGN.md` before Android or UI changes.
- Inspect existing module boundaries and dependency versions before adding libraries.
- Keep hardware behind interfaces with fake implementations for previews/tests.
- Never commit or push automatically; never read or use credential files.
- Keep location, physiological, and authentication data private by default.
- Never make medical conclusions from motion or PPG estimates.
- Run focused tests, lint, and the available build command after each slice.
- No renombres `co.sismomesh` u otros paquetes técnicos solo por cambiar la marca visible.
- No presentes una simulación como una alerta real ni infieras vida a partir del movimiento.
- Usa “Evaluación fisiológica” en UI; nunca “triage” ni diagnósticos clínicos.
- No integres en `main` ni `backup/pre-reset-main` y no hagas push automático.

