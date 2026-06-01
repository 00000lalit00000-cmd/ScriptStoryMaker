# ScriptStoryMaker

Lightweight local-first app to convert story scripts or song lyrics into short vertical videos (1080x1920, 9:16).

## Structure

- `prompts/`: reusable prompt definitions for frontend, backend, and full-app generation.
- `app/frontend/app.py`: Streamlit UI.
- `app/backend/scene_generator.py`: text scene splitting and language detection.
- `app/backend/image_generator.py`: Stable Diffusion image generation.
- `app/backend/tts_generator.py`: Coqui TTS voice generation.
- `app/backend/video_builder.py`: FFmpeg video assembly.
- `app/main.py`: launcher for the Streamlit frontend.
- `app/outputs/`: generated images, audio, and videos.

## Setup

1. Install Python 3.11 or 3.12 for the most compatible experience.
2. Install FFmpeg and add it to your system `PATH`.
3. Create a virtual environment and install dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -U pip wheel
pip install -r requirements.txt
```

4. (Optional) Set a local Stable Diffusion model path if you have downloaded weights:

```powershell
$env:SD_MODEL_PATH = 'C:\path\to\stable-diffusion-model'
```

5. If you do not set `SD_MODEL_PATH`, the app will download `runwayml/stable-diffusion-v1-5` from Hugging Face when first run.

6. If you are using Python 3.14, note that the `TTS` package may not install; the app will still fall back to `pyttsx3` for voice output.

## Run

```bash
python app/main.py
```

Then open the Streamlit URL shown in the terminal.

## Notes

- The first run may download TTS models and Stable Diffusion weights.
- For Marathi/Hindi voice, Coqui multilingual models are used when available.
- Output files are saved to `app/outputs/`.

## Performance Optimizations

The app has been optimized for speed:

1. **Image Generation**:
   - Reduced inference steps from 25 → 15 (~40% faster)
   - Reduced resolution from 1280x768 → 960x576 for faster processing
   - Uses float16 precision on GPU (float32 on CPU)
   - Pipeline model is cached across scenes to avoid reloading

2. **Video Encoding**:
   - FFmpeg uses `ultrafast` preset instead of default (much faster)
   - Reduced quality setting (CRF 28 vs 23) for acceptable quality with faster encoding
   - Removed Ken Burns zoom/pan effect (complex filter = slow)
   - Simplified to scale + text overlay only
   - Output is suppressed to reduce I/O overhead

3. **Expected Times** (rough estimates on CPU):
   - 5-scene video: ~2–5 minutes
   - With GPU: ~30–60 seconds

To improve performance further:
- Use a GPU if available (CUDA-capable NVIDIA card)
- Reduce text quality by setting fewer inference steps in `image_generator.py`
- Use a smaller/faster model instead of Stable Diffusion v1.5
