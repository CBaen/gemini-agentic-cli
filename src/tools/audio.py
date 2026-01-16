"""
Audio and Speech Tools

Gemini provides powerful audio capabilities:
- STT (Speech-to-Text): Up to 9.5 hours of audio, 24+ languages
- TTS (Text-to-Speech): Adjustable style, tone, pace, multilingual
- Speaker diarization (identify different speakers)
- Background noise filtering
- Multi-speaker dialogue support
- Seamless language mixing
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, List


# Gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"

# Supported audio formats
SUPPORTED_AUDIO_FORMATS = {'.mp3', '.wav', '.m4a', '.flac', '.ogg', '.aac', '.wma'}

# Available voice styles for TTS
VOICE_STYLES = [
    "natural", "professional", "casual", "enthusiastic",
    "calm", "serious", "friendly", "authoritative"
]

# Supported languages (subset - Gemini supports 24+)
SUPPORTED_LANGUAGES = [
    "en", "es", "fr", "de", "it", "pt", "ja", "ko", "zh",
    "ar", "hi", "ru", "nl", "pl", "tr", "vi", "th", "id"
]


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
    """Call Gemini with appropriate timeout for audio processing."""
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
        return False, "Timeout - audio processing may take longer for large files"
    except Exception as e:
        return False, f"Error: {e}"


def transcribe_audio(
    audio_path: str,
    identify_speakers: bool = False,
    include_timestamps: bool = True,
    language: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Transcribe audio using Gemini's speech recognition.

    Args:
        audio_path: Path to audio file
        identify_speakers: Enable speaker diarization
        include_timestamps: Include timestamps in transcript
        language: Target language code (auto-detected if not specified)
        account: Gemini account to use (1 or 2)

    Returns:
        Tuple of (success: bool, transcript: str)

    Note:
        - Supports up to 9.5 hours of audio
        - 24+ languages supported
        - Background noise filtering applied automatically
    """
    path = Path(audio_path).expanduser().resolve()

    if not path.exists():
        return False, f"Audio file not found: {audio_path}"

    if path.suffix.lower() not in SUPPORTED_AUDIO_FORMATS:
        return False, f"Unsupported audio format: {path.suffix}. Supported: {SUPPORTED_AUDIO_FORMATS}"

    speaker_note = "Identify and label different speakers (Speaker 1, Speaker 2, etc.)." if identify_speakers else ""
    timestamp_note = "Include timestamps [MM:SS] for each segment." if include_timestamps else ""
    language_note = f"The audio is in {language} language." if language else "Auto-detect the language."

    prompt = f"""Transcribe this audio file: {path}

{language_note}
{speaker_note}
{timestamp_note}

Provide a complete, accurate transcript including:
1. All spoken words with proper punctuation
2. Speaker labels (if diarization requested)
3. Timestamps (if requested)
4. [Non-speech sounds] in brackets
5. [Unclear] for inaudible portions

Format for readability."""

    return call_gemini(prompt, account, timeout=600)  # Long timeout for up to 9.5 hours


def generate_speech(
    text: str,
    output_path: str,
    style: str = "natural",
    language: str = "en",
    pace: str = "normal",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Generate speech from text using Gemini TTS.

    Args:
        text: Text to convert to speech
        output_path: Where to save the audio file
        style: Voice style (natural, professional, casual, etc.)
        language: Language code
        pace: Speaking pace (slow, normal, fast)
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, message: str)
    """
    if style not in VOICE_STYLES:
        return False, f"Unsupported voice style: {style}. Supported: {VOICE_STYLES}"

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    prompt = f"""Generate speech audio for the following text:

Text: {text}

Voice Settings:
- Style: {style}
- Language: {language}
- Pace: {pace}
- Output format: MP3

Generate natural-sounding speech with appropriate intonation and emphasis.

If direct audio generation isn't possible in this context, provide:
1. Phonetic guidance for the text
2. Suggested SSML markup
3. Alternative approaches to generate this audio"""

    success, response = call_gemini(prompt, account)

    if success:
        return True, f"Speech generation request sent. Output path: {output_path}\nResponse: {response}"

    return False, response


def generate_dialogue(
    script: List[dict],
    output_path: str,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Generate multi-speaker dialogue audio.

    Args:
        script: List of dicts with 'speaker', 'text', and optional 'style'
               Example: [{"speaker": "Alice", "text": "Hello!", "style": "friendly"}]
        output_path: Where to save the audio file
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, message: str)
    """
    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Format script for prompt
    script_text = "\n".join([
        f"[{item.get('speaker', 'Speaker')}] ({item.get('style', 'natural')}): {item['text']}"
        for item in script
    ])

    prompt = f"""Generate multi-speaker dialogue audio for this script:

{script_text}

Requirements:
- Each speaker should have a distinct voice
- Maintain consistent voices throughout
- Natural conversation flow with appropriate pauses
- Match the specified styles for each speaker

Output format: MP3
Output path: {output_path}

If direct generation isn't possible, provide voice casting suggestions and timing guidance."""

    return call_gemini(prompt, account)


