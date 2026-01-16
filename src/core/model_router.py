"""
Model Router - Automatic Model Selection Based on Task Type

Routes requests to the appropriate Gemini model based on task complexity
and quota optimization. Updated with correct model IDs for AI Pro + OAuth.

Quotas (per account, 2 accounts available):
- 3.0 Thinking: 300/day (600 total)
- 3.0 Pro: 100/day (200 total)
- 3.0 Flash: Unlimited (rate limited)
- 2.5 Pro: 100/day (200 total)
- 2.5 Flash: Unlimited (rate limited)
- 2.5 Flash-Lite: 1,500/day (3,000 total) - BEST FOR HIGH VOLUME
- Images: 1,000/day (2,000 total)
- Video (Veo 3.1): 3/day (6 total)

Routing Strategy:
- Heavy research/automation: Flash-Lite (3,000/day budget)
- Quick chat/summaries: 3.0 Flash (unlimited)
- Architecture/complex reasoning: 3.0 Pro (use sparingly)
- Large file analysis: 2.5 Pro (1M context stability)
- Image generation: gemini-3-pro-image-preview or gemini-2.5-flash-image
- Video generation: Veo 3.1 (very limited, use sparingly)
"""

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class GeminiModel(Enum):
    """Available Gemini models with their IDs."""
    # Gemini 3.0 Series (Agentic Era)
    PRO_3 = "gemini-3-pro-preview"
    FLASH_3 = "gemini-3-flash-preview"
    # Note: Thinking mode uses FLASH_3 with thinking_level="high" config

    # Gemini 2.5 Series (Stable/Production)
    PRO_25 = "gemini-2.5-pro"
    FLASH_25 = "gemini-2.5-flash"
    FLASH_LITE = "gemini-2.5-flash-lite"  # HIGH VOLUME - 1,500/day per account

    # Specialized Models
    IMAGE_PRO = "gemini-3-pro-image-preview"  # High-fidelity images
    IMAGE_FLASH = "gemini-2.5-flash-image"    # Faster image generation
    # VIDEO = "veo-3.1"  # Video generation (3/day per account)


class TaskType(Enum):
    """Task types for automatic model routing."""
    # High volume tasks -> FLASH_LITE (3,000/day total)
    RESEARCH = "research"
    AUTOMATION = "automation"
    DATA_EXTRACTION = "data_extraction"
    FORMATTING = "formatting"

    # Standard tasks -> FLASH_3 (unlimited)
    CHAT = "chat"
    SUMMARY = "summary"
    QUICK_ANSWER = "quick_answer"

    # Complex tasks -> PRO_3 (200/day total, use sparingly)
    ARCHITECTURE = "architecture"
    COMPLEX_REASONING = "complex_reasoning"
    DEBUGGING = "debugging"

    # Large context tasks -> PRO_25 (200/day total)
    LARGE_FILE_ANALYSIS = "large_file_analysis"
    CODE_REVIEW = "code_review"

    # Multimodal input tasks -> FLASH_3 or FLASH_25
    VIDEO_ANALYSIS = "video_analysis"
    AUDIO_ANALYSIS = "audio_analysis"
    DOCUMENT_ANALYSIS = "document_analysis"
    IMAGE_ANALYSIS = "image_analysis"

    # Image output tasks -> IMAGE_PRO or IMAGE_FLASH
    IMAGE_GENERATION = "image_generation"
    IMAGE_GENERATION_FAST = "image_generation_fast"

    # Video output -> VEO (very limited)
    VIDEO_GENERATION = "video_generation"


@dataclass
class ModelConfig:
    """Configuration for a model."""
    model_id: str
    description: str
    daily_quota_per_account: int  # -1 = unlimited
    supports_image_output: bool = False
    supports_video_output: bool = False
    supports_thinking: bool = False
    context_window: int = 1_000_000  # tokens


