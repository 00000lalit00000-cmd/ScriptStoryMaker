import os
from pathlib import Path
from typing import Optional

try:
    from TTS.api import TTS
except ImportError:
    TTS = None

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None

MODEL_MAP = {
    "en": "tts_models/en/ljspeech/tacotron2-DDC",
    "hi": "tts_models/multilingual/multi-dataset/your_tts",
    "mr": "tts_models/multilingual/multi-dataset/your_tts",
}


def _select_model(language: str) -> str:
    return MODEL_MAP.get(language, MODEL_MAP["en"])


def generate_voice(text: str, language: str, output_dir: Path) -> Path:
    """Generate multilingual voiceover and save as WAV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / f"voice_{language}.wav"

    if TTS is not None:
        model_name = _select_model(language)
        tts = TTS(model_name=model_name, progress_bar=False, gpu=False)
        tts.tts_to_file(text=text, file_path=str(audio_path))
        return audio_path

    if pyttsx3 is not None:
        engine = pyttsx3.init()
        engine.save_to_file(text, str(audio_path))
        engine.runAndWait()
        return audio_path

    raise RuntimeError("No TTS backend is available. Install 'TTS' or 'pyttsx3'.")
