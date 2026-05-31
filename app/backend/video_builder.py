import contextlib
import subprocess
import wave
from pathlib import Path
from typing import List

FRAME_RATE = 25
WIDTH = 1080
HEIGHT = 1920


def _get_font_option() -> str:
    common_windows = Path("C:/Windows/Fonts/arial.ttf")
    if common_windows.exists():
        return f"fontfile={common_windows.as_posix()}"
    return "font=Arial"


def _escape_text(text: str) -> str:
    escaped = text.replace("%", "%%").replace("'", "\\'").replace(":", "\\:")
    return escaped


def _get_audio_duration(audio_path: Path) -> float:
    with contextlib.closing(wave.open(str(audio_path), "r")) as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def _create_scene_clip(image_path: Path, scene_text: str, duration: int, output_path: Path) -> None:
    font_option = _get_font_option()
    escaped_text = _escape_text(scene_text)
    filter_parts = [
        f"scale={WIDTH}:{HEIGHT}",
        f"zoompan=z='min(zoom+0.0008,1.1)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={int(duration * FRAME_RATE)}",
        f"fps={FRAME_RATE}",
        f"drawtext={font_option}:text='{escaped_text}':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=h-220"
    ]
    filter_chain = ",".join(filter_parts)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-t",
            str(duration),
            "-vf",
            filter_chain,
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        check=True,
    )


def _concat_clips(clips: List[Path], output_path: Path) -> None:
    list_file = output_path.parent / "concat_list.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for clip in clips:
            f.write(f"file '{clip.as_posix()}'\n")
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-c",
            "copy",
            str(output_path),
        ],
        check=True,
    )


def build_vertical_video(
    image_paths: List[Path], scenes: List[dict], audio_path: Path, output_dir: Path, style: str = "realistic"
) -> Path:
    """Build a final vertical MP4 from scene images and voiceover audio."""
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_clips: List[Path] = []
    for scene, image_path in zip(scenes, image_paths):
        clip_path = output_dir / f"scene_{scene['id']:02d}.mp4"
        _create_scene_clip(image_path, scene["text"], scene["duration"], clip_path)
        scene_clips.append(clip_path)

    raw_video_path = output_dir / "raw_video.mp4"
    _concat_clips(scene_clips, raw_video_path)

    final_video_path = output_dir / "final_output.mp4"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(raw_video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(final_video_path),
        ],
        check=True,
    )

    return final_video_path
