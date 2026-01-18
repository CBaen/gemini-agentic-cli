"""
Orchestrator - The Core Agent Loop

This is the beating heart of the Gemini Agentic CLI.
It coordinates: user input → Gemini → tool execution → response display.

Phase 4 Complete - Full multimodal and experimental capabilities:
- Security layer integration (sandboxing, whitelisting)
- Confirmation prompts for destructive operations
- Extended tool registry (60+ tools)
- Session lifecycle management
- Audit logging
- Video, audio, document, web, code execution capabilities
- Custom tool loading via YAML
- Jupyter notebook support
- Live API infrastructure (voice/video)
- Self-correction loops
- Real-time streaming
- IDE integration server

Flow:
    1. User provides input
    2. Orchestrator builds prompt with history + system instructions
    3. Calls Gemini via gemini-account.sh
    4. Parses tool calls from response
    5. Security check on tool calls
    6. Request confirmation if needed
    7. Executes tools, feeds results back to Gemini
    8. Loops until Gemini responds without tool calls
    9. Displays final response, saves history
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional, Callable

from .tool_protocol import (
    ToolCall, ToolResult,
    parse_tool_calls, contains_tool_call,
    format_tool_result, build_system_prompt
)
from .memory import (
    load_history, save_history,
    add_user_message, add_assistant_message, add_tool_result,
    format_history_for_prompt
)


class Orchestrator:
    """
    The main orchestration engine for the Gemini Agentic CLI.

    Manages:
        - Conversation flow
        - Gemini API calls (via shell)
        - Tool execution with security checks
        - Account rotation
        - Session lifecycle
    """

    def __init__(
        self,
        history: Optional[list] = None,
        gemini_script: Optional[str] = None,
        project_root: Optional[str] = None,
        security_enabled: bool = True
    ):
        """
        Initialize the orchestrator.

        Args:
            history: Optional pre-loaded conversation history
            gemini_script: Path to gemini-account.sh (auto-detected if not provided)
            project_root: Root directory for sandboxing (defaults to cwd)
            security_enabled: Whether to enforce security checks
        """
        self.history = history if history is not None else []
        self.turn_count = 0
        self.security_enabled = security_enabled
        self.project_root = Path(project_root or os.getcwd()).resolve()

        # Initialize security layer
        if security_enabled:
            try:
                from integrations.security import initialize_security, set_confirmation_callback
                initialize_security(str(self.project_root))
                set_confirmation_callback(self._request_user_confirmation)
            except ImportError:
                print("Warning: Security module not available")

        # Initialize audit logging
        try:
            from integrations.audit import log_session_start
            log_session_start(str(self.project_root))
        except ImportError:
            pass  # Audit logging optional

        # Find gemini-account.sh
        if gemini_script:
            self.gemini_script = gemini_script
        else:
            default_path = Path.home() / ".claude" / "scripts" / "gemini-account.sh"
            if default_path.exists():
                self.gemini_script = str(default_path)
            else:
                self.gemini_script = None

        # Build tool registry
        self.tool_registry = self._build_tool_registry()

        # System prompt (built with available tools)
        self.system_prompt = build_system_prompt(self.tool_registry)

    def _build_tool_registry(self) -> dict[str, Callable]:
        """Build the registry of available tools."""
        registry = {}

        # Core filesystem tools
        try:
            from tools.filesystem import (
                read_file, write_file, edit_file, delete_file,
                delete_directory, create_directory, move_file, copy_file,
                list_directory
            )
            registry.update({
                "read_file": read_file,
                "write_file": write_file,
                "edit_file": edit_file,
                "delete_file": delete_file,
                "delete_directory": delete_directory,
                "create_directory": create_directory,
                "move_file": move_file,
                "copy_file": copy_file,
                "list_directory": list_directory,
            })
        except ImportError as e:
            print(f"Warning: Filesystem tools not available: {e}")

        # Shell tools
        try:
            from tools.shell import run_command
            registry["run_command"] = run_command
        except ImportError as e:
            print(f"Warning: Shell tools not available: {e}")

        # Search tools (Phase 2)
        try:
            from tools.search import search_code, search_files, grep_count
            registry.update({
                "search_code": search_code,
                "search_files": search_files,
                "grep_count": grep_count,
            })
        except ImportError:
            pass  # Optional tools

        # Qdrant tools (Phase 2)
        try:
            from integrations.qdrant_client import query_research, store_research
            registry.update({
                "query_research": query_research,
                "store_research": store_research,
            })
        except ImportError:
            pass  # Optional tools

        # Spawn tools (Phase 3) - parallel Gemini instances
        try:
            from tools.spawn import spawn_research, spawn_single
            registry.update({
                "spawn_research": spawn_research,
                "spawn_single": spawn_single,
            })
        except ImportError:
            pass  # Optional tools

        # Image tools (Phase 3)
        try:
            from tools.image import (
                analyze_image, generate_image_prompt,
                describe_for_accessibility, extract_text_from_image
            )
            registry.update({
                "analyze_image": analyze_image,
                "generate_image_prompt": generate_image_prompt,
                "describe_for_accessibility": describe_for_accessibility,
                "extract_text_from_image": extract_text_from_image,
            })
        except ImportError:
            pass  # Optional tools

        # Claude collaboration tools (Phase 3)
        try:
            from integrations.claude_collab import (
                check_turn, signal_claude_turn,
                read_handoff_context, add_to_shared_memory
            )
            registry.update({
                "check_turn": check_turn,
                "signal_claude_turn": signal_claude_turn,
                "read_handoff_context": read_handoff_context,
                "add_to_shared_memory": add_to_shared_memory,
            })
        except ImportError:
            pass  # Optional tools

        # Video tools (Phase 3)
        try:
            from tools.video import (
                analyze_video, describe_video_scene, extract_video_frames,
                transcribe_video, count_objects_in_video, detect_video_emotions
            )
            registry.update({
                "analyze_video": analyze_video,
                "describe_video_scene": describe_video_scene,
                "extract_video_frames": extract_video_frames,
                "transcribe_video": transcribe_video,
                "count_objects_in_video": count_objects_in_video,
                "detect_video_emotions": detect_video_emotions,
            })
        except ImportError:
            pass  # Optional tools

        # Audio tools (Phase 3)
        try:
            from tools.audio import (
                transcribe_audio, generate_speech, generate_dialogue,
                analyze_audio, translate_audio, extract_audio_segment
            )
            registry.update({
                "transcribe_audio": transcribe_audio,
                "generate_speech": generate_speech,
                "generate_dialogue": generate_dialogue,
                "analyze_audio": analyze_audio,
                "translate_audio": translate_audio,
                "extract_audio_segment": extract_audio_segment,
            })
        except ImportError:
            pass  # Optional tools

        # Document tools (Phase 3)
        try:
            from tools.documents import (
                process_document, extract_tables, summarize_document,
                extract_form_data, compare_documents, analyze_spreadsheet,
                query_document_section
            )
            registry.update({
                "process_document": process_document,
                "extract_tables": extract_tables,
                "summarize_document": summarize_document,
                "extract_form_data": extract_form_data,
                "compare_documents": compare_documents,
                "analyze_spreadsheet": analyze_spreadsheet,
                "query_document_section": query_document_section,
            })
        except ImportError:
            pass  # Optional tools

        # Web tools (Phase 3)
        try:
            from tools.web import (
                web_search, fetch_url, fetch_multiple_urls, extract_links,
                scrape_structured_data, search_and_summarize,
                monitor_page_changes, verify_claim
            )
            registry.update({
                "web_search": web_search,
                "fetch_url": fetch_url,
                "fetch_multiple_urls": fetch_multiple_urls,
                "extract_links": extract_links,
                "scrape_structured_data": scrape_structured_data,
                "search_and_summarize": search_and_summarize,
                "monitor_page_changes": monitor_page_changes,
                "verify_claim": verify_claim,
            })
        except ImportError:
            pass  # Optional tools

        # Code execution tools (Phase 3)
        try:
            from tools.code_execution import (
                execute_python, calculate, analyze_data, validate_code,
                solve_equation, run_simulation, generate_and_test, debug_code
            )
            registry.update({
                "execute_python": execute_python,
                "calculate": calculate,
                "analyze_data": analyze_data,
                "validate_code": validate_code,
                "solve_equation": solve_equation,
                "run_simulation": run_simulation,
                "generate_and_test": generate_and_test,
                "debug_code": debug_code,
            })
        except ImportError:
            pass  # Optional tools

        # Custom tools (Phase 3 - loaded from YAML config)
        try:
            from tools.custom_loader import get_custom_tools
            custom = get_custom_tools()
            registry.update(custom)
        except ImportError:
            pass  # Optional tools

        # Enhanced image tools (Phase 3)
        try:
            from tools.image import generate_image, detect_objects, compare_images
            registry.update({
                "generate_image": generate_image,
                "detect_objects": detect_objects,
                "compare_images": compare_images,
            })
        except ImportError:
            pass  # Already loaded basic image tools

        # Notebook tools (Phase 4)
        try:
            from tools.notebook import (
                read_notebook, get_cell, edit_cell, insert_cell,
                delete_notebook_cell, move_cell, execute_notebook,
                create_notebook, convert_notebook, clear_outputs
            )
            registry.update({
                "read_notebook": read_notebook,
                "get_cell": get_cell,
                "edit_cell": edit_cell,
                "insert_cell": insert_cell,
                "delete_notebook_cell": delete_notebook_cell,
                "move_cell": move_cell,
                "execute_notebook": execute_notebook,
                "create_notebook": create_notebook,
                "convert_notebook": convert_notebook,
                "clear_outputs": clear_outputs,
            })
        except ImportError:
            pass  # Optional tools

        # Live API tools (Phase 4)
        try:
            from tools.live_api import (
                start_live_session, end_live_session, get_live_transcripts
            )
            registry.update({
                "start_live_session": start_live_session,
                "end_live_session": end_live_session,
                "get_live_transcripts": get_live_transcripts,
            })
        except ImportError:
            pass  # Optional tools

        return registry

    def _request_user_confirmation(self, message: str) -> bool:
        """
        Request user confirmation for a potentially destructive operation.

        Args:
            message: Description of the operation

        Returns:
            True if user confirms, False otherwise
        """
        print(f"\n  [CONFIRM] {message}")
        try:
            response = input("  Allow? (y/n): ").strip().lower()
            return response in ('y', 'yes')
        except (KeyboardInterrupt, EOFError):
            return False

    def _check_security(self, tool_call: ToolCall) -> tuple[bool, str]:
        """
        Check if a tool call passes security validation.

        Args:
            tool_call: The tool call to check

        Returns:
            Tuple of (allowed: bool, message: str)
        """
        if not self.security_enabled:
            return True, "Security disabled"

        try:
            from integrations.security import (
                check_file_operation, check_command,
                validate_path, request_confirmation
            )
        except ImportError:
            return True, "Security module not available"

        tool_name = tool_call.tool
        args = tool_call.args

        # File operations (single path)
        file_ops_single = {
            'read_file': 'read',
            'write_file': 'write',
            'edit_file': 'edit',
            'delete_file': 'delete',
            'delete_directory': 'delete',
            'create_directory': 'create',
            'list_directory': 'list',
        }

        # File operations (two paths: source and destination)
        file_ops_dual = {
            'move_file': 'move',
            'copy_file': 'copy',
        }

        if tool_name in file_ops_single:
            path = args.get('path', '.')
            operation = file_ops_single[tool_name]

            result = check_file_operation(operation, path)

            if not result.allowed:
                return False, result.message

            # Request confirmation for modifying operations
            if result.requires_confirmation:
                details = f"{tool_name} on {path}"
                if not request_confirmation(tool_name, details):
                    return False, "User denied operation"

        elif tool_name in file_ops_dual:
            source = args.get('source', '')
            destination = args.get('destination', '')
            operation = file_ops_dual[tool_name]

            # Check both paths
            for check_path in [source, destination]:
                result = check_file_operation(operation, check_path)
                if not result.allowed:
                    return False, result.message

            # Request confirmation
            details = f"{tool_name}: {source} -> {destination}"
            if not request_confirmation(tool_name, details):
                return False, "User denied operation"

        # Command execution
        elif tool_name == 'run_command':
            cmd = args.get('cmd', '')
            result = check_command(cmd)

            if not result.allowed:
                return False, result.message

            # Request confirmation for commands
            if result.requires_confirmation:
                if not request_confirmation('run_command', cmd):
                    return False, "User denied command"

        return True, "Allowed"

    def _get_account(self) -> int:
        """Get the account number for the current turn (alternates 1, 2)."""
        return (self.turn_count % 2) + 1

    def _call_gemini(
        self,
        prompt: str,
        account: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Call Gemini via the shell script.

        Args:
            prompt: The prompt to send
            account: Account number (1 or 2). If None, uses rotation.
            model: Model ID (e.g., 'gemini-2.5-flash'). If None, uses default.

        Returns:
            Gemini's response text
        """
        if not self.gemini_script:
            return "Error: gemini-account.sh not found. Please ensure it exists at ~/.claude/scripts/gemini-account.sh"

        acc = account or self._get_account()
        model_id = model or "gemini-2.5-flash-lite"  # Default to Flash-Lite for quota preservation

        # On Windows, call gemini directly via PowerShell (bypass shell script issues)
        if sys.platform == 'win32':
            # Swap credentials to requested account
            gemini_dir = Path.home() / ".gemini"
            try:
                import shutil
                shutil.copy2(
                    gemini_dir / f"oauth_creds_account{acc}.json",
                    gemini_dir / "oauth_creds.json"
                )
                shutil.copy2(
                    gemini_dir / f"google_accounts_account{acc}.json",
                    gemini_dir / "google_accounts.json"
                )
            except Exception as e:
                return f"Error switching to account {acc}: {e}"

            # Call gemini via PowerShell with positional prompt
            # Use --output-format text for simple text responses (no tool execution)
            escaped_prompt = prompt.replace("'", "''")  # PowerShell escaping
            ps_command = f"gemini -m '{model_id}' --output-format text '{escaped_prompt}'"

            try:
                result = subprocess.run(
                    ["powershell.exe", "-NonInteractive", "-Command", ps_command],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=str(Path.home())  # Run from home dir to avoid agentic mode in project
                )
            except subprocess.TimeoutExpired:
                return "Error: Gemini request timed out after 5 minutes."
            except Exception as e:
                return f"Error calling Gemini: {e}"
        else:
            # On Linux/Mac, use bash script
            try:
                result = subprocess.run(
                    ["bash", self.gemini_script, str(acc), prompt, model_id],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=os.getcwd()
                )
            except subprocess.TimeoutExpired:
                return "Error: Gemini request timed out after 5 minutes."
            except Exception as e:
                return f"Error calling Gemini: {e}"

        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return f"Error from Gemini (exit {result.returncode}): {error_msg}"

        response = result.stdout.strip()

        if not response:
            return "Error: Gemini returned an empty response. This may indicate rate limiting or authentication issues."

        return response

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call with security checks.

        Args:
            tool_call: The parsed tool call

        Returns:
            ToolResult with success status and output
        """
        tool_name = tool_call.tool
        args = tool_call.args

        # Security check
        allowed, security_msg = self._check_security(tool_call)
        if not allowed:
            # Log security block
            try:
                from integrations.audit import log_security_event
                log_security_event("blocked", tool_name, args, blocked=True, reason=security_msg)
            except ImportError:
                pass
            return ToolResult(
                tool=tool_name,
                success=False,
                output="",
                error=f"Security: {security_msg}"
            )

        # Check if tool exists
        if tool_name not in self.tool_registry:
            available = ", ".join(self.tool_registry.keys())
            return ToolResult(
                tool=tool_name,
                success=False,
                output="",
                error=f"Unknown tool: {tool_name}. Available tools: {available}"
            )

        handler = self.tool_registry[tool_name]

        # Start timing for audit
        import time
        start_time = time.time()

        try:
            # Dispatch based on tool name
            if tool_name == "read_file":
                success, output = handler(args.get("path", ""))
            elif tool_name == "write_file":
                success, output = handler(args.get("path", ""), args.get("content", ""))
            elif tool_name == "edit_file":
                success, output = handler(
                    args.get("path", ""),
                    args.get("old_text", ""),
                    args.get("new_text", "")
                )
            elif tool_name == "list_directory":
                success, output = handler(args.get("path", "."))
            elif tool_name == "delete_file":
                success, output = handler(args.get("path", ""))
            elif tool_name == "delete_directory":
                recursive = args.get("recursive", "false").lower() in ("true", "yes", "1")
                success, output = handler(args.get("path", ""), recursive)
            elif tool_name == "create_directory":
                success, output = handler(args.get("path", ""))
            elif tool_name == "move_file":
                success, output = handler(args.get("source", ""), args.get("destination", ""))
            elif tool_name == "copy_file":
                success, output = handler(args.get("source", ""), args.get("destination", ""))
            elif tool_name == "run_command":
                success, output = handler(args.get("cmd", ""))
            elif tool_name == "search_code":
                success, output = handler(
                    args.get("pattern", ""),
                    args.get("path", "."),
                    args.get("file_type"),
                    int(args.get("max_results", 50))
                )
            elif tool_name == "search_files":
                success, output = handler(
                    args.get("pattern", "*"),
                    args.get("path", ".")
                )
            elif tool_name == "grep_count":
                success, output = handler(
                    args.get("pattern", ""),
                    args.get("path", ".")
                )
            elif tool_name == "query_research":
                success, output = handler(
                    args.get("query", ""),
                    int(args.get("limit", 5))
                )
            elif tool_name == "store_research":
                success, output = handler(
                    args.get("content", ""),
                    args.get("research_type", "general")
                )
            # Phase 3: Spawn tools
            elif tool_name == "spawn_research":
                # Parse queries - could be JSON array or comma-separated
                queries_raw = args.get("queries", "")
                if queries_raw.startswith("["):
                    import json
                    queries = json.loads(queries_raw)
                else:
                    queries = [q.strip() for q in queries_raw.split(",") if q.strip()]
                success, output = handler(queries)
            elif tool_name == "spawn_single":
                account = int(args.get("account", 1))
                success, output = handler(args.get("query", ""), account)
            # Phase 3: Image tools
            elif tool_name == "analyze_image":
                success, output = handler(
                    args.get("image_path", args.get("path", "")),
                    args.get("prompt", "Describe this image in detail.")
                )
            elif tool_name == "generate_image_prompt":
                success, output = handler(
                    args.get("description", ""),
                    args.get("style", "photorealistic"),
                    args.get("aspect_ratio", "1:1")
                )
            elif tool_name == "describe_for_accessibility":
                success, output = handler(
                    args.get("image_path", args.get("path", "")),
                    args.get("context", "")
                )
            elif tool_name == "extract_text_from_image":
                success, output = handler(args.get("image_path", args.get("path", "")))
            # Phase 3: Claude collaboration tools
            elif tool_name == "check_turn":
                success, output = handler()
            elif tool_name == "signal_claude_turn":
                success, output = handler(
                    summary=args.get("summary", ""),
                    research_topics=args.get("research_topics", "").split(",") if args.get("research_topics") else None,
                    questions=args.get("questions", "").split(",") if args.get("questions") else None
                )
            elif tool_name == "read_handoff_context":
                success, output = handler()
            elif tool_name == "add_to_shared_memory":
                success, output = handler(
                    category=args.get("category", "Learning"),
                    content=args.get("content", ""),
                    source="gemini"
                )
            # Phase 3: Video tools
            elif tool_name == "analyze_video":
                success, output = handler(
                    args.get("video_path", args.get("path", "")),
                    args.get("query", ""),
                    args.get("timestamp")
                )
            elif tool_name == "describe_video_scene":
                success, output = handler(
                    args.get("video_path", args.get("path", "")),
                    args.get("start_time"),
                    args.get("end_time")
                )
            elif tool_name == "transcribe_video":
                success, output = handler(
                    args.get("video_path", args.get("path", "")),
                    args.get("include_timestamps", "true").lower() in ("true", "yes", "1"),
                    args.get("identify_speakers", "false").lower() in ("true", "yes", "1")
                )
            elif tool_name == "count_objects_in_video":
                success, output = handler(
                    args.get("video_path", args.get("path", "")),
                    args.get("object_type", ""),
                    args.get("throughout", "true").lower() in ("true", "yes", "1")
                )
            # Phase 3: Audio tools
            elif tool_name == "transcribe_audio":
                success, output = handler(
                    args.get("audio_path", args.get("path", "")),
                    args.get("identify_speakers", "false").lower() in ("true", "yes", "1"),
                    args.get("include_timestamps", "true").lower() in ("true", "yes", "1"),
                    args.get("language")
                )
            elif tool_name == "generate_speech":
                success, output = handler(
                    args.get("text", ""),
                    args.get("output_path", ""),
                    args.get("style", "natural"),
                    args.get("language", "en"),
                    args.get("pace", "normal")
                )
            elif tool_name == "analyze_audio":
                success, output = handler(
                    args.get("audio_path", args.get("path", "")),
                    args.get("analysis_type", "general")
                )
            elif tool_name == "translate_audio":
                success, output = handler(
                    args.get("audio_path", args.get("path", "")),
                    args.get("target_language", "en"),
                    args.get("output_mode", "text")
                )
            # Phase 3: Document tools
            elif tool_name == "process_document":
                success, output = handler(
                    args.get("document_path", args.get("path", "")),
                    args.get("query", "")
                )
            elif tool_name == "extract_tables":
                success, output = handler(
                    args.get("document_path", args.get("path", "")),
                    args.get("output_format", "markdown"),
                    int(args.get("table_index")) if args.get("table_index") else None
                )
            elif tool_name == "summarize_document":
                success, output = handler(
                    args.get("document_path", args.get("path", "")),
                    args.get("summary_type", "executive"),
                    int(args.get("max_length")) if args.get("max_length") else None
                )
            elif tool_name == "extract_form_data":
                success, output = handler(
                    args.get("document_path", args.get("path", "")),
                    args.get("form_type", "auto")
                )
            elif tool_name == "compare_documents":
                success, output = handler(
                    args.get("doc_path_1", args.get("path1", "")),
                    args.get("doc_path_2", args.get("path2", "")),
                    args.get("comparison_focus", "content")
                )
            elif tool_name == "analyze_spreadsheet":
                success, output = handler(
                    args.get("spreadsheet_path", args.get("path", "")),
                    args.get("analysis_type", "overview"),
                    args.get("sheet_name")
                )
            # Phase 3: Web tools
            elif tool_name == "web_search":
                success, output = handler(
                    args.get("query", ""),
                    args.get("include_sources", "true").lower() in ("true", "yes", "1"),
                    int(args.get("num_results", 5))
                )
            elif tool_name == "fetch_url":
                success, output = handler(
                    args.get("url", ""),
                    args.get("query")
                )
            elif tool_name == "fetch_multiple_urls":
                urls_raw = args.get("urls", "")
                if urls_raw.startswith("["):
                    import json
                    urls = json.loads(urls_raw)
                else:
                    urls = [u.strip() for u in urls_raw.split(",") if u.strip()]
                success, output = handler(urls, args.get("query"))
            elif tool_name == "scrape_structured_data":
                success, output = handler(
                    args.get("url", ""),
                    args.get("data_type", "auto")
                )
            elif tool_name == "search_and_summarize":
                success, output = handler(
                    args.get("topic", ""),
                    args.get("depth", "standard")
                )
            elif tool_name == "verify_claim":
                success, output = handler(args.get("claim", ""))
            # Phase 3: Code execution tools
            elif tool_name == "execute_python":
                success, output = handler(
                    args.get("code", ""),
                    args.get("description")
                )
            elif tool_name == "calculate":
                success, output = handler(
                    args.get("expression", ""),
                    int(args.get("precision", 10))
                )
            elif tool_name == "analyze_data":
                success, output = handler(
                    args.get("data", ""),
                    args.get("analysis", "descriptive")
                )
            elif tool_name == "validate_code":
                test_inputs = None
                if args.get("test_inputs"):
                    import json
                    try:
                        test_inputs = json.loads(args["test_inputs"])
                    except:
                        pass
                success, output = handler(
                    args.get("code", ""),
                    args.get("language", "python"),
                    test_inputs
                )
            elif tool_name == "solve_equation":
                success, output = handler(
                    args.get("equation", ""),
                    args.get("variable", "x"),
                    args.get("method", "auto")
                )
            elif tool_name == "run_simulation":
                success, output = handler(
                    args.get("description", ""),
                    int(args.get("iterations", 1000))
                )
            elif tool_name == "debug_code":
                success, output = handler(
                    args.get("code", ""),
                    args.get("error_message")
                )
            # Phase 3: Enhanced image tools
            elif tool_name == "generate_image":
                success, output = handler(
                    args.get("prompt", ""),
                    args.get("output_path", ""),
                    args.get("aspect_ratio", "1:1"),
                    args.get("style")
                )
            elif tool_name == "detect_objects":
                objects_raw = args.get("objects_to_find", "")
                objects = None
                if objects_raw:
                    if objects_raw.startswith("["):
                        import json
                        objects = json.loads(objects_raw)
                    else:
                        objects = [o.strip() for o in objects_raw.split(",") if o.strip()]
                success, output = handler(
                    args.get("image_path", args.get("path", "")),
                    objects,
                    args.get("return_bounding_boxes", "true").lower() in ("true", "yes", "1")
                )
            elif tool_name == "compare_images":
                success, output = handler(
                    args.get("image_path_1", args.get("path1", "")),
                    args.get("image_path_2", args.get("path2", "")),
                    args.get("comparison_type", "visual")
                )
            # Phase 4: Notebook tools
            elif tool_name == "read_notebook":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    args.get("include_outputs", "true").lower() in ("true", "yes", "1")
                )
            elif tool_name == "get_cell":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    int(args.get("cell_index", 0))
                )
            elif tool_name == "edit_cell":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    int(args.get("cell_index", 0)),
                    args.get("new_content", ""),
                    args.get("cell_type")
                )
            elif tool_name == "insert_cell":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    int(args.get("position", 0)),
                    args.get("content", ""),
                    args.get("cell_type", "code")
                )
            elif tool_name == "delete_notebook_cell":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    int(args.get("cell_index", 0))
                )
            elif tool_name == "move_cell":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    int(args.get("from_index", 0)),
                    int(args.get("to_index", 0))
                )
            elif tool_name == "execute_notebook":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    args.get("output_path"),
                    int(args.get("timeout", 60))
                )
            elif tool_name == "create_notebook":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    args.get("kernel", "python3")
                )
            elif tool_name == "convert_notebook":
                success, output = handler(
                    args.get("notebook_path", args.get("path", "")),
                    args.get("output_format", "html"),
                    args.get("output_path")
                )
            elif tool_name == "clear_outputs":
                success, output = handler(
                    args.get("notebook_path", args.get("path", ""))
                )
            # Phase 4: Live API tools
            elif tool_name == "start_live_session":
                success, output = handler(
                    args.get("session_id")
                )
            elif tool_name == "end_live_session":
                success, output = handler()
            elif tool_name == "get_live_transcripts":
                success, output = handler()
            else:
                # Generic call attempt for custom tools and any others
                success, output = handler(**args)

            # Log successful tool call
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                from integrations.audit import log_event
                log_event(
                    "tool_call", tool=tool_name, args=args,
                    status="success" if success else "failure",
                    duration_ms=duration_ms
                )
            except ImportError:
                pass

            return ToolResult(
                tool=tool_name,
                success=success,
                output=output,
                error=None if success else output
            )

        except Exception as e:
            # Log error
            duration_ms = int((time.time() - start_time) * 1000)
            try:
                from integrations.audit import log_event
                log_event(
                    "tool_call", tool=tool_name, args=args,
                    status="error", duration_ms=duration_ms, error=str(e)
                )
            except ImportError:
                pass

            return ToolResult(
                tool=tool_name,
                success=False,
                output="",
                error=f"Tool execution error: {e}"
            )

    def process_input(self, user_input: str) -> str:
        """
        Process a single user input through the full agentic loop.

        Args:
            user_input: The user's message

        Returns:
            The final response to display
        """
        self.turn_count += 1

        # Update session if available
        try:
            from integrations.session import update_session
            update_session(turn_count=self.turn_count, current_task=user_input[:100])
        except ImportError:
            pass

        # Add user message to history
        add_user_message(self.history, user_input)

        # Build the full prompt
        history_context = format_history_for_prompt(self.history[:-1])
        if history_context:
            full_prompt = f"{self.system_prompt}\n\nPrevious conversation:\n{history_context}\n\nUser: {user_input}"
        else:
            full_prompt = f"{self.system_prompt}\n\nUser: {user_input}"

        # Call Gemini
        response = self._call_gemini(full_prompt)

        # Handle errors from Gemini
        if response.startswith("Error:"):
            add_assistant_message(self.history, response)
            return response

        # Agentic loop: execute tools until no more tool calls
        max_iterations = 10
        iteration = 0

        while contains_tool_call(response) and iteration < max_iterations:
            iteration += 1

            # Parse and execute tool calls
            tool_calls = parse_tool_calls(response)
            tool_results = []

            for tc in tool_calls:
                print(f"  [Executing: {tc.tool}]")
                result = self._execute_tool(tc)
                formatted = format_tool_result(result)
                tool_results.append(formatted)
                add_tool_result(self.history, tc.tool, formatted)

            # Build continuation prompt with results
            results_text = "\n\n".join(tool_results)
            continuation = f"{results_text}\n\nPlease continue based on the tool results above."

            # Call Gemini again with results
            response = self._call_gemini(continuation)

            if response.startswith("Error:"):
                break

        # Add final response to history
        add_assistant_message(self.history, response)

        return response

    def run(self):
        """
        Run the interactive REPL loop.

        Handles user input, processes through the agentic loop,
        and displays responses until user exits.
        """
        # Start session
        try:
            from integrations.session import start_session
            start_session(str(self.project_root))
        except ImportError:
            pass

        print("Gemini Agentic CLI ready. Type 'exit' or 'quit' to leave.")
        print("Type 'clear' to reset conversation history.")
        if self.security_enabled:
            print("Security: ENABLED (sandboxing to project root)")
        else:
            print("Security: DISABLED (use with caution)")
        print("-" * 50)
        print()

        while True:
            try:
                user_input = input("You: ").strip()
            except (KeyboardInterrupt, EOFError):
                print("\n\nGoodbye!")
                break

            if not user_input:
                continue

            # Handle special commands
            if user_input.lower() in ('exit', 'quit'):
                print("\nGoodbye!")
                break

            if user_input.lower() == 'clear':
                self.history = []
                print("Conversation history cleared.\n")
                continue

            if user_input.lower() == 'history':
                info = self._get_session_info()
                print(f"\nSession: {info['message_count']} messages, {info['tool_calls_count']} tool calls")
                print()
                continue

            if user_input.lower() == 'security':
                self.security_enabled = not self.security_enabled
                status = "ENABLED" if self.security_enabled else "DISABLED"
                print(f"Security: {status}\n")
                continue

            # Process the input
            print()
            response = self.process_input(user_input)
            print(f"\nGemini: {response}\n")

    def _get_session_info(self) -> dict:
        """Get session statistics."""
        tool_calls = sum(
            1 for entry in self.history
            if entry.get("role") == "tool_result"
        )
        return {
            "message_count": len(self.history),
            "tool_calls_count": tool_calls
        }
