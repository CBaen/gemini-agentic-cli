"""
Orchestrator - The Core Agent Loop

This is the beating heart of the Gemini Agentic CLI.
It coordinates: user input → Gemini → tool execution → response display.

Phase 2 additions:
- Security layer integration (sandboxing, whitelisting)
- Confirmation prompts for destructive operations
- Extended tool registry (search, edit, qdrant)
- Session lifecycle management

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
            from tools.filesystem import read_file, write_file, edit_file, list_directory
            registry.update({
                "read_file": read_file,
                "write_file": write_file,
                "edit_file": edit_file,
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

        # File operations
        if tool_name in ('read_file', 'write_file', 'edit_file', 'list_directory'):
            path = args.get('path', '.')
            operation = tool_name.split('_')[0]  # read, write, edit, list

            result = check_file_operation(operation, path)

            if not result.allowed:
                return False, result.message

            # Request confirmation for write operations
            if result.requires_confirmation:
                details = f"{tool_name} on {path}"
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

    def _call_gemini(self, prompt: str, account: Optional[int] = None) -> str:
        """
        Call Gemini via the shell script.

        Args:
            prompt: The prompt to send
            account: Account number (1 or 2). If None, uses rotation.

        Returns:
            Gemini's response text
        """
        if not self.gemini_script:
            return "Error: gemini-account.sh not found. Please ensure it exists at ~/.claude/scripts/gemini-account.sh"

        acc = account or self._get_account()

        # Find Git Bash on Windows for reliable execution
        if sys.platform == 'win32':
            git_bash = Path("C:/Program Files/Git/usr/bin/bash.exe")
            if not git_bash.exists():
                git_bash = Path("C:/Program Files/Git/bin/bash.exe")
            if not git_bash.exists():
                return "Error: Git Bash not found. Please install Git for Windows."

            try:
                result = subprocess.run(
                    [str(git_bash), self.gemini_script, str(acc), prompt],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    cwd=os.getcwd()
                )
            except subprocess.TimeoutExpired:
                return "Error: Gemini request timed out after 5 minutes."
            except Exception as e:
                return f"Error calling Gemini: {e}"
        else:
            try:
                result = subprocess.run(
                    ["bash", self.gemini_script, str(acc), prompt],
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
            else:
                # Generic call attempt
                success, output = handler(**args)

            return ToolResult(
                tool=tool_name,
                success=success,
                output=output,
                error=None if success else output
            )

        except Exception as e:
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
