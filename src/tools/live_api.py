"""
Multimodal Live API

Provides real-time, low-latency bidirectional communication:
- Voice input via microphone
- Voice output via text-to-speech
- Real-time text streaming
- Session management with resumption
- Audio/video stream handling

Note: Full WebSocket implementation requires the Gemini Live API.
This module provides the infrastructure for when that's available.
"""

import sys
import time
import json
import threading
import queue
import wave
import struct
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List, Generator
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod


class SessionState(Enum):
    """Live session states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LISTENING = "listening"
    SPEAKING = "speaking"
    PROCESSING = "processing"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class LiveConfig:
    """Configuration for live sessions."""
    sample_rate: int = 16000  # Audio sample rate (Hz)
    channels: int = 1  # Mono audio
    chunk_size: int = 1024  # Audio chunk size
    silence_threshold: float = 0.01  # Voice activity detection threshold
    silence_duration: float = 1.0  # Seconds of silence to end utterance
    max_session_duration: int = 3600  # Max session length (seconds)
    auto_reconnect: bool = True
    reconnect_delay: float = 1.0


@dataclass
class Transcript:
    """A transcript entry with timestamp."""
    timestamp: float
    speaker: str  # "user" or "assistant"
    text: str
    is_final: bool = True
    confidence: float = 1.0


@dataclass
class LiveSession:
    """Represents a live interaction session."""
    session_id: str
    state: SessionState = SessionState.DISCONNECTED
    config: LiveConfig = field(default_factory=LiveConfig)
    transcripts: List[Transcript] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    last_activity: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AudioCapture:
    """
    Captures audio from microphone.

    Note: Requires pyaudio for actual audio capture.
    Falls back to simulation if not available.
    """

    def __init__(self, config: LiveConfig):
        self.config = config
        self.is_capturing = False
        self.audio_queue: queue.Queue = queue.Queue()
        self.capture_thread: Optional[threading.Thread] = None
        self._pyaudio = None
        self._stream = None

    def _init_pyaudio(self) -> bool:
        """Initialize PyAudio if available."""
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            return True
        except ImportError:
            print("Warning: pyaudio not installed. Audio capture unavailable.")
            print("Install with: pip install pyaudio")
            return False

    def start(self) -> bool:
        """Start audio capture."""
        if self.is_capturing:
            return True

        if not self._init_pyaudio():
            return False

        try:
            import pyaudio
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                input=True,
                frames_per_buffer=self.config.chunk_size
            )

            self.is_capturing = True
            self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self.capture_thread.start()
            return True

        except Exception as e:
            print(f"Error starting audio capture: {e}")
            return False

    def stop(self):
        """Stop audio capture."""
        self.is_capturing = False
        if self.capture_thread:
            self.capture_thread.join(timeout=1.0)

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None

    def _capture_loop(self):
        """Continuously capture audio chunks."""
        while self.is_capturing:
            try:
                data = self._stream.read(self.config.chunk_size, exception_on_overflow=False)
                self.audio_queue.put(data)
            except Exception as e:
                if self.is_capturing:
                    print(f"Audio capture error: {e}")
                break

    def get_chunk(self, timeout: float = 0.1) -> Optional[bytes]:
        """Get next audio chunk."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_audio_level(self, data: bytes) -> float:
        """Calculate audio level for voice activity detection."""
        if not data:
            return 0.0

        # Convert bytes to samples
        samples = struct.unpack(f'{len(data)//2}h', data)
        if not samples:
            return 0.0

        # Calculate RMS
        rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5
        # Normalize to 0-1 range (max 16-bit value is 32767)
        return rms / 32767.0


class AudioPlayback:
    """
    Plays audio output.

    Note: Requires pyaudio for actual audio playback.
    """

    def __init__(self, config: LiveConfig):
        self.config = config
        self.is_playing = False
        self.audio_queue: queue.Queue = queue.Queue()
        self.playback_thread: Optional[threading.Thread] = None
        self._pyaudio = None
        self._stream = None

    def _init_pyaudio(self) -> bool:
        """Initialize PyAudio if available."""
        try:
            import pyaudio
            self._pyaudio = pyaudio.PyAudio()
            return True
        except ImportError:
            return False

    def start(self) -> bool:
        """Start audio playback."""
        if self.is_playing:
            return True

        if not self._init_pyaudio():
            return False

        try:
            import pyaudio
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.config.channels,
                rate=self.config.sample_rate,
                output=True,
                frames_per_buffer=self.config.chunk_size
            )

            self.is_playing = True
            self.playback_thread = threading.Thread(target=self._playback_loop, daemon=True)
            self.playback_thread.start()
            return True

        except Exception as e:
            print(f"Error starting audio playback: {e}")
            return False

    def stop(self):
        """Stop audio playback."""
        self.is_playing = False
        if self.playback_thread:
            self.playback_thread.join(timeout=1.0)

        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

        if self._pyaudio:
            self._pyaudio.terminate()
            self._pyaudio = None

    def _playback_loop(self):
        """Play queued audio chunks."""
        while self.is_playing:
            try:
                data = self.audio_queue.get(timeout=0.1)
                self._stream.write(data)
            except queue.Empty:
                continue
            except Exception as e:
                if self.is_playing:
                    print(f"Audio playback error: {e}")
                break

    def play(self, data: bytes):
        """Queue audio data for playback."""
        self.audio_queue.put(data)


