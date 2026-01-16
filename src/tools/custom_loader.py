"""
Custom Tool Loader

Allows users to define custom tools via YAML configuration.
This makes the CLI extensible without modifying code.

Configuration file: ~/.gemini-cli/custom_tools.yaml

Example:
```yaml
tools:
  - name: deploy_preview
    command: "vercel deploy --prebuilt"
    description: "Deploy preview to Vercel"
    confirmation_required: true

  - name: run_tests
    command: "npm test"
    description: "Run project tests"
    confirmation_required: false
```
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any, List, Callable
import json


# Default config location
DEFAULT_CONFIG_PATH = Path.home() / ".gemini-cli" / "custom_tools.yaml"


def load_yaml_config(config_path: Path = None) -> Tuple[bool, Any]:
    """
    Load YAML configuration file.

    Args:
        config_path: Path to config file (defaults to ~/.gemini-cli/custom_tools.yaml)

    Returns:
        Tuple of (success: bool, config_dict or error_message)
    """
    path = config_path or DEFAULT_CONFIG_PATH

    if not path.exists():
        return False, f"Config file not found: {path}"

    try:
        # Try to use pyyaml if available
        try:
            import yaml
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            return True, config
        except ImportError:
            # Fallback to basic YAML parsing for simple configs
            return parse_simple_yaml(path)

    except Exception as e:
        return False, f"Error loading config: {e}"


def parse_simple_yaml(path: Path) -> Tuple[bool, Any]:
    """
    Basic YAML parser for simple tool definitions.
    Handles the subset of YAML we need without external dependencies.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Very basic YAML parsing for tool definitions
        tools = []
        current_tool = {}
        in_tools_list = False

        for line in content.split('\n'):
            stripped = line.strip()

            if stripped.startswith('tools:'):
                in_tools_list = True
                continue

            if not in_tools_list:
                continue

            if stripped.startswith('- name:'):
                if current_tool:
                    tools.append(current_tool)
                current_tool = {'name': stripped.split(':', 1)[1].strip().strip('"').strip("'")}
            elif stripped.startswith('command:'):
                current_tool['command'] = stripped.split(':', 1)[1].strip().strip('"').strip("'")
            elif stripped.startswith('description:'):
                current_tool['description'] = stripped.split(':', 1)[1].strip().strip('"').strip("'")
            elif stripped.startswith('confirmation_required:'):
                value = stripped.split(':', 1)[1].strip().lower()
                current_tool['confirmation_required'] = value in ('true', 'yes', '1')
            elif stripped.startswith('timeout:'):
                try:
                    current_tool['timeout'] = int(stripped.split(':', 1)[1].strip())
                except ValueError:
                    current_tool['timeout'] = 120
            elif stripped.startswith('working_dir:'):
                current_tool['working_dir'] = stripped.split(':', 1)[1].strip().strip('"').strip("'")

        if current_tool:
            tools.append(current_tool)

        return True, {'tools': tools}

    except Exception as e:
        return False, f"YAML parsing error: {e}"


