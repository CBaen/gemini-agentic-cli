"""
Tool Protocol - Text-Based Tool Communication

This module defines how Gemini requests tool execution and how we format results.
We use text parsing because we invoke Gemini via CLI, not the API SDK.

Protocol Format:
    TOOL_CALL: tool_name | param=value | param=value
    TOOL_RESULT: tool_name | status=success/error | output=...

For multiline content, triple backticks are used:
    TOOL_CALL: write_file | path=test.py | content=```
    print("hello")
    ```

Escaping:
    - Pipe in content: | → \\|
    - Backslash before pipe: \\ → \\\\
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ToolCall:
    """Represents a parsed tool call from Gemini's response."""
    tool: str
    args: dict[str, str]
    raw: str  # Original text for debugging


@dataclass
class ToolResult:
    """Represents a tool execution result to send back to Gemini."""
    tool: str
    success: bool
    output: str
    error: Optional[str] = None


# Pattern to match tool calls
# Matches: TOOL_CALL: tool_name | args...
TOOL_CALL_PATTERN = re.compile(
    r'TOOL_CALL:\s*(\w+)\s*\|(.+?)(?=TOOL_CALL:|$)',
    re.DOTALL
)

# Pattern to match key=value pairs
# Handles escaped pipes and backtick-delimited content
ARG_PATTERN = re.compile(
    r'(\w+)=(```[\s\S]*?```|[^|]+?)(?=\s*\||$)'
)


def escape_content(text: str) -> str:
    """Escape special characters in content for protocol safety."""
    # Escape backslashes first, then pipes
    text = text.replace('\\', '\\\\')
    text = text.replace('|', '\\|')
    return text


def unescape_content(text: str) -> str:
    """Unescape special characters from protocol format."""
    # Unescape in reverse order
    text = text.replace('\\|', '|')
    text = text.replace('\\\\', '\\')
    return text


def parse_tool_calls(response: str) -> list[ToolCall]:
    """
    Parse all tool calls from Gemini's response.

    Args:
        response: The full text response from Gemini

    Returns:
        List of ToolCall objects (may be empty if no tool calls found)
    """
    tool_calls = []

    # Find all TOOL_CALL: patterns
    for match in TOOL_CALL_PATTERN.finditer(response):
        tool_name = match.group(1).strip()
        args_str = match.group(2).strip()
        raw_text = match.group(0)

        # Parse arguments
        args = {}
        for arg_match in ARG_PATTERN.finditer(args_str):
            key = arg_match.group(1).strip()
            value = arg_match.group(2).strip()

            # Handle backtick-delimited content
            if value.startswith('```') and value.endswith('```'):
                # Extract content between backticks
                value = value[3:-3]
                # Remove optional language specifier on first line
                if value.startswith('\n'):
                    value = value[1:]
                elif '\n' in value:
                    first_newline = value.index('\n')
                    first_part = value[:first_newline]
                    # If first part looks like a language tag, skip it
                    if first_part.strip().isalnum() or first_part.strip() == '':
                        value = value[first_newline + 1:]
            else:
                # Unescape regular values
                value = unescape_content(value)

            args[key] = value

        tool_calls.append(ToolCall(tool=tool_name, args=args, raw=raw_text))

    return tool_calls


def contains_tool_call(response: str) -> bool:
    """Check if response contains any tool calls."""
    return 'TOOL_CALL:' in response


def format_tool_result(result: ToolResult) -> str:
    """
    Format a tool result to send back to Gemini.

    Args:
        result: The ToolResult object

    Returns:
        Formatted string for Gemini to process
    """
    if result.success:
        # Escape output content for protocol safety
        output = result.output
        # Use backticks for multiline output
        if '\n' in output:
            return f"TOOL_RESULT: {result.tool} | status=success | output=```\n{output}\n```"
        else:
            return f"TOOL_RESULT: {result.tool} | status=success | output={escape_content(output)}"
    else:
        error_msg = result.error or "Unknown error"
        return f"TOOL_RESULT: {result.tool} | status=error | error={escape_content(error_msg)}"


def format_available_tools(tool_registry: dict) -> str:
    """
    Format available tools for Gemini's system prompt.

    Args:
        tool_registry: Dict mapping tool names to their handler functions

    Returns:
        Formatted string describing available tools
    """
    lines = ["Available tools:"]
    for name, handler in tool_registry.items():
        doc = handler.__doc__ or "No description available"
        # Get first line of docstring
        first_line = doc.strip().split('\n')[0]
        lines.append(f"  - {name}: {first_line}")
    return '\n'.join(lines)


# System prompt template for Gemini
SYSTEM_PROMPT_TEMPLATE = """You are an AI assistant with access to tools for file operations and command execution.

When you need to use a tool, output EXACTLY this format:
TOOL_CALL: tool_name | param1=value1 | param2=value2

For multiline content (like file contents), use triple backticks:
TOOL_CALL: write_file | path=example.py | content=```
print("Hello, World!")
```

{available_tools}

IMPORTANT:
- Wait for TOOL_RESULT before proceeding
- You can make multiple tool calls in sequence
- If a tool fails, you can try an alternative approach
- When your task is complete, respond normally without tool calls

Current working directory: {cwd}
"""


def build_system_prompt(tool_registry: dict) -> str:
    """Build the complete system prompt with available tools."""
    import os
    return SYSTEM_PROMPT_TEMPLATE.format(
        available_tools=format_available_tools(tool_registry),
        cwd=os.getcwd()
    )
