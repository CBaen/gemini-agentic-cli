"""
Orchestrator - The Core Agent Loop

This is the beating heart of the Gemini Agentic CLI.
It coordinates: user input → Gemini → tool execution → response display.

Flow:
    1. User provides input
    2. Orchestrator builds prompt with history + system instructions
    3. Calls Gemini via gemini-account.sh
    4. Parses tool calls from response
    5. Executes tools, feeds results back to Gemini
    6. Loops until Gemini responds without tool calls
    7. Displays final response, saves history
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
        - Tool execution
        - Account rotation
    """

    def __init__(
        self,
        history: Optional[list] = None,
        gemini_script: Optional[str] = None
    ):
        """
        Initialize the orchestrator.

        Args:
            history: Optional pre-loaded conversation history
            gemini_script: Path to gemini-account.sh (auto-detected if not provided)
        """
        self.history = history if history is not None else []
        self.turn_count = 0

        # Find gemini-account.sh
        if gemini_script:
            self.gemini_script = gemini_script
        else:
            # Default location
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
        from tools.filesystem import read_file, write_file, list_directory
        from tools.shell import run_command

        return {
            "read_file": read_file,
            "write_file": write_file,
            "list_directory": list_directory,
            "run_command": run_command,
        }

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
                    timeout=300,  # 5 minute timeout for complex queries
                    cwd=os.getcwd()
                )
            except subprocess.TimeoutExpired:
                return "Error: Gemini request timed out after 5 minutes."
            except Exception as e:
                return f"Error calling Gemini: {e}"
        else:
            # Unix
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

        # Check for errors
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else "Unknown error"
            return f"Error from Gemini (exit {result.returncode}): {error_msg}"

        response = result.stdout.strip()

        # Handle empty response
        if not response:
            return "Error: Gemini returned an empty response. This may indicate rate limiting or authentication issues."

        return response

    def _execute_tool(self, tool_call: ToolCall) -> ToolResult:
        """
        Execute a single tool call.

        Args:
            tool_call: The parsed tool call

        Returns:
            ToolResult with success status and output
        """
        tool_name = tool_call.tool
        args = tool_call.args

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
            # Call the tool with appropriate arguments
            if tool_name == "read_file":
                success, output = handler(args.get("path", ""))
            elif tool_name == "write_file":
                success, output = handler(args.get("path", ""), args.get("content", ""))
            elif tool_name == "list_directory":
                success, output = handler(args.get("path", "."))
            elif tool_name == "run_command":
                success, output = handler(args.get("cmd", ""))
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

        # Add user message to history
        add_user_message(self.history, user_input)

        # Build the full prompt
        history_context = format_history_for_prompt(self.history[:-1])  # Exclude current
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
        max_iterations = 10  # Safety limit
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
        print("Gemini Agentic CLI ready. Type 'exit' or 'quit' to leave.")
        print("Type 'clear' to reset conversation history.")
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

            # Process the input
            print()  # Visual spacing
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