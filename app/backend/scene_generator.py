import re
from typing import Dict, List, Optional

from langdetect import detect
from langdetect.lang_detect_exception import LangDetectException

SCENE_MIN = 4
SCENE_MAX = 8


def detect_language(text: str, override: Optional[str] = None) -> str:
    """Detect English, Hindi, or Marathi language from the input text."""
    if override:
        normalized = override.strip().lower()
        if normalized in {"en", "hi", "mr"}:
            return normalized

    devanagari = re.search(r"[\u0900-\u097F]", text)
    if not devanagari:
        try:
            detected = detect(text)
            if detected.startswith("en"):
                return "en"
        except LangDetectException:
            pass
        return "en"

    marathi_markers = ["आहे", "मला", "तू", "मी", "आपण", "किंवा", "असल्यास"]
    if any(marker in text for marker in marathi_markers):
        return "mr"
    return "hi"


def _normalize_text(text: str) -> str:
    text = text.replace("\n", " ").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def split_into_scenes(text: str, language: str) -> List[Dict[str, str]]:
    """Split the input text into 4-8 scene descriptions."""
    normalized = _normalize_text(text)
    if not normalized:
        return []

    sentences = re.split(r"(?<=[.!?])\s+", normalized)
    if len(sentences) < SCENE_MIN:
        words = normalized.split()
        approx = max(1, len(words) // SCENE_MIN)
        sentences = [" ".join(words[i : i + approx]) for i in range(0, len(words), approx)]

    scenes = []
    for idx, sentence in enumerate(sentences[:SCENE_MAX]):
        scenes.append(
            {
                "id": idx + 1,
                "text": sentence.strip(),
                "duration": max(3, min(5, len(sentence.split()) // 3 + 2)),
            }
        )

    if len(scenes) < SCENE_MIN:
        joined = " ".join(scene["text"] for scene in scenes)
        scenes = []
        words = joined.split()
        chunk_size = max(1, len(words) // SCENE_MIN)
        for idx in range(SCENE_MIN):
            start = idx * chunk_size
            end = start + chunk_size if idx < SCENE_MIN - 1 else len(words)
            scenes.append(
                {
                    "id": idx + 1,
                    "text": " ".join(words[start:end]).strip(),
                    "duration": 4,
                }
            )

    return scenes
