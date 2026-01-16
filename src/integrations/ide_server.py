"""
IDE Integration Server

Provides a JSON-RPC server that IDEs (like VS Code) can connect to:
- Language Server Protocol (LSP) inspired design
- Code completion suggestions
- Inline code generation
- Code explanation on hover
- Quick fixes and refactoring
- Command palette integration

The server runs as a subprocess that the IDE extension communicates with.
"""

import sys
import json
import threading
import socketserver
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, asdict
from enum import Enum


class RequestMethod(Enum):
    """Supported request methods."""
    INITIALIZE = "initialize"
    SHUTDOWN = "shutdown"
    COMPLETE = "complete"
    EXPLAIN = "explain"
    GENERATE = "generate"
    REFACTOR = "refactor"
    FIX = "fix"
    EXECUTE = "execute"
    SEARCH = "search"


@dataclass
class Position:
    """Position in a document."""
    line: int
    character: int


@dataclass
class Range:
    """Range in a document."""
    start: Position
    end: Position


@dataclass
class TextEdit:
    """A text edit to apply."""
    range: Range
    new_text: str


@dataclass
class CompletionItem:
    """A completion suggestion."""
    label: str
    detail: str = ""
    documentation: str = ""
    insert_text: str = ""
    kind: str = "text"  # text, function, class, etc.


@dataclass
class CodeAction:
    """A code action (quick fix, refactoring)."""
    title: str
    kind: str  # quickfix, refactor, etc.
    edits: List[TextEdit] = None
    command: str = None


class IDEHandler:
    """
    Handles IDE requests.

    This is where the actual Gemini integration happens.
    """

    def __init__(self, gemini_script: str = None):
        self.gemini_script = gemini_script or str(
            Path.home() / ".claude" / "scripts" / "gemini-account.sh"
        )
        self.initialized = False
        self.workspace_root: Optional[str] = None

    def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Route and handle a request.

        Args:
            method: Request method name
            params: Request parameters

        Returns:
            Response data
        """
        handlers = {
            "initialize": self._handle_initialize,
            "shutdown": self._handle_shutdown,
            "complete": self._handle_complete,
            "explain": self._handle_explain,
            "generate": self._handle_generate,
            "refactor": self._handle_refactor,
            "fix": self._handle_fix,
            "execute": self._handle_execute,
            "search": self._handle_search,
        }

        handler = handlers.get(method)
        if not handler:
            return {"error": f"Unknown method: {method}"}

        try:
            return handler(params)
        except Exception as e:
            return {"error": str(e)}

    def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Initialize the server."""
        self.workspace_root = params.get("workspaceRoot")
        self.initialized = True

        return {
            "capabilities": {
                "completionProvider": True,
                "codeActionProvider": True,
                "hoverProvider": True,
                "executeCommandProvider": True,
            },
            "serverInfo": {
                "name": "Gemini Agentic CLI",
                "version": "1.0.0"
            }
        }

    def _handle_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Shutdown the server."""
        self.initialized = False
        return {"status": "shutdown"}

    def _handle_complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Provide code completions.

        Params:
            - file: File path
            - position: Cursor position
            - context: Surrounding code
        """
        file_path = params.get("file", "")
        position = params.get("position", {})
        context = params.get("context", "")

        # Build prompt for Gemini
        prompt = f"""Provide code completion suggestions for the following context:

File: {file_path}
Position: Line {position.get('line', 0)}, Column {position.get('character', 0)}

Context:
{context}

Provide 3-5 relevant completions. Format each as:
COMPLETION: <label> | <detail> | <insert_text>
"""

        # Call Gemini (would use actual implementation)
        # For now, return placeholder
        completions = [
            CompletionItem(
                label="placeholder",
                detail="Gemini completion",
                insert_text="# Gemini would provide actual completion here"
            )
        ]

        return {
            "completions": [asdict(c) for c in completions]
        }

    def _handle_explain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Explain selected code.

        Params:
            - code: Selected code
            - file: File path (for context)
            - language: Programming language
        """
        code = params.get("code", "")
        language = params.get("language", "")

        prompt = f"""Explain this {language} code concisely:

