import os
import uuid
import shutil
import subprocess
from typing import Callable, Optional, Dict, Any

import yt_dlp

def _get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return shutil.which('ffmpeg') or 'ffmpeg'

FFMPEG_EXE = _get_ffmpeg_exe()
FFMPEG_PATH = os.path.dirname(FFMPEG_EXE)


def download_video(
    url: str, 
    output_dir: str, 
    quality: str = "best", 
    progress_callback: Optional[Callable[[float], None]] = None
) -> Dict[str, Any]:
    """
    Downloads a video using yt-dlp.
    Returns a dictionary with file_path, duration, title, and resolution.
    """
    file_id = str(uuid.uuid4())
    output_template = os.path.join(output_dir, f"{file_id}.%(ext)s")
    
    # Information to collect
    download_info = {}

    def yt_dlp_progress_hook(d):
        if d['status'] == 'finished':
            if progress_callback:
                progress_callback(100.0)
        elif d['status'] == 'downloading':
            # Calculate percentage
            downloaded = d.get('downloaded_bytes', 0)
            total = d.get('total_bytes', 0) or d.get('total_bytes_estimate', 0)
            if total > 0:
                percent = (downloaded / total) * 100
                if progress_callback:
                    progress_callback(percent)

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_template,
        'progress_hooks': [yt_dlp_progress_hook],
        'quiet': True,
        'no_warnings': True,

    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        file_path = ydl.prepare_filename(info_dict)
        
        # Ensure correct extension if merged
        if not file_path.endswith('.mp4') and os.path.exists(file_path):
            pass # yt-dlp might have changed the extension to .mkv depending on ffmpeg, we handle this gracefully
        
        # In case ffmpeg merged to a different extension, we need to find the actual file
        # We can just look for the base name
        base_path = os.path.splitext(file_path)[0]
        actual_path = file_path
        if not os.path.exists(file_path):
            for ext in ['.mp4', '.mkv', '.webm']:
                if os.path.exists(base_path + ext):
                    actual_path = base_path + ext
                    break
        
        download_info = {
            "file_path": actual_path,
            "duration": info_dict.get('duration', 0.0),
            "title": info_dict.get('title', 'Unknown Title'),
            "resolution": f"{info_dict.get('width', 0)}x{info_dict.get('height', 0)}"
        }

    return download_info


def register_local_upload(file_path: str) -> Dict[str, Any]:
    """
    Registers a local uploaded file and extracts its metadata using ffprobe to match download_video interface.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    # Get metadata using ffprobe
    # We use subprocess to call ffprobe, which is part of ffmpeg
    cmd = [
        'ffprobe', 
        '-v', 'error', 
        '-show_entries', 'format=duration', 
        '-of', 'default=noprint_wrappers=1:nokey=1', 
        file_path
    ]
    
    try:
        duration_str = subprocess.check_output(cmd).decode('utf-8').strip()
        duration = float(duration_str)
    except Exception:
        duration = 0.0
        
    cmd_res = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=s=x:p=0',
        file_path
    ]
    
    try:
        resolution = subprocess.check_output(cmd_res).decode('utf-8').strip()
    except Exception:
        resolution = "0x0"
        
    filename = os.path.basename(file_path)
    title = os.path.splitext(filename)[0]

    return {
        "file_path": file_path,
        "duration": duration,
        "title": title,
        "resolution": resolution
    }
