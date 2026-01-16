"""
Batch Processor - Async Batch Operations with Rate Limiting

Handles high-volume batch operations (like generating 100 images) with:
- Async/await pattern for concurrent execution
- Semaphore-based concurrency control per model type
- Auto-retry with exponential backoff for rate limits
- Account rotation for quota distribution

Rate Limits (AI Pro + OAuth):
| Model | RPM | Concurrency |
|-------|-----|-------------|
| gemini-3-pro-preview | ~30-60 | 5 |
| gemini-3-flash-preview | ~60+ | 10 |
| gemini-3-pro-image-preview | ~5-10 | 2 |
| gemini-2.5-flash-image | ~60 | 10 |
| gemini-2.5-flash-lite | ~60 | 10 |

Usage:
    processor = BatchProcessor()

    # Single request with retry
    result = await processor.execute_with_retry(prompt, model="gemini-3-flash-preview")

    # Batch requests
    prompts = ["prompt1", "prompt2", ...]
    results = await processor.batch_execute(prompts, model="gemini-2.5-flash-lite")

    # Image batch (uses lower concurrency)
    results = await processor.batch_generate_images(prompts, output_dir="./images")
"""

import asyncio
import subprocess
import sys
import os
import random
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


# Gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"


class ModelType(Enum):
    """Model types with their concurrency limits."""
    PRO = "pro"           # Low concurrency (5)
    FLASH = "flash"       # High concurrency (10)
    IMAGE_PRO = "image_pro"   # Very low concurrency (2)
    IMAGE_FLASH = "image_flash"  # Standard concurrency (10)


# Model ID to type mapping
MODEL_TYPE_MAP = {
    "gemini-3-pro-preview": ModelType.PRO,
    "gemini-2.5-pro": ModelType.PRO,
    "gemini-3-flash-preview": ModelType.FLASH,
    "gemini-2.5-flash": ModelType.FLASH,
    "gemini-2.5-flash-lite": ModelType.FLASH,
    "gemini-3-pro-image-preview": ModelType.IMAGE_PRO,
    "gemini-2.5-flash-image": ModelType.IMAGE_FLASH,
}

# Concurrency limits per model type
CONCURRENCY_LIMITS = {
    ModelType.PRO: 5,
    ModelType.FLASH: 10,
    ModelType.IMAGE_PRO: 2,
    ModelType.IMAGE_FLASH: 10,
}


@dataclass
class BatchResult:
    """Result from a batch operation."""
    index: int
    success: bool
    result: str
    prompt: str
    attempts: int
    account_used: int


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_delay: float = 2.0
    max_delay: float = 30.0
    jitter: float = 0.5  # Random jitter factor


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


def is_rate_limited(response: str) -> bool:
    """Check if response indicates rate limiting."""
    rate_limit_indicators = [
        "429",
        "Resource Exhausted",
        "RESOURCE_EXHAUSTED",
        "rate limit",
        "quota exceeded",
        "Too Many Requests",
    ]
    response_lower = response.lower()
    for indicator in rate_limit_indicators:
        if indicator.lower() in response_lower:
            return True
    return False


