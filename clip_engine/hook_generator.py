import os
import json
import groq
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

VIRAL_HOOK_TEMPLATES = {
    "curiosity_gap": [
        "I tried {topic} for 30 days... here's what happened",
        "Nobody tells you this about {topic}",
        "The truth about {topic} that nobody talks about",
        "I discovered something about {topic} that changed everything",
        "You won't believe what happens when you {topic}",
    ],
    "bold_claim": [
        "This {topic} hack will change your life forever",
        "The #1 mistake everyone makes with {topic}",
        "{topic} in 60 seconds flat",
        "I found the secret to {topic}",
        "Stop doing this with {topic} immediately",
    ],
    "question": [
        "Did you know this about {topic}?",
        "Why is nobody talking about {topic}?",
        "What happens when you {topic}?",
        "Are you making this {topic} mistake?",
        "Want to know the real secret to {topic}?",
    ],
    "contrarian": [
        "Everything you know about {topic} is wrong",
        "Why {topic} is a complete waste of time",
        "{topic} is dead. Here's what to do instead",
        "The worst advice about {topic} is everywhere",
        "Stop believing these {topic} myths",
    ],
    "number": [
        "3 reasons why {topic} fails",
        "5 {topic} hacks the pros don't want you to know",
        "7 signs you're doing {topic} wrong",
        "10 {topic} tips that actually work",
        "The 1 rule that changes everything about {topic}",
    ],
    "story": [
        "Last night something crazy happened with {topic}",
        "I was about to give up on {topic}... then this happened",
        "My {topic} journey took an unexpected turn",
        "What happened next with {topic} shocked me",
        "A stranger taught me this about {topic}",
    ],
    "pain_point": [
        "Tired of failing at {topic}? Watch this",
        "If {topic} is stressing you out, you need this",
        "Stop struggling with {topic} - here's the fix",
        "The {topic} problem nobody is solving",
        "Why {topic} never works for you",
    ],
    "transformation": [
        "From zero to hero with {topic}",
        "How I mastered {topic} in 30 days",
        "Before vs after learning {topic}",
        "My {topic} transformation story",
        "From hating {topic} to loving it",
    ],
}

ALL_HOOK_TYPES = list(VIRAL_HOOK_TEMPLATES.keys())


def generate_hooks(
    topic: str,
    num_hooks: int = 5,
    hook_types: Optional[list] = None,
    content_context: str = "",
    api_key: Optional[str] = None,
) -> list:
    if hook_types is None:
        hook_types = ALL_HOOK_TYPES

    if api_key is None:
        api_key = os.environ.get("GROQ_API_KEY")
    
    client = groq.Groq(api_key=api_key)

    templates_section = ""
    for htype in hook_types:
        if htype in VIRAL_HOOK_TEMPLATES:
            templates_section += f"\n{htype}:\n"
            for t in VIRAL_HOOK_TEMPLATES[htype]:
                templates_section += f"  - {t}\n"

    context_line = ""
    if content_context:
        context_line = f"\nContent context: {content_context}"

    prompt = f"""You are a viral content expert. Generate {num_hooks} engaging hooks for short-form video.

Topic: {topic}{context_line}

Proven hook templates (use as inspiration, create ORIGINAL variations):

{templates_section}

Requirements:
- Each hook must be 5-15 words
- Create original variations inspired by the templates
- Mix different hook types for variety
- Make them scroll-stopping and attention-grabbing
- Consider the video content for relevance
- Use power words: secret, hack, truth, mistake, stop, never, always

Return ONLY a JSON array of hook objects with "hook" and "type" fields.
Example format: [{{"hook": "This changed my life", "type": "bold_claim"}}]

Generate exactly {num_hooks} hooks. Return ONLY the JSON array, no other text."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=1000,
    )

    text = response.choices[0].message.content.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        hooks = json.loads(text)
        if isinstance(hooks, list):
            return hooks[:num_hooks]
    except json.JSONDecodeError:
        pass

    fallback_hooks = []
    import random
    for i in range(num_hooks):
        htype = random.choice(hook_types)
        if htype in VIRAL_HOOK_TEMPLATES:
            template = random.choice(VIRAL_HOOK_TEMPLATES[htype])
            fallback_hooks.append({
                "hook": template.format(topic=topic),
                "type": htype,
            })
    return fallback_hooks


def _get_ffmpeg_exe():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        return 'ffmpeg'

FFMPEG_EXE = _get_ffmpeg_exe()


def _get_font_path():
    import platform
    system = platform.system()
    if system == "Darwin":
        return "/System/Library/Fonts/Supplemental/Arial.ttf"
    elif system == "Windows":
        return "C:/Windows/Fonts/arial.ttf"
    else:
        for font in [
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        ]:
            if os.path.exists(font):
                return font
        return "sans-serif"


def add_hook_overlay(video_path: str, hook_text: str, output_path: str) -> str:
    import subprocess

    duration = "3"
    fontsize = "48"
    fontcolor = "white"
    borderw = "3"
    bordercolor = "black"
    font_path = _get_font_path()

    font_param = f"fontfile='{font_path}':" if font_path != "sans-serif" else ""
    drawtext = (
        f"drawtext={font_param}"
        f"text='{_escape_ffmpeg(hook_text)}':"
        f"fontsize={fontsize}:"
        f"fontcolor={fontcolor}:"
        f"borderw={borderw}:"
        f"bordercolor={bordercolor}:"
        f"x=(w-text_w)/2:"
        f"y=(h-text_h)/4:"
        f"enable='between(t,0.5,{duration})'"
    )

    cmd = [
        FFMPEG_EXE, "-y",
        "-i", video_path,
        "-vf", drawtext,
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "fast",
        "-c:a", "copy",
        output_path,
    ]

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return output_path


def _escape_ffmpeg(text: str) -> str:
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text
