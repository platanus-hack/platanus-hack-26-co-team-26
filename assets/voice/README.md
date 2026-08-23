# assets/voice — paquete de voz offline (generado)

Los `.mp3` de esta carpeta **no están commiteados** (ver `.gitignore`) —
son binarios generados por `tools/voice_pack/generate_voice_pack.py` a partir
de `tools/voice_pack/catalog.py`. Para regenerarlos localmente:

```bash
export ELEVENLABS_API_KEY="tu-key"
export ELEVENLABS_VOICE_ID="voice-id"
python3 tools/voice_pack/generate_voice_pack.py
```

Ver `docs/voice/VOICE-GUIDANCE.md` para el diseño completo (por qué es
offline, los 3 casos, los guiones, y cómo se conecta con
`VoiceGuidanceSelector` en Kotlin).

Estructura esperada tras generar (`es/` = locale):

```
assets/voice/es/rescuer_instructions.mp3
assets/voice/es/trapped_calm.mp3
assets/voice/es/trapped_actionable.mp3
assets/voice/es/manifest.json   # sha256 de cada archivo — sí se commitea
                                  # cuando el equipo fije la versión de release
```
