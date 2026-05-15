from __future__ import annotations

import contextlib
import subprocess
import tempfile
import wave
from pathlib import Path

from app.providers.tts.base import TTSProvider
from app.providers.tts.schemas import TTSResult


class EspeakTTSProvider(TTSProvider):
    provider_name = "espeak-ng"

    def synthesize(self, text: str, voice_settings: dict | None = None) -> TTSResult:
        settings = voice_settings or {}
        voice_name = settings.get("voice_name") or "ru"
        speed = str(settings.get("speed") or "155")
        with tempfile.TemporaryDirectory(prefix="kunzhutik-tts-") as tmp_dir_name:
            output_path = Path(tmp_dir_name) / "voice.wav"
            subprocess.run(
                [
                    "espeak-ng",
                    "-v",
                    voice_name,
                    "-s",
                    speed,
                    "-w",
                    str(output_path),
                    text,
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=20,
            )
            audio_bytes = output_path.read_bytes()
            duration = _read_wav_duration_seconds(output_path)
        return TTSResult(
            audio_bytes=audio_bytes,
            mime_type="audio/wav",
            duration_sec=duration,
            provider=self.provider_name,
            voice_id=voice_name,
            raw_response={"provider": self.provider_name, "voice_name": voice_name, "speed": speed},
        )


def _read_wav_duration_seconds(file_path: Path) -> float:
    with contextlib.closing(wave.open(str(file_path), "rb")) as wav_file:
        frame_count = wav_file.getnframes()
        sample_rate = wav_file.getframerate()
    if not sample_rate:
        return 0.0
    return round(frame_count / sample_rate, 2)