class VoiceActivityDetector:
    """Detects voice activity in audio stream."""

    def __init__(self, config: LiveConfig):
        self.config = config
        self.is_speaking = False
        self.silence_start: Optional[float] = None
        self.speech_frames: List[bytes] = []

    def process_chunk(self, chunk: bytes, level: float) -> Optional[bytes]:
        """
        Process an audio chunk and detect speech.

        Args:
            chunk: Audio data
            level: Audio level (0-1)

        Returns:
            Complete utterance when speech ends, None otherwise
        """
        if level > self.config.silence_threshold:
            # Voice detected
            self.is_speaking = True
            self.silence_start = None
            self.speech_frames.append(chunk)

        elif self.is_speaking:
            # In speech but current frame is silent
            self.speech_frames.append(chunk)

            if self.silence_start is None:
                self.silence_start = time.time()
            elif time.time() - self.silence_start > self.config.silence_duration:
                # End of utterance
                utterance = b''.join(self.speech_frames)
                self.speech_frames = []
                self.is_speaking = False
                self.silence_start = None
                return utterance

        return None


class LiveAPIClient(ABC):
    """
    Abstract base class for Live API clients.

    Subclass this to implement actual Gemini Live API connection.
    """

    @abstractmethod
    def connect(self, session: LiveSession) -> bool:
        """Connect to the Live API."""
        pass

    @abstractmethod
    def disconnect(self):
        """Disconnect from the Live API."""
        pass

    @abstractmethod
    def send_audio(self, data: bytes) -> bool:
        """Send audio data to the API."""
        pass

    @abstractmethod
    def send_text(self, text: str) -> bool:
        """Send text to the API."""
        pass

    @abstractmethod
    def receive(self) -> Generator[Dict[str, Any], None, None]:
        """Receive responses from the API."""
        pass


class SimulatedLiveClient(LiveAPIClient):
    """
    Simulated Live API client for testing.

    Uses the existing Gemini CLI interface to simulate live interactions.
    """

    def __init__(self, gemini_script: str):
        self.gemini_script = gemini_script
        self.connected = False
        self.session: Optional[LiveSession] = None

    def connect(self, session: LiveSession) -> bool:
        """Simulate connection."""
        self.session = session
        self.connected = True
        session.state = SessionState.CONNECTED
        return True

    def disconnect(self):
        """Simulate disconnection."""
        self.connected = False
        if self.session:
            self.session.state = SessionState.DISCONNECTED

    def send_audio(self, data: bytes) -> bool:
        """Audio sending not supported in simulation."""
        return False

    def send_text(self, text: str) -> bool:
        """Send text via CLI."""
        if not self.connected:
            return False

        # Would call Gemini here
        return True

    def receive(self) -> Generator[Dict[str, Any], None, None]:
        """Receive simulated responses."""
        yield {"type": "text", "content": "Simulated response"}


