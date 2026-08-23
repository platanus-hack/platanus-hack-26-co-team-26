# Agent instructions

- Read `PROJECT_CONTEXT.md` and `DESIGN.md` before Android or UI changes.
- Inspect existing module boundaries and dependency versions before adding libraries.
- Keep hardware behind interfaces with fake implementations for previews/tests.
- Never commit or push automatically; never read or use credential files.
- Keep location, physiological, and authentication data private by default.
- Never make medical conclusions from motion or PPG estimates.
- Run focused tests, lint, and the available build command after each slice.

