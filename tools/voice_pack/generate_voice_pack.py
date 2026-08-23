"""Genera el paquete de voz offline llamando una sola vez a la API de
ElevenLabs (text-to-speech) por cada entrada de catalog.py.

Este script se corre en desarrollo, NO en el teléfono — la app nunca llama a
ElevenLabs en tiempo real (ver docs/voice/VOICE-GUIDANCE.md § "Por qué esto
NO es una llamada en vivo a la API"). La salida son archivos .mp3 estáticos
que se empaquetan como asset de la app.

Uso:
    export ELEVENLABS_API_KEY="..."   # nunca lo pases como argumento de línea
                                        # de comandos, queda en el historial
    export ELEVENLABS_VOICE_ID="..."  # elegido de tu librería de voces
    python3 tools/voice_pack/generate_voice_pack.py --dry-run   # revisa antes
    python3 tools/voice_pack/generate_voice_pack.py             # genera

Requiere: pip install requests (ver requirements.txt de esta carpeta).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from catalog import CATALOG, VoiceEntry

API_BASE = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL_ID = "eleven_multilingual_v2"
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent


def estimate(entries: list[VoiceEntry]) -> None:
    total_chars = 0
    for entry in entries:
        n = len(entry.text)
        total_chars += n
        print(f"  {entry.case_id:24s} {n:5d} caracteres  locale={entry.locale}")
    print(f"\nTotal: {total_chars} caracteres en {len(entries)} guiones.")
    print(
        "Revisa tu cuota mensual del plan Creator en "
        "https://elevenlabs.io/app/subscription antes de generar — este "
        "script no la consulta por ti."
    )


def synthesize(entry: VoiceEntry, voice_id: str, model_id: str, api_key: str) -> bytes:
    import requests

    url = f"{API_BASE}/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": entry.text,
        "model_id": model_id,
        "voice_settings": {
            "stability": entry.voice_settings.stability,
            "similarity_boost": entry.voice_settings.similarity_boost,
            "style": entry.voice_settings.style,
            "use_speaker_boost": entry.voice_settings.use_speaker_boost,
        },
    }
    resp = requests.post(url, headers=headers, json=body, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(
            f"ElevenLabs devolvió {resp.status_code} para '{entry.case_id}': "
            f"{resp.text[:500]}"
        )
    return resp.content


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--voice-id",
        default=os.environ.get("ELEVENLABS_VOICE_ID"),
        help="Voice ID de ElevenLabs (o variable ELEVENLABS_VOICE_ID). Sin default: "
        "es una elección del equipo, no del código.",
    )
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Default: assets/voice/<locale> en la raíz del repo, por locale del catálogo.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Solo muestra qué se generaría y el conteo de caracteres, sin llamar a la API.",
    )
    args = parser.parse_args()

    if args.dry_run:
        print("Catálogo actual (tools/voice_pack/catalog.py):\n")
        estimate(CATALOG)
        return 0

    api_key = os.environ.get("ELEVENLABS_API_KEY")
    if not api_key:
        print(
            "Falta ELEVENLABS_API_KEY en el entorno. No se hardcodea ninguna "
            "key en este repo — expórtala en tu shell antes de correr esto:\n"
            '  export ELEVENLABS_API_KEY="tu-key"',
            file=sys.stderr,
        )
        return 1
    if not args.voice_id:
        print(
            "Falta --voice-id (o ELEVENLABS_VOICE_ID). Elige una voz de tu "
            "librería en https://elevenlabs.io/app/voice-library — ver "
            "docs/voice/VOICE-GUIDANCE.md para criterios sugeridos por caso.",
            file=sys.stderr,
        )
        return 1

    by_locale: dict[str, list[VoiceEntry]] = {}
    for entry in CATALOG:
        by_locale.setdefault(entry.locale, []).append(entry)

    manifest_entries = []
    for locale, entries in by_locale.items():
        out_dir = Path(args.out_dir) if args.out_dir else REPO_ROOT / "assets" / "voice" / locale
        out_dir.mkdir(parents=True, exist_ok=True)

        for entry in entries:
            print(f"Generando '{entry.case_id}' ({locale})...")
            audio = synthesize(entry, args.voice_id, args.model_id, api_key)
            out_path = out_dir / f"{entry.case_id}.mp3"
            out_path.write_bytes(audio)
            sha256 = hashlib.sha256(audio).hexdigest()
            manifest_entries.append(
                {
                    "case_id": entry.case_id,
                    "locale": locale,
                    "file": out_path.name,
                    "sha256": sha256,
                    "bytes": len(audio),
                    "chars": len(entry.text),
                    "voice_id": args.voice_id,
                    "model_id": args.model_id,
                }
            )
            print(f"  -> {out_path} ({len(audio)} bytes, sha256={sha256[:12]}...)")

        manifest = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "locale": locale,
            "entries": [m for m in manifest_entries if m["locale"] == locale],
        }
        manifest_path = out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")
        print(f"Manifest: {manifest_path}")

    print(
        "\nListo. La app debe verificar el sha256 de cada archivo contra "
        "manifest.json antes de confiar en el paquete embebido (integridad "
        "en modo avión) — ver docs/voice/VOICE-GUIDANCE.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