def analyze_audio(
    audio_path: str,
    analysis_type: str = "general",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Analyze audio content beyond transcription.

    Args:
        audio_path: Path to audio file
        analysis_type: Type of analysis:
            - "general": Overall audio analysis
            - "music": Musical analysis (tempo, key, instruments)
            - "emotion": Emotional tone analysis
            - "quality": Audio quality assessment
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, analysis: str)
    """
    path = Path(audio_path).expanduser().resolve()

    if not path.exists():
        return False, f"Audio file not found: {audio_path}"

    analysis_prompts = {
        "general": """Analyze this audio file and describe:
1. Type of audio (speech, music, ambient, mixed)
2. Duration estimate
3. Number of speakers/sources
4. Overall quality
5. Key content summary""",

        "music": """Analyze this music audio:
1. Tempo (BPM estimate)
2. Key signature
3. Time signature
4. Instruments detected
5. Genre classification
6. Mood/energy level
7. Structure (intro, verse, chorus, etc.)""",

        "emotion": """Analyze the emotional content of this audio:
1. Primary emotional tone
2. Emotional variations throughout
3. Speaker sentiment (if speech)
4. Energy/intensity levels
5. Tension points
6. Overall emotional arc""",

        "quality": """Assess the technical quality of this audio:
1. Sample rate estimate
2. Bit depth impression
3. Noise level
4. Dynamic range
5. Clarity/intelligibility
6. Compression artifacts
7. Recommendations for improvement"""
    }

    analysis_prompt = analysis_prompts.get(analysis_type, analysis_prompts["general"])

    prompt = f"""Audio file: {path}

{analysis_prompt}

Provide detailed analysis based on the audio content."""

    return call_gemini(prompt, account)


def translate_audio(
    audio_path: str,
    target_language: str,
    output_mode: str = "text",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Transcribe and translate audio to another language.

    Args:
        audio_path: Path to audio file
        target_language: Language code to translate to
        output_mode: "text" for transcript or "audio" for dubbed audio
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, result: str)
    """
    path = Path(audio_path).expanduser().resolve()

    if not path.exists():
        return False, f"Audio file not found: {audio_path}"

    output_instruction = ""
    if output_mode == "audio":
        output_instruction = f"""
Also generate speech audio in {target_language} that matches the original:
- Preserve speaker characteristics where possible
- Match timing and pacing
- Maintain emotional tone"""

    prompt = f"""Transcribe and translate this audio file: {path}

Target language: {target_language}

1. First, transcribe the original audio
2. Then translate to {target_language}
3. Preserve meaning, tone, and intent
{output_instruction}

Format:
ORIGINAL:
[Original transcript]

TRANSLATION ({target_language}):
[Translated text]"""

    return call_gemini(prompt, account, timeout=300)


def extract_audio_segment(
    audio_path: str,
    start_time: str,
    end_time: str,
    output_path: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Extract and describe a segment of audio.

    Args:
        audio_path: Path to audio file
        start_time: Start timestamp (format: MM:SS)
        end_time: End timestamp (format: MM:SS)
        output_path: Optional path to save extracted segment
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, segment_info: str)
    """
    path = Path(audio_path).expanduser().resolve()

    if not path.exists():
        return False, f"Audio file not found: {audio_path}"

    save_note = f"\nSave extracted segment to: {output_path}" if output_path else ""

    prompt = f"""For the audio file: {path}

Extract and analyze the segment from {start_time} to {end_time}.
{save_note}

Provide:
1. Complete transcript of the segment
2. Description of audio content
3. Speaker information (if speech)
4. Notable audio events
5. Context within the larger audio file"""

    return call_gemini(prompt, account)


# Tool registry
AUDIO_TOOLS = {
    "transcribe_audio": transcribe_audio,
    "generate_speech": generate_speech,
    "generate_dialogue": generate_dialogue,
    "analyze_audio": analyze_audio,
    "translate_audio": translate_audio,
    "extract_audio_segment": extract_audio_segment,
}