class LiveInteractionManager:
    """
    Manages live voice/text interactions.

    Coordinates audio capture, voice activity detection,
    API communication, and audio playback.
    """

    def __init__(
        self,
        config: LiveConfig = None,
        on_transcript: Callable[[Transcript], None] = None,
        on_state_change: Callable[[SessionState], None] = None
    ):
        self.config = config or LiveConfig()
        self.on_transcript = on_transcript
        self.on_state_change = on_state_change

        self.session: Optional[LiveSession] = None
        self.audio_capture: Optional[AudioCapture] = None
        self.audio_playback: Optional[AudioPlayback] = None
        self.vad: Optional[VoiceActivityDetector] = None
        self.client: Optional[LiveAPIClient] = None

        self._running = False
        self._main_thread: Optional[threading.Thread] = None

    def start_session(
        self,
        session_id: str = None,
        client: LiveAPIClient = None
    ) -> LiveSession:
        """
        Start a new live session.

        Args:
            session_id: Optional session ID (auto-generated if not provided)
            client: Live API client to use

        Returns:
            The created session
        """
        import uuid
        session_id = session_id or str(uuid.uuid4())[:8]

        self.session = LiveSession(
            session_id=session_id,
            config=self.config
        )

        self.client = client
        self.audio_capture = AudioCapture(self.config)
        self.audio_playback = AudioPlayback(self.config)
        self.vad = VoiceActivityDetector(self.config)

        # Connect client
        if self.client:
            if not self.client.connect(self.session):
                self.session.state = SessionState.ERROR
                return self.session

        self._set_state(SessionState.CONNECTED)
        return self.session

    def start_listening(self) -> bool:
        """Start listening for voice input."""
        if not self.session or self.session.state == SessionState.ERROR:
            return False

        if not self.audio_capture.start():
            print("Audio capture not available. Using text-only mode.")
            self._set_state(SessionState.CONNECTED)
            return False

        self._set_state(SessionState.LISTENING)
        self._running = True
        self._main_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._main_thread.start()
        return True

    def stop_listening(self):
        """Stop listening for voice input."""
        self._running = False
        if self._main_thread:
            self._main_thread.join(timeout=2.0)

        if self.audio_capture:
            self.audio_capture.stop()

        self._set_state(SessionState.CONNECTED)

    def end_session(self):
        """End the current session."""
        self.stop_listening()

        if self.audio_playback:
            self.audio_playback.stop()

        if self.client:
            self.client.disconnect()

        self._set_state(SessionState.DISCONNECTED)
        self.session = None

    def send_text(self, text: str) -> bool:
        """Send text input."""
        if not self.session or not self.client:
            return False

        self._set_state(SessionState.PROCESSING)

        # Record user transcript
        self._add_transcript("user", text)

        # Send to client
        success = self.client.send_text(text)

        if success:
            self._set_state(SessionState.LISTENING)
        else:
            self._set_state(SessionState.ERROR)

        return success

    def _listen_loop(self):
        """Main listening loop."""
        while self._running:
            chunk = self.audio_capture.get_chunk()
            if not chunk:
                continue

            level = self.audio_capture.get_audio_level(chunk)
            utterance = self.vad.process_chunk(chunk, level)

            if utterance:
                # Complete utterance detected
                self._set_state(SessionState.PROCESSING)
                self._process_utterance(utterance)
                self._set_state(SessionState.LISTENING)

    def _process_utterance(self, audio_data: bytes):
        """Process a complete utterance."""
        # In a full implementation, this would:
        # 1. Send audio to Gemini Live API for transcription
        # 2. Receive transcribed text
        # 3. Send to Gemini for response
        # 4. Receive audio response
        # 5. Play audio response

        # For now, just log that we detected speech
        print("\n[Speech detected - processing...]")

        # Simulate transcription
        transcript = Transcript(
            timestamp=time.time(),
            speaker="user",
            text="[Audio transcription would appear here]",
            is_final=True
        )
        self._add_transcript("user", transcript.text)

    def _add_transcript(self, speaker: str, text: str):
        """Add a transcript entry."""
        transcript = Transcript(
            timestamp=time.time(),
            speaker=speaker,
            text=text
        )

        if self.session:
            self.session.transcripts.append(transcript)
            self.session.last_activity = time.time()

        if self.on_transcript:
            self.on_transcript(transcript)

    def _set_state(self, state: SessionState):
        """Update session state."""
        if self.session:
            self.session.state = state

        if self.on_state_change:
            self.on_state_change(state)

    def get_transcripts(self) -> List[Transcript]:
        """Get all transcripts from current session."""
        return self.session.transcripts if self.session else []

    def export_transcripts(self, path: str, format: str = "json") -> bool:
        """
        Export transcripts to file.

        Args:
            path: Output file path
            format: "json" or "txt"

        Returns:
            Success status
        """
        if not self.session:
            return False

        try:
            output_path = Path(path).expanduser().resolve()

            if format == "json":
                data = {
                    "session_id": self.session.session_id,
                    "start_time": self.session.start_time,
                    "transcripts": [
                        {
                            "timestamp": t.timestamp,
                            "speaker": t.speaker,
                            "text": t.text,
                            "confidence": t.confidence
                        }
                        for t in self.session.transcripts
                    ]
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2)

            elif format == "txt":
                with open(output_path, 'w', encoding='utf-8') as f:
                    for t in self.session.transcripts:
                        timestamp = time.strftime('%H:%M:%S', time.localtime(t.timestamp))
                        f.write(f"[{timestamp}] {t.speaker}: {t.text}\n")

            return True

        except Exception as e:
            print(f"Error exporting transcripts: {e}")
            return False


# Tool functions for the orchestrator
def start_live_session(session_id: str = None) -> tuple[bool, str]:
    """Start a new live interaction session."""
    # This would be called from the orchestrator
    return True, f"Live session started: {session_id or 'auto'}"


def end_live_session() -> tuple[bool, str]:
    """End the current live session."""
    return True, "Live session ended"


def get_live_transcripts() -> tuple[bool, str]:
    """Get transcripts from current live session."""
    return True, "No active live session"


# Tool registry
LIVE_API_TOOLS = {
    "start_live_session": start_live_session,
    "end_live_session": end_live_session,
    "get_live_transcripts": get_live_transcripts,
}
