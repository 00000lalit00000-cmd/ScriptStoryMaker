import sys
from pathlib import Path

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

with st.form(key="script_form"):
    user_text = st.text_area("Enter your story or song lyrics", height=250)
    language_choice = st.selectbox("Language", ["Auto", "EN", "HI", "MR"])
    style_choice = st.selectbox("Visual Style", ["cartoon/kids", "realistic"])
    generate_button = st.form_submit_button("Generate Video")

if generate_button:
    if not user_text.strip():
        st.error("Please enter some text before generating a video.")
    else:
        try:
            st.info("Starting pipeline: detecting language and splitting scenes...")
            effective_language = language_choice if language_choice != "Auto" else None
            detected_language = detect_language(user_text, effective_language)
            scenes = split_into_scenes(user_text, detected_language)

            st.info(f"Detected language: {detected_language.upper()}")
            st.info("Generating images for each scene...")
            IMAGE_DIR.mkdir(parents=True, exist_ok=True)
            audio_dir = AUDIO_DIR
            audio_dir.mkdir(parents=True, exist_ok=True)
            VIDEO_DIR.mkdir(parents=True, exist_ok=True)

            image_paths = generate_images(scenes, style_choice, IMAGE_DIR)
            st.success(f"Generated {len(image_paths)} images.")

            st.info("Generating voiceover...")
            audio_path = generate_voice(user_text, detected_language, audio_dir)
            st.success(f"Voice generated at: {audio_path.name}")

            st.info("Building final video with FFmpeg...")
            video_path = build_vertical_video(image_paths, scenes, audio_path, VIDEO_DIR, style_choice)
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

        except Exception as exc:
            st.error(f"Pipeline failed: {exc}")
            raise