# Model configurations
MODEL_CONFIGS = {
    GeminiModel.PRO_3: ModelConfig(
        model_id="gemini-3-pro-preview",
        description="Complex reasoning, architecture, PhD-level tasks",
        daily_quota_per_account=100,
        supports_thinking=True,
        context_window=1_000_000
    ),
    GeminiModel.FLASH_3: ModelConfig(
        model_id="gemini-3-flash-preview",
        description="High-speed chat, summaries, daily driver",
        daily_quota_per_account=-1,  # Unlimited
        supports_thinking=True,  # With thinking_level="high"
        context_window=1_000_000
    ),
    GeminiModel.PRO_25: ModelConfig(
        model_id="gemini-2.5-pro",
        description="Stable, large file analysis, 1M context",
        daily_quota_per_account=100,
        context_window=1_000_000
    ),
    GeminiModel.FLASH_25: ModelConfig(
        model_id="gemini-2.5-flash",
        description="Standard balance of speed and intelligence",
        daily_quota_per_account=-1,  # Unlimited but rate limited
        context_window=1_000_000
    ),
    GeminiModel.FLASH_LITE: ModelConfig(
        model_id="gemini-2.5-flash-lite",
        description="HIGH VOLUME - formatting, extraction, automation",
        daily_quota_per_account=1500,  # 3,000 total with 2 accounts
        context_window=1_000_000
    ),
    GeminiModel.IMAGE_PRO: ModelConfig(
        model_id="gemini-3-pro-image-preview",
        description="High-fidelity images with accurate text",
        daily_quota_per_account=1000,  # 2,000 total
        supports_image_output=True
    ),
    GeminiModel.IMAGE_FLASH: ModelConfig(
        model_id="gemini-2.5-flash-image",
        description="Faster, standard image generation",
        daily_quota_per_account=1000,  # 2,000 total
        supports_image_output=True
    ),
}


# Task to model mapping - optimized for quota preservation
TASK_MODEL_MAP = {
    # High volume -> FLASH_LITE (preserve Pro quota)
    TaskType.RESEARCH: GeminiModel.FLASH_LITE,
    TaskType.AUTOMATION: GeminiModel.FLASH_LITE,
    TaskType.DATA_EXTRACTION: GeminiModel.FLASH_LITE,
    TaskType.FORMATTING: GeminiModel.FLASH_LITE,

    # Standard tasks -> FLASH_3 (unlimited, fast)
    TaskType.CHAT: GeminiModel.FLASH_3,
    TaskType.SUMMARY: GeminiModel.FLASH_3,
    TaskType.QUICK_ANSWER: GeminiModel.FLASH_3,

    # Complex tasks -> PRO_3 (use sparingly)
    TaskType.ARCHITECTURE: GeminiModel.PRO_3,
    TaskType.COMPLEX_REASONING: GeminiModel.PRO_3,
    TaskType.DEBUGGING: GeminiModel.PRO_3,

    # Large context -> PRO_25 (stable with big files)
    TaskType.LARGE_FILE_ANALYSIS: GeminiModel.PRO_25,
    TaskType.CODE_REVIEW: GeminiModel.PRO_25,

    # Multimodal input -> FLASH_3 (capable + unlimited)
    TaskType.VIDEO_ANALYSIS: GeminiModel.FLASH_3,
    TaskType.AUDIO_ANALYSIS: GeminiModel.FLASH_3,
    TaskType.DOCUMENT_ANALYSIS: GeminiModel.FLASH_3,
    TaskType.IMAGE_ANALYSIS: GeminiModel.FLASH_3,

    # Image output -> IMAGE_PRO (high quality) or IMAGE_FLASH (fast)
    TaskType.IMAGE_GENERATION: GeminiModel.IMAGE_PRO,
    TaskType.IMAGE_GENERATION_FAST: GeminiModel.IMAGE_FLASH,

    # Video output -> handled separately (Veo 3.1)
    TaskType.VIDEO_GENERATION: None,  # Special handling needed
}


