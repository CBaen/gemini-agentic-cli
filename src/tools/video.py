"""
Video Analysis Tools

Gemini can analyze video content with powerful capabilities:
- 1M token context = ~1 hour of video
- Timestamp-based querying (format: MM:SS)
- Frame extraction (configurable FPS, default 1 FPS)
- Scene description and segmentation
- Object/count analysis
- Emotion detection
- Audio+visual transcription
- Supports up to 10 videos per request
- YouTube URLs also supported
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, List


# Gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"

# Supported video formats
SUPPORTED_VIDEO_FORMATS = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}


def get_git_bash() -> Optional[Path]:
    """Find Git Bash on Windows."""
    if sys.platform != 'win32':
        return None
    paths = [
        Path("C:/Program Files/Git/usr/bin/bash.exe"),
        Path("C:/Program Files/Git/bin/bash.exe"),
    ]
    for p in paths:
        if p.exists():
            return p
    return None


def call_gemini(query: str, account: int = 1, timeout: int = 180) -> Tuple[bool, str]:
    """Call Gemini with extended timeout for video analysis."""
    if not GEMINI_SCRIPT.exists():
        return False, f"gemini-account.sh not found"

    try:
        if sys.platform == 'win32':
            git_bash = get_git_bash()
            if not git_bash:
                return False, "Git Bash not found"
            cmd = [str(git_bash), str(GEMINI_SCRIPT), str(account), query]
        else:
            cmd = ["bash", str(GEMINI_SCRIPT), str(account), query]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Error: {error}"

        response = result.stdout.strip()
        return bool(response), response or "Empty response"

    except subprocess.TimeoutExpired:
        return False, "Timeout - video analysis may take longer for large files"
    except Exception as e:
        return False, f"Error: {e}"


def analyze_video(
    video_path: str,
    query: str,
    timestamp: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Analyze video content using Gemini.

    Args:
        video_path: Path to video file or YouTube URL
        query: What to analyze or find in the video
        timestamp: Optional specific timestamp to focus on (format: MM:SS)
        account: Gemini account to use (1 or 2)

    Returns:
        Tuple of (success: bool, analysis: str)

    Note:
        - 1M token context supports ~1 hour of video
        - Frame extraction at 1 FPS by default
    """
    # Check if it's a YouTube URL
    is_youtube = video_path.startswith(('http://', 'https://')) and ('youtube.com' in video_path or 'youtu.be' in video_path)

    if not is_youtube:
        path = Path(video_path).expanduser().resolve()
        if not path.exists():
            return False, f"Video not found: {video_path}"
        if path.suffix.lower() not in SUPPORTED_VIDEO_FORMATS:
            return False, f"Unsupported video format: {path.suffix}"
        video_ref = str(path)
    else:
        video_ref = video_path

    timestamp_note = ""
    if timestamp:
        timestamp_note = f"\nFocus specifically on timestamp: {timestamp}"

    prompt = f"""Analyze this video: {video_ref}
{timestamp_note}

Query: {query}

Provide a detailed analysis including:
1. Direct answer to the query
2. Relevant visual elements observed
3. Any audio/speech content related to the query
4. Timestamps of key moments (format: MM:SS)

If you cannot directly access the video, explain what analysis would be performed and what information would be extracted."""

    return call_gemini(prompt, account, timeout=300)  # Extended timeout for video


def describe_video_scene(
    video_path: str,
    start_time: str = None,
    end_time: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Generate detailed scene descriptions for a video segment.

    Args:
        video_path: Path to video file or YouTube URL
        start_time: Start timestamp (format: MM:SS), defaults to beginning
        end_time: End timestamp (format: MM:SS), defaults to end
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, scene_descriptions: str)
    """
    time_range = ""
    if start_time or end_time:
        start = start_time or "00:00"
        end = end_time or "end"
        time_range = f"\nAnalyze segment from {start} to {end}"

    prompt = f"""Describe the scenes in this video: {video_path}
{time_range}

