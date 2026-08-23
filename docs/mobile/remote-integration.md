# Remote implementation context

Before this local foundation work, GitHub had two relevant branches:

- `origin/develop` at the fetched `af0d0f0`, including commit `753ed8d` with the CameraX/AIB PPG engine and DSP package.
- `origin/feat/motion-alert-evidence` at `f19c8f7`, including the deliberate-motion classifier, accelerometer/gyroscope adapter, and tests.

The current working tree keeps its own frontend shell and typed CameraX/PPG seam so it remains reviewable without silently overwriting those branches. Integrating the complete remote engines should be done as a focused merge/cherry-pick by a user with write access to `.git`, followed by adapting `MobileShell` to `CameraXPpgEngine` and `MotionPort` rather than keeping duplicate acquisition paths.

No GitHub credentials were read or used. `origin` was fetched read-only; no commit, push, or merge was completed in this session.
