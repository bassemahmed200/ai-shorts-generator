import os
import subprocess
from typing import List, Dict, Any
from .utils import format_timestamp

def _get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return 'ffmpeg'

FFMPEG_EXE = _get_ffmpeg_exe()

def generate_srt(transcript_segments: List[Dict[str, Any]], start_time: float, end_time: float, output_path: str):
    """
    Generates an SRT file for the clip, recalculating timestamps relative to start_time.
    Only includes segments that fall within [start_time, end_time].
    """
    lines = []
    counter = 1
    
    for seg in transcript_segments:
        # Check if segment overlaps with the clip window
        if seg["end"] < start_time or seg["start"] > end_time:
            continue
            
        # Adjust timestamps relative to clip start
        rel_start = max(0, seg["start"] - start_time)
        rel_end = min(end_time - start_time, seg["end"] - start_time)
        
        # Don't add segments that are too short after cropping
        if rel_end - rel_start < 0.1:
            continue
            
        lines.append(str(counter))
        lines.append(f"{format_timestamp(rel_start)} --> {format_timestamp(rel_end)}")
        lines.append(seg["text"])
        lines.append("")
        counter += 1
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        
    return output_path

RESOLUTIONS = {
    "portrait": (1080, 1920),  # 9:16 vertical (TikTok/Reels/Shorts)
    "landscape": (1920, 1080),  # 16:9 horizontal (YouTube)
    "square": (1080, 1080),    # 1:1 square (Instagram/Facebook)
}


def build_ffmpeg_command(
    input_path: str,
    start: float,
    end: float,
    output_path: str,
    crop_style: str = "portrait"
) -> List[str]:
    """
    Builds the ffmpeg command for cropping video.
    crop_style: "portrait" (9:16) or "landscape" (16:9)
    """
    w, h = RESOLUTIONS.get(crop_style, RESOLUTIONS["portrait"])

    filter_complex = (
        f"scale=-2:{h},"
        f"crop={w}:{h}:(in_w-{w})/2:(in_h-{h})/2"
    )

    cmd = [
        FFMPEG_EXE, "-y",
        "-ss", str(start),
        "-to", str(end),
        "-i", input_path,
        "-vf", filter_complex,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]

    return cmd


def crop_video(
    input_path: str,
    start: float,
    end: float,
    output_path: str,
    crop_style: str = "portrait"
):
    """
    Uses ffmpeg to cut and crop video.
    crop_style: "portrait" (9:16) or "landscape" (16:9)
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")

    cmd = build_ffmpeg_command(input_path, start, end, output_path, crop_style)

    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8')
        raise RuntimeError(f"FFmpeg error during video editing: {error_msg}")

    return output_path


def crop_to_vertical(
    input_path: str,
    start: float,
    end: float,
    output_path: str,
    target_resolution: tuple = (1080, 1920)
):
    """
    Backward-compatible wrapper.
    """
    return crop_video(input_path, start, end, output_path, "portrait")
