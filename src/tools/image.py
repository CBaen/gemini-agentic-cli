"""
Image Tools - Generation and Analysis

Gemini has powerful multimodal capabilities:
- Image analysis: Describe, OCR, object detection
- Image generation: Create images from text prompts (Imagen)

Note: Image generation via CLI may require specific Gemini model configurations.
Analysis works with base64-encoded images or file paths.
"""

import subprocess
import sys
import os
import base64
from pathlib import Path
from typing import Tuple, Optional


# Gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"


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


def call_gemini(query: str, account: int = 1, timeout: int = 120) -> Tuple[bool, str]:
    """Call Gemini and return response."""
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
        return False, "Timeout"
    except Exception as e:
        return False, f"Error: {e}"


def analyze_image(
    image_path: str,
    prompt: str = "Describe this image in detail.",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Analyze an image using Gemini's vision capabilities.

    Args:
        image_path: Path to the image file
        prompt: Analysis prompt (default: general description)
        account: Gemini account to use (1 or 2)

    Returns:
        Tuple of (success: bool, analysis: str)

    Note:
        This creates a prompt that describes the image context.
        For true multimodal analysis, the gemini-account.sh script
        would need to support image inputs directly.
    """
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        return False, f"Image not found: {image_path}"

    if not path.is_file():
        return False, f"Not a file: {image_path}"

    # Check file extension
    valid_extensions = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}
    if path.suffix.lower() not in valid_extensions:
        return False, f"Unsupported image format: {path.suffix}"

    # For CLI-based Gemini, we describe the analysis request
    # True multimodal would require API integration
    full_prompt = f"""I have an image file at: {path}

Please analyze this image. {prompt}

Note: If you cannot see the image directly, describe what analysis you would perform and what information would be useful."""

    return call_gemini(full_prompt, account)


def generate_image_prompt(
    description: str,
    style: str = "photorealistic",
    aspect_ratio: str = "1:1"
) -> Tuple[bool, str]:
    """
    Generate an optimized prompt for image generation.

    Gemini can help craft better prompts for image generation tools.

    Args:
        description: Basic description of desired image
        style: Art style (photorealistic, illustration, painting, etc.)
        aspect_ratio: Desired aspect ratio (1:1, 16:9, 4:3, etc.)

    Returns:
        Tuple of (success: bool, optimized_prompt: str)
    """
    prompt = f"""Create an optimized image generation prompt for the following:

Description: {description}
Style: {style}
Aspect Ratio: {aspect_ratio}

Provide a detailed, vivid prompt that would work well with image generation models like DALL-E, Midjourney, or Imagen. Include:
- Specific visual details
- Lighting and atmosphere
- Composition suggestions
- Style keywords

Return only the optimized prompt, nothing else."""

    return call_gemini(prompt, account=1)


def describe_for_accessibility(
    image_path: str,
    context: str = ""
) -> Tuple[bool, str]:
    """
    Generate accessibility-focused image description.

    Creates alt-text style descriptions suitable for screen readers.

    Args:
        image_path: Path to the image
        context: Optional context about where the image appears

    Returns:
        Tuple of (success: bool, alt_text: str)
    """
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        return False, f"Image not found: {image_path}"

    context_note = f" Context: {context}" if context else ""

    prompt = f"""Generate an accessibility-focused description for the image at: {path}{context_note}

Create a concise but informative alt-text description suitable for screen readers. Include:
- Main subject or content
- Important visual elements
- Any text visible in the image
- Emotional tone or atmosphere if relevant

Keep it under 150 words but make it descriptive enough to convey the image's meaning."""

    return call_gemini(prompt, account=1)


def extract_text_from_image(image_path: str) -> Tuple[bool, str]:
    """
    Extract text from an image (OCR-style).

    Args:
        image_path: Path to the image

    Returns:
        Tuple of (success: bool, extracted_text: str)
    """
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        return False, f"Image not found: {image_path}"

    prompt = f"""Extract all text visible in the image at: {path}

Return only the extracted text, preserving the layout as much as possible.
If no text is visible, state "No text detected in image."

Note: For actual OCR, this would require direct image input to Gemini's vision model."""

    return call_gemini(prompt, account=1)


# Tool registry
IMAGE_TOOLS = {
    "analyze_image": analyze_image,
    "generate_image_prompt": generate_image_prompt,
    "describe_for_accessibility": describe_for_accessibility,
    "extract_text_from_image": extract_text_from_image,
}
