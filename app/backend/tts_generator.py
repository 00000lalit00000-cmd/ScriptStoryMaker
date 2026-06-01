import os
import multiprocessing
import threading
import time
from pathlib import Path
from typing import Callable, Optional

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


def generate_voice(
    text: str,
    language: str,
    output_dir: Path,
    stop_callback: Optional[Callable[[], bool]] = None,
) -> Path:
    """Generate multilingual voiceover and save as WAV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    audio_path = output_dir / f"voice_{language}.wav"

    if stop_callback is not None and stop_callback():
        raise RuntimeError("Stopped by user.")

    if pyttsx3 is not None:
        engine = pyttsx3.init()
        stop_event = threading.Event()

        def run_engine() -> None:
            engine.save_to_file(text, str(audio_path))
            engine.runAndWait()
            stop_event.set()

        worker = threading.Thread(target=run_engine, daemon=True)
        worker.start()

        while worker.is_alive():
            if stop_callback is not None and stop_callback():
                engine.stop()
                worker.join(timeout=5)
                raise RuntimeError("Stopped by user.")
            time.sleep(0.1)

        return audio_path

    if TTS is not None:
        model_name = _select_model(language)

        def run_tts_model(model_name: str, text: str, output_path: str) -> None:
            tts = TTS(model_name=model_name, progress_bar=False, gpu=False)
            tts.tts_to_file(text=text, file_path=output_path)

        process = multiprocessing.Process(
            target=run_tts_model,
            args=(model_name, text, str(audio_path)),
            daemon=True,
        )
        process.start()

        try:
            while process.is_alive():
                if stop_callback is not None and stop_callback():
                    process.terminate()
                    process.join(timeout=5)
                    raise RuntimeError("Stopped by user.")
                time.sleep(0.1)
        finally:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)

        if process.exitcode != 0:
            raise RuntimeError("TTS generation failed.")

        return audio_path

    raise RuntimeError("No TTS backend is available. Install 'TTS' or 'pyttsx3'.")