# Tool name to task type mapping
TOOL_TASK_MAP = {
    # Research/spawn tools -> FLASH_LITE (high volume)
    "spawn_research": TaskType.RESEARCH,
    "spawn_single": TaskType.RESEARCH,
    "query_research": TaskType.RESEARCH,
    "store_research": TaskType.RESEARCH,
    "search_and_summarize": TaskType.RESEARCH,

    # Image generation tools -> IMAGE_PRO
    "generate_image": TaskType.IMAGE_GENERATION,

    # Image analysis tools -> FLASH_3
    "analyze_image": TaskType.IMAGE_ANALYSIS,
    "describe_for_accessibility": TaskType.IMAGE_ANALYSIS,
    "extract_text_from_image": TaskType.IMAGE_ANALYSIS,
    "detect_objects": TaskType.IMAGE_ANALYSIS,
    "compare_images": TaskType.IMAGE_ANALYSIS,

    # Video tools -> FLASH_3
    "analyze_video": TaskType.VIDEO_ANALYSIS,
    "describe_video_scene": TaskType.VIDEO_ANALYSIS,
    "extract_video_frames": TaskType.VIDEO_ANALYSIS,
    "transcribe_video": TaskType.VIDEO_ANALYSIS,
    "count_objects_in_video": TaskType.VIDEO_ANALYSIS,
    "detect_video_emotions": TaskType.VIDEO_ANALYSIS,

    # Audio tools -> FLASH_3
    "transcribe_audio": TaskType.AUDIO_ANALYSIS,
    "analyze_audio": TaskType.AUDIO_ANALYSIS,
    "translate_audio": TaskType.AUDIO_ANALYSIS,
    "generate_speech": TaskType.AUDIO_ANALYSIS,
    "generate_dialogue": TaskType.AUDIO_ANALYSIS,
    "extract_audio_segment": TaskType.AUDIO_ANALYSIS,

    # Document tools -> FLASH_3 (or PRO_25 for very large docs)
    "process_document": TaskType.DOCUMENT_ANALYSIS,
    "extract_tables": TaskType.DATA_EXTRACTION,
    "summarize_document": TaskType.SUMMARY,
    "extract_form_data": TaskType.DATA_EXTRACTION,
    "compare_documents": TaskType.DOCUMENT_ANALYSIS,
    "analyze_spreadsheet": TaskType.DOCUMENT_ANALYSIS,
    "query_document_section": TaskType.DOCUMENT_ANALYSIS,

    # Code tools -> FLASH_LITE (automation) or PRO_3 (debugging)
    "execute_python": TaskType.AUTOMATION,
    "calculate": TaskType.AUTOMATION,
    "analyze_data": TaskType.DATA_EXTRACTION,
    "validate_code": TaskType.AUTOMATION,
    "solve_equation": TaskType.AUTOMATION,
    "run_simulation": TaskType.AUTOMATION,
    "generate_and_test": TaskType.AUTOMATION,
    "debug_code": TaskType.DEBUGGING,  # Uses PRO_3

    # Web/search tools -> FLASH_LITE (high volume)
    "web_search": TaskType.RESEARCH,
    "fetch_url": TaskType.RESEARCH,
    "fetch_multiple_urls": TaskType.RESEARCH,
    "verify_claim": TaskType.RESEARCH,

    # File operations -> FLASH_LITE
    "read_file": TaskType.AUTOMATION,
    "write_file": TaskType.AUTOMATION,
    "edit_file": TaskType.AUTOMATION,
    "search_code": TaskType.RESEARCH,
    "search_files": TaskType.RESEARCH,
}


class ModelRouter:
    """
    Routes requests to the appropriate Gemini model.

    Optimizes for:
    1. Quota preservation (use Flash-Lite for high volume)
    2. Task appropriateness (Pro for complex, Flash for quick)
    3. Cost efficiency (unlimited models for frequent tasks)
    """

    def __init__(self, default_model: GeminiModel = GeminiModel.FLASH_LITE):
        """
        Initialize the model router.

        Args:
            default_model: Default model for unspecified tasks
                          (FLASH_LITE recommended for quota preservation)
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

        model = TASK_MODEL_MAP.get(task_type)
        if model is None:
            model = self.default_model

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

        task_type = TOOL_TASK_MAP.get(tool_name)
        if task_type:
            return self.get_model_for_task(task_type)

        # Default to FLASH_LITE for unknown tools (quota preservation)
        return MODEL_CONFIGS[self.default_model].model_id

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
        return task_type in (TaskType.IMAGE_GENERATION, TaskType.IMAGE_GENERATION_FAST)

    def is_video_generation_task(self, tool_name: str) -> bool:
        """Check if a tool requires video generation (very limited quota)."""
        task_type = TOOL_TASK_MAP.get(tool_name)
        return task_type == TaskType.VIDEO_GENERATION

    def get_model_info(self, model: GeminiModel) -> ModelConfig:
        """Get configuration info for a model."""
        return MODEL_CONFIGS[model]

    def list_models(self) -> dict:
        """List all available models with their configs."""
        return {
            model.value: {
                "description": config.description,
                "daily_quota_per_account": config.daily_quota_per_account,
                "supports_image_output": config.supports_image_output,
                "supports_thinking": config.supports_thinking,
            }
            for model, config in MODEL_CONFIGS.items()
        }

    def get_quota_summary(self, num_accounts: int = 2) -> dict:
        """
        Get quota summary for all models.

        Args:
            num_accounts: Number of Pro accounts (default: 2)

        Returns:
            Dict with model quotas
        """
        summary = {}
        for model, config in MODEL_CONFIGS.items():
            if config.daily_quota_per_account == -1:
                total = "Unlimited"
            else:
                total = config.daily_quota_per_account * num_accounts
            summary[model.value] = {
                "per_account": config.daily_quota_per_account,
                "total": total,
                "description": config.description
            }
        return summary


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


def is_video_task(tool_name: str) -> bool:
    """Check if a tool is a video generation task."""
    return get_router().is_video_generation_task(tool_name)
