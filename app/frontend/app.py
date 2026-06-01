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
        "stop_initiated": False,
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
    color_choice: str,
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
            color_palette=(None if color_choice == "Default" else color_choice),
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
        st.session_state.stop_initiated = False
        st.session_state.thread = None


def _start_generation(
    user_text: str,
    detected_language: str,
    scenes: list[dict],
    style_choice: str,
    color_choice: str,
) -> None:
    st.session_state.running = True
    st.session_state.stop_requested = False
    st.session_state.stop_initiated = False
    st.session_state.video_path = ""
    st.session_state.error = ""
    st.session_state.progress_message = "Preparing generation..."

    thread = Thread(
        target=_generation_worker,
        args=(user_text, detected_language, scenes, style_choice, color_choice),
        daemon=True,
    )
    st.session_state.thread = thread
    thread.start()


_init_session_state()

# Palette color definitions for preview - vibrant kid-friendly colors
PALETTE_COLORS = {
    "Default": "#6C757D",
    "Warm": "#FF6B35",      # Vibrant orange-red
    "Cool": "#00A8FF",      # Bright sky blue
    "Pastel": "#FF69B4",    # Hot pink (playful)
    "Vibrant": "#FF00FF",   # Magenta (super vibrant)
    "Monochrome": "#1A1A1A",
}

# Emoji indicators for palette themes
PALETTE_EMOJIS = {
    "Default": "🎨",
    "Warm": "🔥",
    "Cool": "❄️",
    "Pastel": "🌸",
    "Vibrant": "⚡",
    "Monochrome": "⬛",
}

with st.form(key="script_form"):
    user_text = st.text_area("Enter your story or song lyrics", height=250)
    language_choice = st.selectbox("Language", ["Auto", "EN", "HI", "MR"])
    style_choice = st.selectbox("Visual Style", ["cartoon/kids", "realistic"])
    color_choice = st.selectbox(
        "Color Palette",
        ["Default", "Warm", "Cool", "Pastel", "Vibrant", "Monochrome"],
    )

    # Display palette preview with emoji and swatch
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**{PALETTE_EMOJIS[color_choice]} Selected Palette:** {color_choice}")
    with col2:
        palette_html = f'<div style="background-color: {PALETTE_COLORS[color_choice]}; width: 100%; height: 35px; border-radius: 8px; border: 3px solid #333; box-shadow: 0 2px 8px rgba(0,0,0,0.2);"></div>'
        st.markdown(palette_html, unsafe_allow_html=True)

    st.markdown("---")
    submit_button = st.form_submit_button("Generate Video", type="primary")

if submit_button and not st.session_state.running:
    if not user_text.strip():
        st.error("Please enter some text before generating a video.")
    else:
        effective_language = language_choice if language_choice != "Auto" else None
        detected_language = detect_language(user_text, effective_language)
        scenes = split_into_scenes(user_text, detected_language)
        _start_generation(user_text, detected_language, scenes, style_choice, color_choice)

if st.session_state.error:
    st.error(st.session_state.error)

if st.session_state.running:
    # Progress display with visual indicators
    st.warning("⏳ **Generation in progress...**")
    progress_container = st.container()
    with progress_container:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.markdown(f"**📍 Status:** {st.session_state.progress_message or 'Starting...'}")
        with col2:
            if st.button("🛑 Stop", key="stop_btn"):
                st.session_state.stop_requested = True
                st.session_state.stop_initiated = True
                st.session_state.progress_message = "Stop requested. Canceling generation..."
                st.rerun()

        if st.session_state.stop_initiated:
            st.warning("🛑 Stop requested. Waiting for the pipeline to cancel...")

        # Animated progress bar
        progress_bar = st.progress(0.3)
        st.caption("🎬 Each step can be interrupted now with step-level cancellation")

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
