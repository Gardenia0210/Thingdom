"""Convert a local recording to text with DashScope."""

import os
import subprocess
from http import HTTPStatus
from pathlib import Path
from tempfile import TemporaryDirectory


def transcribe(recording, model="paraformer-realtime-v2"):
    import dashscope
    from dashscope.audio.asr import Recognition

    endpoint = os.getenv("DASHSCOPE_WEBSOCKET_URL")
    if endpoint:
        dashscope.base_websocket_api_url = endpoint
    with TemporaryDirectory() as directory:
        wav = Path(directory) / "speech.wav"
        subprocess.run(
            ["sox", str(recording), "-r", "16000", "-c", "1", "-b", "16", str(wav)],
            check=True, timeout=30,
        )
        recognition = Recognition(model=model, format="wav", sample_rate=16000,
                                  language_hints=["en", "zh"], callback=None)
        result = recognition.call(str(wav))
    if result.status_code != HTTPStatus.OK:
        raise RuntimeError(f"Speech recognition failed: {result.message}")
    return " ".join(sentence["text"].strip() for sentence in (result.get_sentence() or [])
                    if sentence.get("text", "").strip())
