import os
from pathlib import Path
from typing import Callable, List, Optional

import torch
from diffusers import StableDiffusionPipeline

MODEL_NAME = "runwayml/stable-diffusion-v1-5"
MODEL_PATH_ENV = "SD_MODEL_PATH"

# Global pipeline cache to avoid reloading
_pipeline_cache = None


def _get_pipeline() -> StableDiffusionPipeline:
    """Load pipeline once and reuse across scenes."""
    global _pipeline_cache
    if _pipeline_cache is not None:
        return _pipeline_cache
    
    model_path = os.environ.get(MODEL_PATH_ENV)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    # Use float16 for faster inference on GPU, float32 on CPU
    dtype = torch.float16 if device == "cuda" else torch.float32
    
    if model_path:
        _pipeline_cache = StableDiffusionPipeline.from_pretrained(
            model_path, 
            torch_dtype=dtype, 
            safety_checker=None
        ).to(device)
    else:
        _pipeline_cache = StableDiffusionPipeline.from_pretrained(
            MODEL_NAME, 
            torch_dtype=dtype, 
            safety_checker=None
        ).to(device)

    if device == "cpu":
        # Reduce memory and improve stability for CPU-only systems.
        try:
            _pipeline_cache.enable_attention_slicing()
        except Exception:
            pass
        try:
            _pipeline_cache.enable_vae_tiling()
        except Exception:
            pass
    
    return _pipeline_cache


def _scene_prompt(scene_text: str, style: str, color_palette: Optional[str] = None) -> str:
    # Core composition and lighting
    base = f"{scene_text}, portrait orientation, dramatic lighting, cinematic composition"

    # Improved facial and body coherence guidance
    if style == "cartoon/kids":
        # Kid-friendly with emphasis on proportioned characters
        body_guidance = "proportioned full body, matching face and body scale, aligned posture, coherent anatomy, playful expression, cheerful demeanor"
        base_prompt = f"{base}, {body_guidance}"
    else:
        # Realistic with anatomical precision
        body_guidance = "proportioned full body, matching face and body scale, aligned posture, coherent anatomy, natural proportions, detailed face"
        base_prompt = f"{base}, {body_guidance}"

    # Color palette override from UI
    if color_palette:
        cp = color_palette.lower()
        if cp == "warm":
            color_hint = "warm color palette, golden highlights, warm skin tones"
        elif cp == "cool":
            color_hint = "cool blue-green palette, soft cold highlights"
        elif cp == "pastel":
            color_hint = "soft pastel color palette, low saturation, gentle tones"
        elif cp == "vibrant":
            color_hint = "vibrant saturated colors, high contrast, energetic mood"
        elif cp == "monochrome":
            color_hint = "monochrome palette, tonal contrast, single-hue styling"
        else:
            color_hint = "balanced natural palette"
    else:
        # Color scheme hints by style
        if style == "cartoon/kids":
            color_hint = "bright vibrant colors, saturated rainbow palette, cheerful tones, playful color blocking"
            return f"{base_prompt}, {color_hint}, colorful cartoon illustration, kid-friendly, playful whimsical style, high energy, fun adventure"
        else:
            # realistic
            color_hint = "muted natural tones, warm highlights, realistic skin tones"

    return f"{base_prompt}, {color_hint}, photorealistic detail, realistic style, high resolution"


def generate_images(
    scenes: List[dict],
    style: str,
    output_dir: Path,
    stop_callback: Optional[Callable[[], bool]] = None,
    color_palette: Optional[str] = None,
) -> List[Path]:
    """Generate one image per scene using Stable Diffusion with optimized settings."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pipe = _get_pipeline()
    image_paths = []

    for scene in scenes:
        if stop_callback is not None and stop_callback():
            raise RuntimeError("Stopped by user.")

        prompt = _scene_prompt(scene["text"], style, color_palette=color_palette)
        filename = f"scene_{scene['id']:02d}.png"
        output_path = output_dir / filename
        
        # Use a concise negative prompt to avoid artifacts without exceeding token limits
        negative_prompt = (
            "deformed, blurry, low-res, watermark, text, extra limbs, worst quality, "
            "jpeg artifacts, cropped, mismatched body parts, anatomical errors, "
            "disconnected limbs, inconsistent proportions"
        )

        # Tweak guidance and steps: more steps for realistic portraits
        if style == "realistic":
            guidance = 8.5
            steps = 20 if pipe.device.type == "cpu" else 25
            height, width = 896, 512
        else:
            guidance = 7.5
            steps = 16
            height, width = 960, 576

        # Create a step-level callback for cancellation during inference
        def step_callback(step, timestep, latents):
            if stop_callback is not None and stop_callback():
                raise RuntimeError("Stopped by user.")

        result = pipe(
            prompt,
            height=height,
            width=width,
            guidance_scale=guidance,
            num_inference_steps=steps,
            negative_prompt=negative_prompt,
            callback=step_callback,
            callback_steps=1,  # Call callback at every step
        )
        image = result.images[0]
        image.save(output_path)
        image_paths.append(output_path)

    return image_paths
