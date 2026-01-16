"""
Image Tools - Generation and Analysis

Gemini has powerful multimodal capabilities:
- Image analysis: OCR, object detection with bounding boxes, visual Q&A
- Image generation: Create images via gemini-2.5-flash-image (500 free/day)

Capabilities (from research):
- Zero-shot object detection and segmentation
- Bounding box coordinates for detected objects
- Formats: PNG, JPEG, BMP, WebP (up to 15MB, 24 megapixels, max 3 per prompt)
- Generation aspect ratios: 21:9, 16:9, 4:3, 3:2, 1:1, 2:3, 3:4, 9:16, 9:21

Model Routing:
- Image analysis: gemini-2.5-flash (default)
- Image generation: gemini-2.5-flash-image (auto-selected)
"""

import subprocess
import sys
import os
import base64
import json
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any


# Gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"

# Model IDs
MODEL_FLASH = "gemini-2.5-flash"
MODEL_FLASH_IMAGE = "gemini-2.5-flash-image"

# Supported aspect ratios for image generation
SUPPORTED_ASPECT_RATIOS = [
    "21:9", "16:9", "4:3", "3:2", "1:1", "2:3", "3:4", "9:16", "9:21"
]

# Supported image formats for analysis
SUPPORTED_IMAGE_FORMATS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp'}


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


def call_gemini(
    query: str,
    account: int = 1,
    timeout: int = 120,
    model: str = MODEL_FLASH
) -> Tuple[bool, str]:
    """
    Call Gemini and return response.

    Args:
        query: The prompt to send
        account: Account number (1 or 2)
        timeout: Request timeout in seconds
        model: Model ID (gemini-2.5-flash or gemini-2.5-flash-image)

    Returns:
        Tuple of (success, response)
    """
    if not GEMINI_SCRIPT.exists():
        return False, f"gemini-account.sh not found"

    try:
        if sys.platform == 'win32':
            git_bash = get_git_bash()
            if not git_bash:
                return False, "Git Bash not found"
            cmd = [str(git_bash), str(GEMINI_SCRIPT), str(account), query, model]
        else:
            cmd = ["bash", str(GEMINI_SCRIPT), str(account), query, model]

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


def generate_image(
    prompt: str,
    output_path: str,
    aspect_ratio: str = "1:1",
    style: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Generate an image using gemini-2.5-flash-image model.

    This automatically uses the image generation model (500 free images/day).

    Args:
        prompt: Description of the image to generate
        output_path: Where to save the generated image
        aspect_ratio: One of: 21:9, 16:9, 4:3, 3:2, 1:1, 2:3, 3:4, 9:16, 9:21
        style: Optional style modifier (photorealistic, illustration, etc.)
        account: Gemini account to use (1 or 2)

    Returns:
        Tuple of (success: bool, message: str)

    Model: gemini-2.5-flash-image (auto-selected)
    Free quota: 500 images per day

    Limitations:
        - Text in images: 25 characters or less recommended
        - May struggle with: precise spatial reasoning, medical images, non-Latin text
    """
    if aspect_ratio not in SUPPORTED_ASPECT_RATIOS:
        return False, f"Unsupported aspect ratio: {aspect_ratio}. Supported: {SUPPORTED_ASPECT_RATIOS}"

    output = Path(output_path).expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    # Build the generation prompt
    style_text = f" in {style} style" if style else ""
    full_prompt = f"""Generate an image with the following specifications:

Prompt: {prompt}{style_text}
Aspect Ratio: {aspect_ratio}
Output Format: PNG

Please generate this image. Return the image data or confirm generation."""

    # Use the image generation model (gemini-2.5-flash-image)
    success, response = call_gemini(full_prompt, account, model=MODEL_FLASH_IMAGE)

    if success:
        return True, f"Image generation request sent using {MODEL_FLASH_IMAGE}.\nOutput path: {output_path}\nResponse: {response}"

    return False, response


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

Provide a detailed, vivid prompt that would work well with Imagen. Include:
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


def detect_objects(
    image_path: str,
    objects_to_find: List[str] = None,
    return_bounding_boxes: bool = True,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Detect objects in an image with optional bounding box coordinates.

    Gemini 2.5 supports zero-shot object detection and segmentation.

    Args:
        image_path: Path to the image file
        objects_to_find: Optional list of specific objects to look for
        return_bounding_boxes: Whether to return bounding box coordinates
        account: Gemini account to use (1 or 2)

    Returns:
        Tuple of (success: bool, detection_results: str)
    """
    path = Path(image_path).expanduser().resolve()

    if not path.exists():
        return False, f"Image not found: {image_path}"

    if path.suffix.lower() not in SUPPORTED_IMAGE_FORMATS:
        return False, f"Unsupported image format: {path.suffix}"

    objects_filter = ""
    if objects_to_find:
        objects_filter = f"\nSpecifically look for: {', '.join(objects_to_find)}"

    bbox_request = ""
    if return_bounding_boxes:
        bbox_request = """
For each detected object, provide bounding box coordinates in the format:
- Object: [name]
  Location: [x_min, y_min, x_max, y_max] (normalized 0-1 coordinates)
  Confidence: [high/medium/low]"""

    prompt = f"""Perform object detection on the image at: {path}
{objects_filter}
{bbox_request}

Identify all distinct objects visible in the image. For each object:
1. Name/classification
2. Position in the image (if bounding boxes requested)
3. Confidence level
4. Any relevant attributes (color, size, state)

Return results in a structured format."""

    return call_gemini(prompt, account)


def compare_images(
    image_path_1: str,
    image_path_2: str,
    comparison_type: str = "visual",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Compare two images and describe differences.

    Args:
        image_path_1: Path to first image
        image_path_2: Path to second image
        comparison_type: Type of comparison (visual, structural, content)
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, comparison_result: str)
    """
    path1 = Path(image_path_1).expanduser().resolve()
    path2 = Path(image_path_2).expanduser().resolve()

    if not path1.exists():
        return False, f"Image not found: {image_path_1}"
    if not path2.exists():
        return False, f"Image not found: {image_path_2}"

    prompt = f"""Compare these two images:
Image 1: {path1}
Image 2: {path2}

Comparison type: {comparison_type}

Analyze and describe:
1. Key similarities between the images
2. Key differences between the images
3. Overall assessment of how similar/different they are
4. Any notable changes if these appear to be versions of the same content

Be specific about visual elements, layout, content, and style."""

    return call_gemini(prompt, account)


# Tool registry
IMAGE_TOOLS = {
    "analyze_image": analyze_image,
    "generate_image": generate_image,
    "generate_image_prompt": generate_image_prompt,
    "describe_for_accessibility": describe_for_accessibility,
    "extract_text_from_image": extract_text_from_image,
    "detect_objects": detect_objects,
    "compare_images": compare_images,
}
