import contextlib
import subprocess
import time
import wave
from pathlib import Path
from typing import Callable, List, Optional

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


def _run_subprocess(args: List[str], stop_callback: Optional[Callable[[], bool]] = None) -> None:
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while True:
        if stop_callback is not None and stop_callback():
            proc.kill()
            proc.wait()
            raise RuntimeError("Stopped by user.")
        status = proc.poll()
        if status is not None:
            if status != 0:
                raise subprocess.CalledProcessError(status, args)
            return
        time.sleep(0.1)


def _create_scene_clip(
    image_path: Path,
    scene_text: str,
    duration: int,
    output_path: Path,
    stop_callback: Optional[Callable[[], bool]] = None,
) -> None:
    font_option = _get_font_option()
    escaped_text = _escape_text(scene_text)
    # Simplified filter chain: reduced resolution scale, removed complex zoompan for speed
    # Use basic scale and text overlay only for faster encoding
    filter_parts = [
        f"scale={WIDTH}:{HEIGHT}",
        f"fps={FRAME_RATE}",
        f"drawtext={font_option}:text='{escaped_text}':fontcolor=white:fontsize=40:box=1:boxcolor=black@0.6:boxborderw=10:x=(w-text_w)/2:y=h-220"
    ]
    filter_chain = ",".join(filter_parts)
    _run_subprocess(
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
            "-preset",
            "ultrafast",  # Fast encoding preset
            "-crf",
            "28",  # Higher CRF = lower quality but faster (default 23)
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        stop_callback=stop_callback,
    )


def _concat_clips(
    clips: List[Path],
    output_path: Path,
    stop_callback: Optional[Callable[[], bool]] = None,
) -> None:
    list_file = output_path.parent / "concat_list.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for clip in clips:
            f.write(f"file '{clip.as_posix()}'\n")
    _run_subprocess(
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
        stop_callback=stop_callback,
    )


def build_vertical_video(
    image_paths: List[Path],
    scenes: List[dict],
    audio_path: Path,
    output_dir: Path,
    style: str = "realistic",
    stop_callback: Optional[Callable[[], bool]] = None,
) -> Path:
    """Build a final vertical MP4 from scene images and voiceover audio."""
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_clips: List[Path] = []
    for scene, image_path in zip(scenes, image_paths):
        if stop_callback is not None and stop_callback():
            raise RuntimeError("Stopped by user.")
        clip_path = output_dir / f"scene_{scene['id']:02d}.mp4"
        _create_scene_clip(
            image_path,
            scene["text"],
            scene["duration"],
            clip_path,
            stop_callback=stop_callback,
        )
        scene_clips.append(clip_path)

    raw_video_path = output_dir / "raw_video.mp4"
    _concat_clips(scene_clips, raw_video_path, stop_callback=stop_callback)

    if stop_callback is not None and stop_callback():
        raise RuntimeError("Stopped by user.")

    final_video_path = output_dir / "final_output.mp4"
    _run_subprocess(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(raw_video_path),
            "-i",
            str(audio_path),
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",  # Fast encoding preset
            "-crf",
            "28",  # Higher CRF = lower quality but faster
            "-c:a",
            "aac",
            "-shortest",
            "-pix_fmt",
            "yuv420p",
            str(final_video_path),
        ],
        stop_callback=stop_callback,
    )

    return final_video_path