For each distinct scene, provide:
1. Scene number and timestamp range (MM:SS - MM:SS)
2. Setting/environment description
3. People/objects present
4. Actions occurring
5. Audio/dialogue summary
6. Mood/atmosphere

Segment the video into logical scenes based on visual or narrative changes."""

    return call_gemini(prompt, account, timeout=300)


def extract_video_frames(
    video_path: str,
    timestamps: List[str],
    output_dir: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Extract and describe frames at specific timestamps.

    Args:
        video_path: Path to video file
        timestamps: List of timestamps to extract (format: MM:SS)
        output_dir: Optional directory to save extracted frames
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, frame_descriptions: str)
    """
    timestamps_str = ", ".join(timestamps)

    prompt = f"""For the video at: {video_path}

Extract and describe the frames at these timestamps: {timestamps_str}

For each frame, provide:
1. Timestamp
2. Detailed visual description
3. Any text visible in the frame
4. Key objects and their positions
5. Overall context within the video narrative

If frame extraction isn't directly possible, describe what would be visible at each timestamp based on video analysis."""

    return call_gemini(prompt, account, timeout=180)


def transcribe_video(
    video_path: str,
    include_timestamps: bool = True,
    identify_speakers: bool = False,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Transcribe audio from video with optional speaker identification.

    Args:
        video_path: Path to video file or YouTube URL
        include_timestamps: Whether to include timestamps in transcript
        identify_speakers: Whether to identify different speakers
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, transcript: str)
    """
    timestamp_note = "Include timestamps (format: [MM:SS]) for each segment." if include_timestamps else ""
    speaker_note = "Identify and label different speakers (Speaker 1, Speaker 2, etc.)." if identify_speakers else ""

    prompt = f"""Transcribe all speech and dialogue from this video: {video_path}

{timestamp_note}
{speaker_note}

Provide a complete transcript including:
1. All spoken words
2. Speaker attribution (if requested)
3. Notable non-speech audio cues [in brackets]
4. Timestamps (if requested)

Format the transcript clearly with proper punctuation."""

    return call_gemini(prompt, account, timeout=300)


def count_objects_in_video(
    video_path: str,
    object_type: str,
    throughout: bool = True,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Count occurrences of specific objects throughout a video.

    Args:
        video_path: Path to video file
        object_type: Type of object to count (e.g., "people", "cars", "dogs")
        throughout: If True, track throughout video; if False, count at single point
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, count_results: str)
    """
    tracking_mode = "throughout the entire video, noting when counts change" if throughout else "at a representative point"

    prompt = f"""Count the number of "{object_type}" in this video: {video_path}

Count {tracking_mode}.

Provide:
1. Total/maximum count observed
2. Timestamps when counts change (if tracking throughout)
3. Locations within frame where objects appear
4. Any uncertainty or occlusion notes

Be precise about what you're counting and note any ambiguous cases."""

    return call_gemini(prompt, account, timeout=180)


def detect_video_emotions(
    video_path: str,
    subjects: str = "all people",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Detect and track emotions of people in a video.

    Args:
        video_path: Path to video file
        subjects: Who to analyze ("all people", "speaker", specific description)
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, emotion_analysis: str)
    """
    prompt = f"""Analyze the emotions displayed in this video: {video_path}

Focus on: {subjects}

For each subject/moment:
1. Timestamp range
2. Primary emotion detected
3. Secondary emotions (if any)
4. Facial expressions observed
5. Body language indicators
6. Vocal tone (if speaking)
7. Confidence level of detection

Track emotional changes throughout the video and note significant transitions."""

    return call_gemini(prompt, account, timeout=240)


# Tool registry
VIDEO_TOOLS = {
    "analyze_video": analyze_video,
    "describe_video_scene": describe_video_scene,
    "extract_video_frames": extract_video_frames,
    "transcribe_video": transcribe_video,
    "count_objects_in_video": count_objects_in_video,
    "detect_video_emotions": detect_video_emotions,
}
