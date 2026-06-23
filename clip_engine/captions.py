import os
import subprocess
from typing import List, Dict, Any

from .subtitles import generate_ass

def _get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return 'ffmpeg'

FFMPEG_EXE = _get_ffmpeg_exe()


def generate_captions(
    transcript_segments: List[Dict[str, Any]],
    start_time: float,
    end_time: float,
    output_path: str,
    style: str = "hormozi",
    language: str = "en",
    video_width: int = None,
    video_height: int = None
) -> str:
    """
    Generates an ASS subtitle file with word-by-word animations.
    
    Styles: hormozi, mrbeast, karaoke, minimal, bounce, classic
    """
    transcript = {
        "language": language,
        "segments": []
    }
    
    for seg in transcript_segments:
        if seg["end"] < start_time or seg["start"] > end_time:
            continue
        
        words = seg.get("words", [])
        word_entries = []
        
        if words:
            for w in words:
                word_entries.append({
                    "word": w["word"],
                    "start": w["start"],
                    "end": w["end"]
                })
        
        if not word_entries:
            word_entries = [{"word": seg["text"].strip(), "start": seg["start"], "end": seg["end"]}]
        
        transcript["segments"].append({
            "words": word_entries
        })
    
    success = generate_ass(
        transcript=transcript,
        clip_start=start_time,
        clip_end=end_time,
        output_path=output_path,
        caption_style=style,
        language=language,
        video_width=video_width,
        video_height=video_height
    )
    
    if not success:
        with open(output_path, "w", encoding="utf-8-sig") as f:
            f.write("[Script Info]\nTitle: Captions\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,60,&H00FFFFFF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,3,0,2,20,20,120,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    
    return output_path


def burn_captions(
    input_path: str,
    ass_path: str,
    output_path: str,
    target_resolution: tuple = None
) -> str:
    """
    Burns ASS captions into video using ffmpeg with libass support.
    The video is already cropped, so we just add the subtitles.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input video not found: {input_path}")
    if not os.path.exists(ass_path):
        raise FileNotFoundError(f"ASS file not found: {ass_path}")
    
    escaped_ass = ass_path.replace('\\', '/').replace(':', '\\:').replace("'", "\\'")
    
    if target_resolution:
        w, h = target_resolution
        vf = f"scale=-2:{h},crop={w}:{h}:(in_w-{w})/2:(in_h-{h})/2,ass='{escaped_ass}'"
    else:
        vf = f"ass='{escaped_ass}'"
    
    cmd = [
        FFMPEG_EXE, "-y",
        "-i", input_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-preset", "fast",
        "-crf", "23",
        "-c:a", "aac",
        "-b:a", "128k",
        "-movflags", "+faststart",
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode('utf-8')
        raise RuntimeError(f"FFmpeg error burning captions: {error_msg}")
    
    return output_path
