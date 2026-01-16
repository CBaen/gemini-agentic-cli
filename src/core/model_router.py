"""
Model Router - Automatic Model Selection Based on Task Type

Routes requests to the appropriate Gemini model:
- gemini-2.5-flash: Default for text, video, audio, documents, code
- gemini-2.5-flash-image: Image generation tasks
- gemini-2.5-pro: Complex reasoning (manual override)

Free tier quotas (per account per day):
- Text/multimodal: ~1,000 requests
- Image generation: 500 images
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class GeminiModel(Enum):
    """Available Gemini models."""
    FLASH = "gemini-2.5-flash"
    FLASH_IMAGE = "gemini-2.5-flash-image"
    PRO = "gemini-2.5-pro"


class TaskType(Enum):
    """Task types for automatic model routing."""
    # Default tasks - use FLASH
    TEXT = "text"
    CHAT = "chat"
    CODE = "code"
    SEARCH = "search"

    # Multimodal input tasks - use FLASH
    VIDEO_ANALYSIS = "video_analysis"
    AUDIO_ANALYSIS = "audio_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    IMAGE_ANALYSIS = "image_analysis"

    # Image output tasks - use FLASH_IMAGE
    IMAGE_GENERATION = "image_generation"

    # Complex reasoning - use PRO (manual)
    COMPLEX_REASONING = "complex_reasoning"


@dataclass
class ModelConfig:
    """Configuration for a model."""
    model_id: str
    description: str
    daily_quota: int
    supports_image_output: bool = False
    supports_thinking: bool = True


# Model configurations
MODEL_CONFIGS = {
    GeminiModel.FLASH: ModelConfig(
        model_id="gemini-2.5-flash",
        description="Fast, balanced model for most tasks",
        daily_quota=1000,
        supports_image_output=False,
        supports_thinking=True
    ),
    GeminiModel.FLASH_IMAGE: ModelConfig(
        model_id="gemini-2.5-flash-image",
        description="Image generation model",
        daily_quota=500,
        supports_image_output=True,
        supports_thinking=False
    ),
    GeminiModel.PRO: ModelConfig(
        model_id="gemini-2.5-pro",
        description="Best reasoning, complex tasks",
        daily_quota=1000,
        supports_image_output=False,
        supports_thinking=True
    ),
}


# Task to model mapping
TASK_MODEL_MAP = {
    # Default tasks -> FLASH
    TaskType.TEXT: GeminiModel.FLASH,
    TaskType.CHAT: GeminiModel.FLASH,
    TaskType.CODE: GeminiModel.FLASH,
    TaskType.SEARCH: GeminiModel.FLASH,

    # Multimodal input -> FLASH
    TaskType.VIDEO_ANALYSIS: GeminiModel.FLASH,
    TaskType.AUDIO_ANALYSIS: GeminiModel.FLASH,
    TaskType.DOCUMENT_ANALYSIS: GeminiModel.FLASH,
    TaskType.IMAGE_ANALYSIS: GeminiModel.FLASH,

    # Image output -> FLASH_IMAGE
    TaskType.IMAGE_GENERATION: GeminiModel.FLASH_IMAGE,

    # Complex reasoning -> PRO
    TaskType.COMPLEX_REASONING: GeminiModel.PRO,
}


# Tool name to task type mapping
TOOL_TASK_MAP = {
    # Image generation tools
    "generate_image": TaskType.IMAGE_GENERATION,

    # Image analysis tools
    "analyze_image": TaskType.IMAGE_ANALYSIS,
    "describe_for_accessibility": TaskType.IMAGE_ANALYSIS,
    "extract_text_from_image": TaskType.IMAGE_ANALYSIS,
    "detect_objects": TaskType.IMAGE_ANALYSIS,
    "compare_images": TaskType.IMAGE_ANALYSIS,

    # Video tools
    "analyze_video": TaskType.VIDEO_ANALYSIS,
    "describe_video_scene": TaskType.VIDEO_ANALYSIS,
    "extract_video_frames": TaskType.VIDEO_ANALYSIS,
    "transcribe_video": TaskType.VIDEO_ANALYSIS,
    "count_objects_in_video": TaskType.VIDEO_ANALYSIS,
    "detect_video_emotions": TaskType.VIDEO_ANALYSIS,

    # Audio tools
    "transcribe_audio": TaskType.AUDIO_ANALYSIS,
    "analyze_audio": TaskType.AUDIO_ANALYSIS,
    "translate_audio": TaskType.AUDIO_ANALYSIS,
    "generate_speech": TaskType.AUDIO_ANALYSIS,
    "generate_dialogue": TaskType.AUDIO_ANALYSIS,
    "extract_audio_segment": TaskType.AUDIO_ANALYSIS,

    # Document tools
    "process_document": TaskType.DOCUMENT_ANALYSIS,
    "extract_tables": TaskType.DOCUMENT_ANALYSIS,
    "summarize_document": TaskType.DOCUMENT_ANALYSIS,
    "extract_form_data": TaskType.DOCUMENT_ANALYSIS,
    "compare_documents": TaskType.DOCUMENT_ANALYSIS,
    "analyze_spreadsheet": TaskType.DOCUMENT_ANALYSIS,
    "query_document_section": TaskType.DOCUMENT_ANALYSIS,

    # Code tools
    "execute_python": TaskType.CODE,
    "calculate": TaskType.CODE,
    "analyze_data": TaskType.CODE,
    "validate_code": TaskType.CODE,
    "solve_equation": TaskType.CODE,
    "run_simulation": TaskType.CODE,
    "generate_and_test": TaskType.CODE,
    "debug_code": TaskType.CODE,

    # Web/search tools
    "web_search": TaskType.SEARCH,
    "fetch_url": TaskType.SEARCH,
    "fetch_multiple_urls": TaskType.SEARCH,
    "search_and_summarize": TaskType.SEARCH,
    "verify_claim": TaskType.SEARCH,
}


class ModelRouter:
    """
    Routes requests to the appropriate Gemini model.

    Provides automatic model selection based on task type,
    with manual override capability.
    """

    def __init__(self, default_model: GeminiModel = GeminiModel.FLASH):
        """
        Initialize the model router.

        Args:
            default_model: Default model for unspecified tasks
        """
        self.default_model = default_model
        self._override_model: Optional[GeminiModel] = None

    def get_model_for_task(self, task_type: TaskType) -> str:
        """
        Get the appropriate model ID for a task type.

        Args:
            task_type: The type of task

        Returns:
            Model ID string
        """
        if self._override_model:
            return MODEL_CONFIGS[self._override_model].model_id

        model = TASK_MODEL_MAP.get(task_type, self.default_model)
        return MODEL_CONFIGS[model].model_id

    def get_model_for_tool(self, tool_name: str) -> str:
        """
        Get the appropriate model ID for a tool.

        Args:
            tool_name: Name of the tool being used

        Returns:
            Model ID string
        """
        if self._override_model:
            return MODEL_CONFIGS[self._override_model].model_id

        task_type = TOOL_TASK_MAP.get(tool_name, TaskType.TEXT)
        return self.get_model_for_task(task_type)

    def set_override(self, model: Optional[GeminiModel]):
        """
        Set a model override for all requests.

        Args:
            model: Model to use for all requests, or None to clear
        """
        self._override_model = model

    def clear_override(self):
        """Clear any model override."""
        self._override_model = None

    def is_image_generation_task(self, tool_name: str) -> bool:
        """Check if a tool requires the image generation model."""
        task_type = TOOL_TASK_MAP.get(tool_name)
        return task_type == TaskType.IMAGE_GENERATION

    def get_model_info(self, model: GeminiModel) -> ModelConfig:
        """Get configuration info for a model."""
        return MODEL_CONFIGS[model]

    def list_models(self) -> dict:
        """List all available models with their configs."""
        return {
            model.value: {
                "description": config.description,
                "daily_quota": config.daily_quota,
                "supports_image_output": config.supports_image_output,
            }
            for model, config in MODEL_CONFIGS.items()
        }


# Global router instance
_router: Optional[ModelRouter] = None


def get_router() -> ModelRouter:
    """Get the global model router instance."""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router


def get_model_for_tool(tool_name: str) -> str:
    """
    Convenience function to get model for a tool.

    Args:
        tool_name: Name of the tool

    Returns:
        Model ID string
    """
    return get_router().get_model_for_tool(tool_name)


def get_model_for_task(task_type: TaskType) -> str:
    """
    Convenience function to get model for a task type.

    Args:
        task_type: Type of task

    Returns:
        Model ID string
    """
    return get_router().get_model_for_task(task_type)


def is_image_task(tool_name: str) -> bool:
    """Check if a tool is an image generation task."""
    return get_router().is_image_generation_task(tool_name)
