"""
Real-Time Streaming

Enables streaming responses as they generate rather than waiting for completion:
- Character-by-character display for interactive experience
- Progress indicators for long operations
- Stream handling from subprocess output
- Buffer management for tool call detection
- Graceful interruption support

This makes the CLI feel more responsive and interactive.
"""

import sys
import time
import subprocess
import threading
import queue
from pathlib import Path
from typing import Optional, Generator, Callable, Tuple
from dataclasses import dataclass


@dataclass
class StreamConfig:
    """Configuration for streaming behavior."""
    char_delay: float = 0.01  # Delay between characters (seconds)
    word_delay: float = 0.05  # Delay between words
    line_delay: float = 0.1   # Delay between lines
    buffer_size: int = 1024   # Read buffer size
    progress_chars: str = "⣾⣽⣻⢿⡿⣟⣯⣷"  # Spinning progress indicator
    show_progress: bool = True


class StreamBuffer:
    """
    Buffer that accumulates streamed content while allowing partial reads.

    Used to detect tool calls before the response is complete.
    """

    def __init__(self):
        self.content = ""
        self.position = 0
        self._lock = threading.Lock()

    def append(self, text: str):
        """Append text to the buffer."""
        with self._lock:
            self.content += text

    def read_new(self) -> str:
        """Read content added since last read."""
        with self._lock:
            new_content = self.content[self.position:]
            self.position = len(self.content)
            return new_content

    def peek_all(self) -> str:
        """Peek at all content without advancing position."""
        with self._lock:
            return self.content

    def reset(self):
        """Reset buffer and position."""
        with self._lock:
            self.content = ""
            self.position = 0

    def contains_tool_call(self) -> bool:
        """Check if buffer contains a tool call marker."""
        with self._lock:
            return "TOOL_CALL:" in self.content


