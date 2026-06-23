import os
import subprocess
import shutil
import math
from typing import List


def _get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which('ffmpeg') or 'ffmpeg'


FFMPEG_EXE = _get_ffmpeg_exe()


def format_timestamp(seconds: float) -> str:
    """
    Formats seconds into SRT timestamp format: HH:MM:SS,mmm
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def extract_audio(video_path: str, output_audio_path: str) -> str:
    """
    Extracts audio from video using ffmpeg.
    Outputs as mp3 to keep file size under Groq's 25MB limit.
    """
    os.makedirs(os.path.dirname(output_audio_path), exist_ok=True)

    mp3_path = output_audio_path.replace('.wav', '.mp3')

    cmd = [
        FFMPEG_EXE, "-y",
        "-i", video_path,
        "-vn",
        "-acodec", "libmp3lame",
        "-ab", "64k",
        "-ar", "16000",
        "-ac", "1",
        mp3_path
    ]

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8')
        raise RuntimeError(f"Failed to extract audio: {error_msg}")

    return mp3_path


def check_ffmpeg_installed() -> bool:
    """
    Checks if ffmpeg is installed and available.
    """
    return os.path.exists(FFMPEG_EXE)


def cleanup_files(file_paths: List[str]):
    """
    Removes temporary files.
    """
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"Failed to clean up {path}: {e}")
