# tools/voice_pack

Genera el paquete de audio offline (`assets/voice/`) a partir de `catalog.py`
usando la API de ElevenLabs (text-to-speech). Se corre una vez en desarrollo
— la app nunca llama a esta API en tiempo real, ver
`docs/voice/VOICE-GUIDANCE.md`.

**Dueño:** Helmut.

## Requisitos

- Cuenta de ElevenLabs con API key (plan Creator o superior — el catálogo
  actual son 3 guiones de ~100-150 palabras cada uno, muy por debajo de la
  cuota mensual del plan Creator).
- `pip install -r requirements.txt`

## Uso

```bash
export ELEVENLABS_API_KEY="tu-key"        # nunca la pegues en el chat ni la commitees
export ELEVENLABS_VOICE_ID="voice-id"     # elige una voz en elevenlabs.io/app/voice-library

# 1. Revisa qué se va a generar y cuántos caracteres consume, sin llamar la API:
python3 generate_voice_pack.py --dry-run

# 2. Genera de verdad:
python3 generate_voice_pack.py
```

Salida: `assets/voice/es/{rescuer_instructions,trapped_calm,trapped_actionable}.mp3`
más `assets/voice/es/manifest.json` (sha256 + metadata de cada archivo, para
que la app valide integridad del paquete embebido antes de confiar en él).

## Cómo agregar o editar un guion

Editar `catalog.py` — es la única fuente de verdad, no editar los `.mp3` a
mano. Cada `case_id` nuevo debe:

1. Agregarse aquí en `catalog.py`.
2. Tener su contraparte en `VoiceGuidanceCase`
   (`core/src/commonMain/kotlin/co/helius/core/domain/voice/VoiceGuidance.kt`)
   con el mismo string exacto en `assetId`.
3. Pasar la revisión de vocabulario de `docs/glossary.md` (nada de promesas
   de rescate, nada de lenguaje clínico).
4. Volver a correr este script para regenerar el `.mp3` correspondiente.

## Por qué no está commiteado el `.mp3` generado

El audio es un binario grande derivado de `catalog.py` — igual que el código
generado de `protocol/`, se regenera, no se edita a mano, pero a diferencia
de ese código sí es razonable no versionarlo en git (peso, y cada
regeneración con la misma voz produce bytes distintos aunque el texto no
cambie). Lo que sí importa versionar es `catalog.py` (la fuente) y, una vez
generado, el `manifest.json` con los checksums de la versión que el equipo
decidió empaquetar en el release — commitéalo aparte cuando tengan el
paquete final.
