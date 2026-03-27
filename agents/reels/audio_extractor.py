"""Audio extraction from video files using ffmpeg"""

import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_audio(video_path: str, output_format: str = "mp3") -> dict:
    """
    Extract audio from a video file using ffmpeg.

    Returns dict with:
        - audio_path: path to extracted audio file
        - duration: audio duration in seconds
    """
    video_path = Path(video_path)
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    audio_path = video_path.with_suffix(f".{output_format}")

    # Extract audio with ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "libmp3lame",
        "-q:a", "2",
        str(audio_path),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")

    # Get duration
    duration = _get_duration(str(audio_path))

    return {
        "audio_path": str(audio_path),
        "duration": duration,
    }


def _get_duration(file_path: str) -> float | None:
    """Get the duration of an audio/video file in seconds."""
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())
    except Exception as e:
        logger.warning(f"Could not get duration: {e}")
    return None
