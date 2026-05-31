import os
from pathlib import Path
from typing import List

import torch
from diffusers import StableDiffusionPipeline

MODEL_NAME = "runwayml/stable-diffusion-v1-5"
MODEL_PATH_ENV = "SD_MODEL_PATH"


def _get_pipeline() -> StableDiffusionPipeline:
    model_path = os.environ.get(MODEL_PATH_ENV)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if model_path:
        return StableDiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float32, safety_checker=None).to(device)
    return StableDiffusionPipeline.from_pretrained(MODEL_NAME, torch_dtype=torch.float32, safety_checker=None).to(device)


def _scene_prompt(scene_text: str, style: str) -> str:
    base = f"{scene_text}, portrait orientation, dramatic lighting, cinematic composition"
    if style == "cartoon/kids":
        return f"{base}, colorful cartoon illustration, kid-friendly, playful characters"
    return f"{base}, photorealistic detail, realistic style, high resolution"


def generate_images(scenes: List[dict], style: str, output_dir: Path) -> List[Path]:
    """Generate one image per scene using Stable Diffusion."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pipe = _get_pipeline()
    image_paths = []

    for scene in scenes:
        prompt = _scene_prompt(scene["text"], style)
        filename = f"scene_{scene['id']:02d}.png"
        output_path = output_dir / filename
        result = pipe(prompt, height=1280, width=768, guidance_scale=7.5, num_inference_steps=25)
        image = result.images[0]
        image.save(output_path)
        image_paths.append(output_path)

    return image_paths