class ProgressIndicator:
    """Displays a progress indicator during long operations."""

    def __init__(self, message: str = "Processing", chars: str = "⣾⣽⣻⢿⡿⣟⣯⣷"):
        self.message = message
        self.chars = chars
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._index = 0

    def start(self):
        """Start the progress indicator."""
        self.running = True
        self.thread = threading.Thread(target=self._spin, daemon=True)
        self.thread.start()

    def stop(self, clear: bool = True):
        """Stop the progress indicator."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=0.5)
        if clear:
            # Clear the progress line
            sys.stdout.write('\r' + ' ' * (len(self.message) + 10) + '\r')
            sys.stdout.flush()

    def _spin(self):
        """Spin the progress indicator."""
        while self.running:
            char = self.chars[self._index % len(self.chars)]
            sys.stdout.write(f'\r{self.message} {char}')
            sys.stdout.flush()
            self._index += 1
            time.sleep(0.1)


def stream_text(
    text: str,
    config: StreamConfig = None,
    on_char: Callable[[str], None] = None
) -> None:
    """
    Stream text to stdout with configurable delays.

    Args:
        text: Text to stream
        config: Streaming configuration
        on_char: Optional callback for each character
    """
    config = config or StreamConfig()

    for i, char in enumerate(text):
        sys.stdout.write(char)
        sys.stdout.flush()

        if on_char:
            on_char(char)

        # Variable delay based on character type
        if char == '\n':
            time.sleep(config.line_delay)
        elif char == ' ':
            time.sleep(config.word_delay)
        else:
            time.sleep(config.char_delay)


def stream_from_process(
    process: subprocess.Popen,
    config: StreamConfig = None,
    on_chunk: Callable[[str], None] = None,
    stop_event: threading.Event = None
) -> Generator[str, None, None]:
    """
    Stream output from a subprocess.

    Args:
        process: Running subprocess with stdout pipe
        config: Streaming configuration
        on_chunk: Optional callback for each chunk
        stop_event: Optional event to signal stop

    Yields:
        Chunks of text as they become available
    """
    config = config or StreamConfig()

    while True:
        if stop_event and stop_event.is_set():
            break

        # Check if process has finished
        if process.poll() is not None:
            # Read any remaining output
            remaining = process.stdout.read()
            if remaining:
                yield remaining
                if on_chunk:
                    on_chunk(remaining)
            break

        # Try to read available data
        try:
            chunk = process.stdout.read(config.buffer_size)
            if chunk:
                yield chunk
                if on_chunk:
                    on_chunk(chunk)
        except Exception:
            break


class StreamingGeminiCaller:
    """
    Calls Gemini with streaming output support.

    Note: True streaming requires the Gemini API to support it.
    This implementation simulates streaming by reading subprocess
    output in chunks.
    """

    def __init__(
        self,
        gemini_script: str,
        config: StreamConfig = None
    ):
        """
        Initialize the streaming caller.

        Args:
            gemini_script: Path to gemini-account.sh
            config: Streaming configuration
        """
        self.gemini_script = gemini_script
        self.config = config or StreamConfig()
        self.current_process: Optional[subprocess.Popen] = None
        self.stop_event = threading.Event()

    def call_streaming(
        self,
        prompt: str,
        account: int = 1,
        on_token: Callable[[str], None] = None,
        show_progress: bool = True
    ) -> Tuple[str, bool]:
        """
        Call Gemini and stream the response.

        Args:
            prompt: The prompt to send
            account: Account number (1 or 2)
            on_token: Callback for each token/chunk
            show_progress: Whether to show progress indicator

        Returns:
            Tuple of (full_response, was_interrupted)
        """
        self.stop_event.clear()

        # Find Git Bash on Windows
        if sys.platform == 'win32':
            git_bash = Path("C:/Program Files/Git/usr/bin/bash.exe")
            if not git_bash.exists():
                git_bash = Path("C:/Program Files/Git/bin/bash.exe")
            if not git_bash.exists():
                return "Error: Git Bash not found", False
            cmd = [str(git_bash), self.gemini_script, str(account), prompt]
        else:
            cmd = ["bash", self.gemini_script, str(account), prompt]

        # Show progress indicator while waiting for first response
        progress = None
        if show_progress and self.config.show_progress:
            progress = ProgressIndicator("Thinking")
            progress.start()

        try:
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  # Line buffered
            )

            buffer = StreamBuffer()
            first_output = True

            for chunk in stream_from_process(
                self.current_process,
                self.config,
                stop_event=self.stop_event
            ):
                # Stop progress on first output
                if first_output and progress:
                    progress.stop()
                    first_output = False

                buffer.append(chunk)

                # Stream to stdout
                if on_token:
                    on_token(chunk)
                else:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()

            # Get any stderr
            stderr = self.current_process.stderr.read()
            if stderr and self.current_process.returncode != 0:
                return f"Error: {stderr}", False

            return buffer.peek_all(), self.stop_event.is_set()

        except Exception as e:
            if progress:
                progress.stop()
            return f"Error: {e}", False

        finally:
            if progress:
                progress.stop(clear=True)
            self.current_process = None

    def interrupt(self):
        """Interrupt the current streaming call."""
        self.stop_event.set()
        if self.current_process:
            try:
                self.current_process.terminate()
            except Exception:
                pass


class StreamingOrchestrator:
    """
    Mixin for the Orchestrator to add streaming support.

    Usage:
        class Orchestrator(StreamingOrchestrator):
            ...
    """

    def __init__(self):
        self.streaming_enabled = True
        self.streaming_config = StreamConfig()
        self._streaming_caller: Optional[StreamingGeminiCaller] = None

    def enable_streaming(self, enabled: bool = True):
        """Enable or disable streaming output."""
        self.streaming_enabled = enabled

    def set_streaming_config(self, config: StreamConfig):
        """Set streaming configuration."""
        self.streaming_config = config

    def _get_streaming_caller(self) -> StreamingGeminiCaller:
        """Get or create streaming caller."""
        if self._streaming_caller is None:
            self._streaming_caller = StreamingGeminiCaller(
                self.gemini_script,
                self.streaming_config
            )
        return self._streaming_caller

    def call_gemini_streaming(
        self,
        prompt: str,
        account: int = None,
        on_token: Callable[[str], None] = None
    ) -> str:
        """
        Call Gemini with streaming output.

        Args:
            prompt: Prompt to send
            account: Account number (optional, uses rotation if not specified)
            on_token: Optional callback for each token

        Returns:
            Full response text
        """
        if not self.streaming_enabled:
            # Fall back to non-streaming
            return self._call_gemini(prompt, account)

        acc = account or self._get_account()
        caller = self._get_streaming_caller()

        response, interrupted = caller.call_streaming(
            prompt,
            account=acc,
            on_token=on_token,
            show_progress=self.streaming_config.show_progress
        )

        if interrupted:
            return response + "\n[Interrupted by user]"

        return response


def create_typing_effect(
    text: str,
    speed: str = "normal"
) -> Generator[str, None, None]:
    """
    Create a typing effect generator.

    Args:
        text: Text to type out
        speed: "slow", "normal", or "fast"

    Yields:
        Characters with appropriate timing
    """
    speeds = {
        "slow": (0.05, 0.1, 0.2),
        "normal": (0.02, 0.05, 0.1),
        "fast": (0.005, 0.01, 0.02)
    }

    char_delay, word_delay, line_delay = speeds.get(speed, speeds["normal"])

    for char in text:
        yield char

        if char == '\n':
            time.sleep(line_delay)
        elif char == ' ':
            time.sleep(word_delay)
        else:
            time.sleep(char_delay)


def display_with_typing(text: str, speed: str = "normal"):
    """Display text with typing effect."""
    for char in create_typing_effect(text, speed):
        sys.stdout.write(char)
        sys.stdout.flush()
    print()  # Final newline


# Progress bar utilities
def progress_bar(
    current: int,
    total: int,
    width: int = 40,
    prefix: str = "",
    suffix: str = ""
) -> str:
    """Generate a progress bar string."""
    percent = current / total if total > 0 else 0
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)
    return f"{prefix}|{bar}| {percent:.1%} {suffix}"


def display_progress(
    current: int,
    total: int,
    prefix: str = "Progress",
    suffix: str = ""
):
    """Display an updating progress bar."""
    bar = progress_bar(current, total, prefix=prefix, suffix=suffix)
    sys.stdout.write(f'\r{bar}')
    sys.stdout.flush()
    if current >= total:
        print()  # Newline when complete
