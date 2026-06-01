import sys
from pathlib import Path
from threading import Thread
from typing import Callable

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from backend.image_generator import generate_images
from backend.scene_generator import detect_language, split_into_scenes
from backend.tts_generator import generate_voice
from backend.video_builder import build_vertical_video

OUTPUT_DIR = ROOT_DIR / "outputs"
IMAGE_DIR = OUTPUT_DIR / "images"
AUDIO_DIR = OUTPUT_DIR / "audio"
VIDEO_DIR = OUTPUT_DIR / "video"

st.set_page_config(page_title="ScriptStoryMaker", layout="centered")
st.title("ScriptStoryMaker")
st.markdown("Convert stories or song lyrics into a short vertical video (9:16).")


def _init_session_state() -> None:
    defaults = {
        "running": False,
        "stop_requested": False,
        "video_path": "",
        "error": "",
        "progress_message": "",
        "thread": None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def _stop_requested() -> bool:
    return st.session_state.get("stop_requested", False)


def _update_progress(message: str) -> None:
    st.session_state.progress_message = message


def _generation_worker(
    user_text: str,
    detected_language: str,
    scenes: list[dict],
    style_choice: str,
) -> None:
    try:
        if _stop_requested():
            raise RuntimeError("Stopped by user.")

        IMAGE_DIR.mkdir(parents=True, exist_ok=True)
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        VIDEO_DIR.mkdir(parents=True, exist_ok=True)

        _update_progress("Generating images for each scene...")
        image_paths = generate_images(
            scenes,
            style_choice,
            IMAGE_DIR,
            stop_callback=_stop_requested,
        )

        if _stop_requested():
            raise RuntimeError("Stopped by user.")

        _update_progress("Generating voiceover...")
        audio_path = generate_voice(
            user_text,
            detected_language,
            AUDIO_DIR,
            stop_callback=_stop_requested,
        )

        if _stop_requested():
            raise RuntimeError("Stopped by user.")

        _update_progress("Building final video with FFmpeg...")
        video_path = build_vertical_video(
            image_paths,
            scenes,
            audio_path,
            VIDEO_DIR,
            style_choice,
            stop_callback=_stop_requested,
        )

        st.session_state.video_path = str(video_path)
        st.session_state.error = ""
        _update_progress("")
    except Exception as exc:
        message = str(exc)
        if "Stopped by user" in message:
            st.session_state.error = "Generation stopped by user."
        else:
            st.session_state.error = f"Pipeline failed: {message}"
        st.session_state.video_path = ""
    finally:
        st.session_state.running = False
        st.session_state.stop_requested = False
        st.session_state.thread = None


def _start_generation(
    user_text: str,
    detected_language: str,
    scenes: list[dict],
    style_choice: str,
) -> None:
    st.session_state.running = True
    st.session_state.stop_requested = False
    st.session_state.video_path = ""
    st.session_state.error = ""
    st.session_state.progress_message = "Preparing generation..."

    thread = Thread(
        target=_generation_worker,
        args=(user_text, detected_language, scenes, style_choice),
        daemon=True,
    )
    st.session_state.thread = thread
    thread.start()


_init_session_state()

with st.form(key="script_form"):
    user_text = st.text_area("Enter your story or song lyrics", height=250)
    language_choice = st.selectbox("Language", ["Auto", "EN", "HI", "MR"])
    style_choice = st.selectbox("Visual Style", ["cartoon/kids", "realistic"])
    generate_button = st.form_submit_button("Generate Video")

if generate_button and not st.session_state.running:
    if not user_text.strip():
        st.error("Please enter some text before generating a video.")
    else:
        effective_language = language_choice if language_choice != "Auto" else None
        detected_language = detect_language(user_text, effective_language)
        scenes = split_into_scenes(user_text, detected_language)
        _start_generation(user_text, detected_language, scenes, style_choice)
        st.success("Generation started. You can stop it at any time.")

if st.session_state.running:
    st.info(st.session_state.progress_message or "Generation is in progress...")
    if st.button("Stop generation"):
        st.session_state.stop_requested = True
        st.experimental_rerun()

if st.session_state.error:
    st.error(st.session_state.error)

if st.session_state.video_path:
    video_path = Path(st.session_state.video_path)
    if video_path.exists():
        st.success(f"Video created: {video_path.name}")
        with open(video_path, "rb") as f:
            video_bytes = f.read()
            st.video(video_bytes)
            st.download_button(
                label="Download Video",
                data=video_bytes,
                file_name=video_path.name,
                mime="video/mp4",
            )
    else:
        st.warning("Video generation completed, but the output file was not found.")