class BatchProcessor:
    """
    Async batch processor for Gemini requests.

    Handles concurrent execution with rate limiting and retry logic.
    """

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        default_model: str = "gemini-2.5-flash-lite"
    ):
        """
        Initialize the batch processor.

        Args:
            retry_config: Configuration for retry behavior
            default_model: Default model to use
        """
        self.retry_config = retry_config or RetryConfig()
        self.default_model = default_model
        self._semaphores: Dict[ModelType, asyncio.Semaphore] = {}
        self._account_counter = 0

    def _get_semaphore(self, model: str) -> asyncio.Semaphore:
        """Get or create a semaphore for the given model."""
        model_type = MODEL_TYPE_MAP.get(model, ModelType.FLASH)

        if model_type not in self._semaphores:
            limit = CONCURRENCY_LIMITS[model_type]
            self._semaphores[model_type] = asyncio.Semaphore(limit)

        return self._semaphores[model_type]

    def _get_next_account(self) -> int:
        """Get next account using round-robin."""
        self._account_counter += 1
        return (self._account_counter % 2) + 1

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        base = self.retry_config.base_delay * (2 ** attempt)
        delay = min(base, self.retry_config.max_delay)

        # Add jitter
        jitter_range = delay * self.retry_config.jitter
        delay += random.uniform(-jitter_range, jitter_range)

        return max(0.1, delay)

    async def _call_gemini_async(
        self,
        query: str,
        account: int,
        model: str,
        timeout: int = 120
    ) -> Tuple[bool, str]:
        """
        Call Gemini asynchronously using subprocess (safe, no shell injection).

        Args:
            query: The prompt to send
            account: Account number (1 or 2)
            model: Model ID
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, response)
        """
        if not GEMINI_SCRIPT.exists():
            return False, f"gemini-account.sh not found at {GEMINI_SCRIPT}"

        try:
            if sys.platform == 'win32':
                git_bash = get_git_bash()
                if not git_bash:
                    return False, "Git Bash not found"
                cmd = [str(git_bash), str(GEMINI_SCRIPT), str(account), query, model]
            else:
                cmd = ["bash", str(GEMINI_SCRIPT), str(account), query, model]

            # Run subprocess asynchronously using create_subprocess_exec
            # This is safe - no shell interpolation, arguments passed as list
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd()
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return False, "Timeout"

            if proc.returncode != 0:
                error = stderr.decode().strip() if stderr else "Unknown error"
                return False, f"Error: {error}"

            response = stdout.decode().strip()
            return bool(response), response or "Empty response"

        except Exception as e:
            return False, f"Error: {e}"

    async def execute_with_retry(
        self,
        prompt: str,
        model: Optional[str] = None,
        account: Optional[int] = None,
        timeout: int = 120
    ) -> Tuple[bool, str, int]:
        """
        Execute a single request with retry logic.

        Args:
            prompt: The prompt to send
            model: Model ID (uses default if not specified)
            account: Account to use (rotates if not specified)
            timeout: Request timeout in seconds

        Returns:
            Tuple of (success, response, attempts)
        """
        model = model or self.default_model
        semaphore = self._get_semaphore(model)

        async with semaphore:
            for attempt in range(self.retry_config.max_retries):
                current_account = account or self._get_next_account()

                success, response = await self._call_gemini_async(
                    prompt, current_account, model, timeout
                )

                if success and not is_rate_limited(response):
                    return True, response, attempt + 1

                if is_rate_limited(response):
                    if attempt < self.retry_config.max_retries - 1:
                        delay = self._calculate_delay(attempt)
                        await asyncio.sleep(delay)
                        # Try alternate account on retry
                        if account is None:
                            current_account = 3 - current_account
                    continue
                else:
                    # Non-rate-limit error, return immediately
                    return False, response, attempt + 1

            return False, f"Max retries ({self.retry_config.max_retries}) exceeded. Last: {response}", self.retry_config.max_retries

    async def batch_execute(
        self,
        prompts: List[str],
        model: Optional[str] = None,
        timeout: int = 120,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[BatchResult]:
        """
        Execute multiple prompts concurrently with rate limiting.

        Args:
            prompts: List of prompts to execute
            model: Model ID (uses default if not specified)
            timeout: Request timeout per prompt
            progress_callback: Optional callback(completed, total) for progress updates

        Returns:
            List of BatchResult objects
        """
        model = model or self.default_model
        results: List[BatchResult] = []
        completed = 0

        async def process_one(index: int, prompt: str) -> BatchResult:
            nonlocal completed
            account = (index % 2) + 1  # Distribute across accounts

            success, response, attempts = await self.execute_with_retry(
                prompt, model, account, timeout
            )

            completed += 1
            if progress_callback:
                progress_callback(completed, len(prompts))

            return BatchResult(
                index=index,
                success=success,
                result=response,
                prompt=prompt,
                attempts=attempts,
                account_used=account
            )

        # Create tasks for all prompts
        tasks = [
            process_one(i, prompt)
            for i, prompt in enumerate(prompts)
        ]

        # Execute all tasks concurrently (semaphore limits actual concurrency)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle any exceptions
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(BatchResult(
                    index=i,
                    success=False,
                    result=str(result),
                    prompt=prompts[i],
                    attempts=0,
                    account_used=0
                ))
            else:
                final_results.append(result)

        return sorted(final_results, key=lambda r: r.index)

    async def batch_generate_images(
        self,
        prompts: List[str],
        output_dir: str = "./generated_images",
        aspect_ratio: str = "1:1",
        high_quality: bool = True,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> List[BatchResult]:
        """
        Generate multiple images concurrently.

        Uses appropriate image model and lower concurrency limits.

        Args:
            prompts: List of image generation prompts
            output_dir: Directory to save generated images
            aspect_ratio: Aspect ratio for images
            high_quality: Use gemini-3-pro-image-preview (True) or gemini-2.5-flash-image (False)
            progress_callback: Optional callback for progress updates

        Returns:
            List of BatchResult objects
        """
        model = "gemini-3-pro-image-preview" if high_quality else "gemini-2.5-flash-image"

        # Ensure output directory exists
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Build full prompts with image generation instructions
        full_prompts = [
            f"Generate an image: {prompt}\nAspect ratio: {aspect_ratio}\nReturn high-quality image."
            for prompt in prompts
        ]

        return await self.batch_execute(
            full_prompts,
            model=model,
            timeout=180,  # Longer timeout for image generation
            progress_callback=progress_callback
        )


# Convenience functions for synchronous usage

def run_batch(
    prompts: List[str],
    model: str = "gemini-2.5-flash-lite",
    timeout: int = 120
) -> List[BatchResult]:
    """
    Synchronous wrapper for batch execution.

    Args:
        prompts: List of prompts
        model: Model ID
        timeout: Timeout per request

    Returns:
        List of BatchResult objects
    """
    processor = BatchProcessor(default_model=model)
    return asyncio.run(processor.batch_execute(prompts, model, timeout))


def run_single_with_retry(
    prompt: str,
    model: str = "gemini-2.5-flash-lite",
    timeout: int = 120
) -> Tuple[bool, str]:
    """
    Synchronous wrapper for single request with retry.

    Args:
        prompt: The prompt
        model: Model ID
        timeout: Timeout

    Returns:
        Tuple of (success, response)
    """
    processor = BatchProcessor(default_model=model)
    success, response, _ = asyncio.run(
        processor.execute_with_retry(prompt, model, timeout=timeout)
    )
    return success, response
