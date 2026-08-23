# Instrucciones para agentes de HELIUS

- Read `PROJECT_CONTEXT.md` and `DESIGN.md` before Android or UI changes.
- Inspect existing module boundaries and dependency versions before adding libraries.
- Keep hardware behind interfaces with fake implementations for previews/tests.
- Never commit or push automatically; never read or use credential files.
- Keep location, physiological, and authentication data private by default.
- Never make medical conclusions from motion or PPG estimates.
- Run focused tests, lint, and the available build command after each slice. For
  local builds use `gradlew.bat -g C:\Users\Admin\.gradle` when the workspace
  cache is incomplete.
- El paquete es `co.helius` en todo el proyecto (rebrand completado, ver commit `249a062`) — cualquier `co.sismomesh` que aparezca (código nuevo, merges de otras ramas) es residuo pre-rebrand, renómbralo, no lo preserves.
- No presentes una simulación como una alerta real ni infieras vida a partir del movimiento.
- Separa siempre API backend, transporte Nearby/BLE y DTN/store-and-forward; una
  entrega local no es un ACK ni una confirmación de rescate.
- Usa “Evaluación fisiológica” en UI; nunca “triage” ni diagnósticos clínicos.
- No integres en `main` ni `backup/pre-reset-main` y no hagas push automático.