```{language}
{code}
```

Provide:
1. What the code does (1-2 sentences)
2. Key concepts used
3. Any potential issues
"""

        # Would call Gemini here
        return {
            "explanation": "Gemini would provide code explanation here",
            "concepts": [],
            "issues": []
        }

    def _handle_generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate code from description.

        Params:
            - description: What to generate
            - file: Target file
            - language: Programming language
            - context: Surrounding code for context
        """
        description = params.get("description", "")
        language = params.get("language", "python")
        context = params.get("context", "")

        prompt = f"""Generate {language} code for: {description}

Context:
{context}

Requirements:
- Follow the existing code style
- Include appropriate error handling
- Add brief comments for complex logic

Return only the code, no explanations.
"""

        # Would call Gemini here
        return {
            "code": f"# Generated code for: {description}\n# Gemini would provide actual code here",
            "language": language
        }

    def _handle_refactor(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest refactoring for code.

        Params:
            - code: Code to refactor
            - type: Refactoring type (rename, extract, inline, etc.)
            - options: Refactoring options
        """
        code = params.get("code", "")
        refactor_type = params.get("type", "improve")

        prompt = f"""Suggest refactoring for this code:

```
{code}
```

Refactoring type: {refactor_type}

Provide the refactored code and explain the changes.
"""

        return {
            "refactored": code,  # Would be Gemini's output
            "changes": ["Gemini would list changes here"]
        }

    def _handle_fix(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest fixes for code issues.

        Params:
            - code: Code with issues
            - diagnostics: List of diagnostics/errors
        """
        code = params.get("code", "")
        diagnostics = params.get("diagnostics", [])

        prompt = f"""Fix the issues in this code:

```
{code}
```

Issues:
{json.dumps(diagnostics, indent=2)}

Provide the fixed code.
"""

        return {
            "fixes": [
                {
                    "title": "Fix suggested by Gemini",
                    "edits": []
                }
            ]
        }

    def _handle_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a command.

        Params:
            - command: Command to execute
            - args: Command arguments
        """
        command = params.get("command", "")
        args = params.get("args", {})

        # Route to appropriate handler
        commands = {
            "gemini.chat": self._cmd_chat,
            "gemini.explain": lambda a: self._handle_explain(a),
            "gemini.generate": lambda a: self._handle_generate(a),
        }

        handler = commands.get(command)
        if handler:
            return handler(args)

        return {"error": f"Unknown command: {command}"}

    def _cmd_chat(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Handle chat command."""
        message = args.get("message", "")
        # Would send to Gemini
        return {"response": f"Response to: {message}"}

    def _handle_search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search codebase with natural language.

        Params:
            - query: Natural language search query
            - scope: Search scope (file, directory, project)
        """
        query = params.get("query", "")
        scope = params.get("scope", "project")

        prompt = f"""Search the codebase for: {query}

Scope: {scope}

Convert this to appropriate grep/ripgrep patterns and return results.
"""

        return {
            "results": [],
            "query_interpreted": f"Searching for: {query}"
        }


class JSONRPCServer:
    """
    JSON-RPC 2.0 server for IDE communication.

    Can run over:
    - stdio (for extension subprocess)
    - TCP socket (for remote/debugging)
    """

    def __init__(self, handler: IDEHandler):
        self.handler = handler
        self.running = False

    def handle_message(self, message: str) -> str:
        """
        Handle a JSON-RPC message.

        Args:
            message: JSON-RPC request string

        Returns:
            JSON-RPC response string
        """
        try:
            request = json.loads(message)
        except json.JSONDecodeError:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32700, "message": "Parse error"},
                "id": None
            })

        # Validate JSON-RPC structure
        if request.get("jsonrpc") != "2.0":
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request"},
                "id": request.get("id")
            })

        method = request.get("method", "")
        params = request.get("params", {})
        request_id = request.get("id")

        # Handle the request
        result = self.handler.handle_request(method, params)

        # Build response
        if "error" in result:
            return json.dumps({
                "jsonrpc": "2.0",
                "error": {"code": -32000, "message": result["error"]},
                "id": request_id
            })

        return json.dumps({
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        })

    def run_stdio(self):
        """Run server using stdio (for extension subprocess)."""
        self.running = True

        while self.running:
            try:
                # Read content length header
                line = sys.stdin.readline()
                if not line:
                    break

                if line.startswith("Content-Length:"):
                    length = int(line.split(":")[1].strip())
                    sys.stdin.readline()  # Empty line
                    content = sys.stdin.read(length)

                    response = self.handle_message(content)

                    # Write response
                    sys.stdout.write(f"Content-Length: {len(response)}\r\n\r\n")
                    sys.stdout.write(response)
                    sys.stdout.flush()

            except Exception as e:
                sys.stderr.write(f"Error: {e}\n")
                break

    def run_tcp(self, host: str = "localhost", port: int = 9999):
        """Run server using TCP socket."""

        class TCPHandler(socketserver.BaseRequestHandler):
            server_ref = self

            def handle(self):
                while True:
                    try:
                        data = self.request.recv(4096)
                        if not data:
                            break

                        # Simple protocol: newline-delimited JSON
                        for line in data.decode().strip().split('\n'):
                            if line:
                                response = self.server_ref.handle_message(line)
                                self.request.sendall((response + '\n').encode())
                    except Exception:
                        break

        self.running = True
        with socketserver.TCPServer((host, port), TCPHandler) as server:
            print(f"IDE server listening on {host}:{port}")
            server.serve_forever()

    def stop(self):
        """Stop the server."""
        self.running = False


def create_vscode_extension_template() -> Dict[str, Any]:
    """
    Generate VS Code extension package.json template.

    Returns a template that can be used to create a VS Code extension
    that connects to this server.
    """
    return {
        "name": "gemini-agentic",
        "displayName": "Gemini Agentic CLI",
        "description": "AI-powered code assistance using Gemini",
        "version": "0.1.0",
        "engines": {
            "vscode": "^1.74.0"
        },
        "categories": ["Other"],
        "activationEvents": ["onStartupFinished"],
        "main": "./out/extension.js",
        "contributes": {
            "commands": [
                {
                    "command": "gemini.chat",
                    "title": "Gemini: Chat"
                },
                {
                    "command": "gemini.explain",
                    "title": "Gemini: Explain Selection"
                },
                {
                    "command": "gemini.generate",
                    "title": "Gemini: Generate Code"
                },
                {
                    "command": "gemini.refactor",
                    "title": "Gemini: Suggest Refactoring"
                }
            ],
            "menus": {
                "editor/context": [
                    {
                        "command": "gemini.explain",
                        "when": "editorHasSelection",
                        "group": "gemini"
                    }
                ]
            },
            "configuration": {
                "title": "Gemini Agentic",
                "properties": {
                    "gemini.serverPath": {
                        "type": "string",
                        "default": "",
                        "description": "Path to the Gemini CLI server"
                    }
                }
            }
        }
    }


# Tool functions for registry
def start_ide_server(port: int = 9999) -> tuple[bool, str]:
    """Start the IDE integration server."""
    handler = IDEHandler()
    server = JSONRPCServer(handler)

    # Start in background thread
    thread = threading.Thread(target=server.run_tcp, args=("localhost", port), daemon=True)
    thread.start()

    return True, f"IDE server started on port {port}"


def get_extension_template() -> tuple[bool, str]:
    """Get VS Code extension template."""
    template = create_vscode_extension_template()
    return True, json.dumps(template, indent=2)


# Tool registry
IDE_SERVER_TOOLS = {
    "start_ide_server": start_ide_server,
    "get_extension_template": get_extension_template,
}


# CLI entry point
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Gemini IDE Server")
    parser.add_argument("--mode", choices=["stdio", "tcp"], default="tcp")
    parser.add_argument("--port", type=int, default=9999)
    args = parser.parse_args()

    handler = IDEHandler()
    server = JSONRPCServer(handler)

    if args.mode == "stdio":
        server.run_stdio()
    else:
        server.run_tcp(port=args.port)