def validate_tool_definition(tool: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate a tool definition.

    Args:
        tool: Tool definition dict

    Returns:
        Tuple of (valid: bool, error_message_if_invalid: str)
    """
    required_fields = ['name', 'command']

    for field in required_fields:
        if field not in tool:
            return False, f"Missing required field: {field}"

    name = tool['name']
    if not name.isidentifier():
        return False, f"Invalid tool name: {name} (must be valid Python identifier)"

    # Check for dangerous patterns in command
    dangerous_patterns = [
        'rm -rf /',
        'rm -rf ~',
        '> /dev/',
        'mkfs.',
        'dd if=',
        ':(){:|:&};:',  # Fork bomb
    ]

    command = tool['command'].lower()
    for pattern in dangerous_patterns:
        if pattern in command:
            return False, f"Dangerous command pattern detected: {pattern}"

    return True, ""


def create_tool_executor(tool_def: Dict[str, Any]) -> Callable:
    """
    Create an executor function for a custom tool.

    Args:
        tool_def: Tool definition dict

    Returns:
        Callable that executes the tool
    """
    name = tool_def['name']
    command_template = tool_def['command']
    description = tool_def.get('description', f"Custom tool: {name}")
    confirmation_required = tool_def.get('confirmation_required', False)
    timeout = tool_def.get('timeout', 120)
    working_dir = tool_def.get('working_dir', None)

    def executor(**kwargs) -> Tuple[bool, str]:
        """Execute the custom tool."""
        # Substitute any arguments into the command template
        command = command_template
        for key, value in kwargs.items():
            command = command.replace(f'{{{key}}}', str(value))
            command = command.replace(f'${key}', str(value))

        # Set working directory
        cwd = working_dir if working_dir else os.getcwd()
        if working_dir:
            cwd = os.path.expanduser(working_dir)

        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd
            )

            output_parts = []
            if result.stdout:
                output_parts.append(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                output_parts.append(f"STDERR:\n{result.stderr}")
            output_parts.append(f"EXIT CODE: {result.returncode}")

            output = "\n".join(output_parts)

            return result.returncode == 0, output

        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except Exception as e:
            return False, f"Execution error: {e}"

    # Attach metadata to the function
    executor.__doc__ = description
    executor.__name__ = name
    executor._requires_confirmation = confirmation_required
    executor._is_custom_tool = True

    return executor


def load_custom_tools(config_path: Path = None) -> Tuple[bool, Dict[str, Callable]]:
    """
    Load all custom tools from configuration.

    Args:
        config_path: Path to config file

    Returns:
        Tuple of (success: bool, tools_dict or error_message)
    """
    success, result = load_yaml_config(config_path)

    if not success:
        # No config file is not an error - just no custom tools
        if "not found" in str(result):
            return True, {}
        return False, result

    config = result
    tools = {}

    if 'tools' not in config:
        return True, {}

    for tool_def in config['tools']:
        valid, error = validate_tool_definition(tool_def)
        if not valid:
            print(f"Warning: Skipping invalid tool '{tool_def.get('name', 'unnamed')}': {error}")
            continue

        executor = create_tool_executor(tool_def)
        tools[tool_def['name']] = executor

    return True, tools


def get_tool_info(tools: Dict[str, Callable]) -> List[Dict[str, Any]]:
    """
    Get information about loaded custom tools.

    Args:
        tools: Dict of tool name -> executor function

    Returns:
        List of tool info dicts
    """
    info = []
    for name, executor in tools.items():
        info.append({
            'name': name,
            'description': executor.__doc__,
            'requires_confirmation': getattr(executor, '_requires_confirmation', False),
            'is_custom': getattr(executor, '_is_custom_tool', False)
        })
    return info


def create_default_config(config_path: Path = None) -> Tuple[bool, str]:
    """
    Create a default configuration file with examples.

    Args:
        config_path: Path for config file

    Returns:
        Tuple of (success: bool, message: str)
    """
    path = config_path or DEFAULT_CONFIG_PATH

    if path.exists():
        return False, f"Config file already exists: {path}"

    default_config = """# Gemini CLI Custom Tools Configuration
# Define your own tools that Gemini can use

tools:
  # Example: Run project tests
  - name: run_tests
    command: "npm test"
    description: "Run the project test suite"
    confirmation_required: false
    timeout: 300

  # Example: Deploy preview (requires confirmation)
  - name: deploy_preview
    command: "vercel deploy --prebuilt"
    description: "Deploy a preview build to Vercel"
    confirmation_required: true
    timeout: 180

  # Example: Format code
  - name: format_code
    command: "prettier --write ."
    description: "Format all code files with Prettier"
    confirmation_required: false
    timeout: 60

  # Example: Tool with arguments
  # Use {arg_name} or $arg_name in command template
  - name: git_commit
    command: "git commit -m '{message}'"
    description: "Create a git commit with the specified message"
    confirmation_required: true
    timeout: 30

# Add your custom tools below:
"""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(default_config)
        return True, f"Created default config at: {path}"
    except Exception as e:
        return False, f"Error creating config: {e}"


def list_custom_tools(config_path: Path = None) -> Tuple[bool, str]:
    """
    List all configured custom tools.

    Args:
        config_path: Path to config file

    Returns:
        Tuple of (success: bool, tools_list: str)
    """
    success, result = load_custom_tools(config_path)

    if not success:
        return False, str(result)

    if not result:
        path = config_path or DEFAULT_CONFIG_PATH
        return True, f"No custom tools configured.\nCreate config at: {path}"

    lines = ["Custom Tools:"]
    for name, executor in result.items():
        confirm = " [requires confirmation]" if getattr(executor, '_requires_confirmation', False) else ""
        lines.append(f"  - {name}: {executor.__doc__}{confirm}")

    return True, "\n".join(lines)


# Standalone functions for tool registry
def load_tools() -> Tuple[bool, str]:
    """Load custom tools and return status."""
    success, result = load_custom_tools()
    if success:
        count = len(result) if isinstance(result, dict) else 0
        return True, f"Loaded {count} custom tools"
    return False, str(result)


def create_config() -> Tuple[bool, str]:
    """Create default config file."""
    return create_default_config()


def list_tools() -> Tuple[bool, str]:
    """List configured tools."""
    return list_custom_tools()


# Tool registry (these are meta-tools for managing custom tools)
CUSTOM_LOADER_TOOLS = {
    "load_custom_tools": load_tools,
    "create_custom_config": create_config,
    "list_custom_tools": list_tools,
}


# Export function for orchestrator to get actual custom tools
def get_custom_tools() -> Dict[str, Callable]:
    """Get dict of custom tool executors for the orchestrator."""
    success, tools = load_custom_tools()
    if success and isinstance(tools, dict):
        return tools
    return {}
