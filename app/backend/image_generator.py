import os
from pathlib import Path
from typing import List

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
    
    return _pipeline_cache


def _scene_prompt(scene_text: str, style: str) -> str:
    base = f"{scene_text}, portrait orientation, dramatic lighting, cinematic composition"
    if style == "cartoon/kids":
        return f"{base}, colorful cartoon illustration, kid-friendly, playful characters"
    return f"{base}, photorealistic detail, realistic style, high resolution"


def generate_images(scenes: List[dict], style: str, output_dir: Path) -> List[Path]:
    """Generate one image per scene using Stable Diffusion with optimized settings."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pipe = _get_pipeline()
    image_paths = []

    for scene in scenes:
        prompt = _scene_prompt(scene["text"], style)
        filename = f"scene_{scene['id']:02d}.png"
        output_path = output_dir / filename
        
        # Reduced inference steps (15 vs 25) for ~40% faster generation
        # Reduced resolution (960x576 vs 1280x768) for faster processing
        result = pipe(
            prompt, 
            height=576, 
            width=960, 
            guidance_scale=7.5, 
            num_inference_steps=15
        )
        image = result.images[0]
        image.save(output_path)
        image_paths.append(output_path)

    return image_paths
