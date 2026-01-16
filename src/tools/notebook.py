"""
Jupyter Notebook Tools

Enables Gemini to work with Jupyter notebooks (.ipynb files):
- Read and analyze notebook content
- Edit cells (code and markdown)
- Insert and delete cells
- Execute cells and capture output
- Convert between formats

Mirrors Claude Code's NotebookEdit capability for parity.
"""

import json
import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any, Union


def read_notebook(path: str) -> Tuple[bool, str]:
    """
    Read and parse a Jupyter notebook.

    Args:
        path: Path to the .ipynb file

    Returns:
        Tuple of (success: bool, notebook_summary: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    if not notebook_path.exists():
        return False, f"Notebook not found: {path}"

    if notebook_path.suffix != '.ipynb':
        return False, f"Not a Jupyter notebook: {path}"

    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        cells = notebook.get('cells', [])
        metadata = notebook.get('metadata', {})

        # Build summary
        lines = [
            f"Notebook: {notebook_path.name}",
            f"Cells: {len(cells)}",
            f"Kernel: {metadata.get('kernelspec', {}).get('display_name', 'Unknown')}",
            f"Language: {metadata.get('language_info', {}).get('name', 'Unknown')}",
            "",
            "--- Cells ---"
        ]

        for i, cell in enumerate(cells):
            cell_type = cell.get('cell_type', 'unknown')
            source = ''.join(cell.get('source', []))

            # Truncate long cells
            preview = source[:200] + '...' if len(source) > 200 else source
            preview = preview.replace('\n', '\\n')

            outputs = cell.get('outputs', [])
            output_info = f" [{len(outputs)} outputs]" if outputs else ""

            lines.append(f"[{i}] {cell_type}{output_info}: {preview}")

        return True, '\n'.join(lines)

    except json.JSONDecodeError as e:
        return False, f"Invalid notebook JSON: {e}"
    except Exception as e:
        return False, f"Error reading notebook: {e}"


def get_cell(path: str, cell_index: int) -> Tuple[bool, str]:
    """
    Get the content of a specific cell.

    Args:
        path: Path to the notebook
        cell_index: Index of the cell (0-based)

    Returns:
        Tuple of (success: bool, cell_content: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        cells = notebook.get('cells', [])

        if cell_index < 0 or cell_index >= len(cells):
            return False, f"Cell index {cell_index} out of range (0-{len(cells)-1})"

        cell = cells[cell_index]
        cell_type = cell.get('cell_type', 'unknown')
        source = ''.join(cell.get('source', []))
        outputs = cell.get('outputs', [])

        result = [
            f"Cell [{cell_index}] - {cell_type}",
            "--- Source ---",
            source,
        ]

        if outputs:
            result.append("\n--- Outputs ---")
            for i, output in enumerate(outputs):
                output_type = output.get('output_type', 'unknown')
                if output_type == 'stream':
                    text = ''.join(output.get('text', []))
                    result.append(f"[stream] {text}")
                elif output_type == 'execute_result':
                    data = output.get('data', {})
                    if 'text/plain' in data:
                        result.append(f"[result] {''.join(data['text/plain'])}")
                elif output_type == 'error':
                    ename = output.get('ename', 'Error')
                    evalue = output.get('evalue', '')
                    result.append(f"[error] {ename}: {evalue}")

        return True, '\n'.join(result)

    except Exception as e:
        return False, f"Error reading cell: {e}"


def edit_cell(
    path: str,
    cell_index: int,
    new_content: str,
    cell_type: str = None
) -> Tuple[bool, str]:
    """
    Edit a cell in a Jupyter notebook.

    Args:
        path: Path to the notebook
        cell_index: Index of the cell to edit (0-based)
        new_content: New source content for the cell
        cell_type: Optional new cell type ('code' or 'markdown')

    Returns:
        Tuple of (success: bool, message: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        cells = notebook.get('cells', [])

        if cell_index < 0 or cell_index >= len(cells):
            return False, f"Cell index {cell_index} out of range (0-{len(cells)-1})"

        # Update the cell
        cells[cell_index]['source'] = new_content.split('\n')

        # Update cell type if specified
        if cell_type and cell_type in ('code', 'markdown', 'raw'):
            cells[cell_index]['cell_type'] = cell_type
            # Clear outputs if converting to non-code cell
            if cell_type != 'code':
                cells[cell_index].pop('outputs', None)
                cells[cell_index].pop('execution_count', None)
            else:
                if 'outputs' not in cells[cell_index]:
                    cells[cell_index]['outputs'] = []
                if 'execution_count' not in cells[cell_index]:
                    cells[cell_index]['execution_count'] = None

        # Write back
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=1)

        return True, f"Cell [{cell_index}] updated successfully"

    except Exception as e:
        return False, f"Error editing cell: {e}"


def insert_cell(
    path: str,
    cell_index: int,
    content: str,
    cell_type: str = 'code'
) -> Tuple[bool, str]:
    """
    Insert a new cell at a specific position.

    Args:
        path: Path to the notebook
        cell_index: Index where to insert (cells after shift down)
        content: Content for the new cell
        cell_type: Type of cell ('code', 'markdown', 'raw')

    Returns:
        Tuple of (success: bool, message: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    if cell_type not in ('code', 'markdown', 'raw'):
        return False, f"Invalid cell type: {cell_type}. Use 'code', 'markdown', or 'raw'"

    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        cells = notebook.get('cells', [])

        # Clamp index to valid range
        insert_index = max(0, min(cell_index, len(cells)))

        # Create new cell
        new_cell = {
            'cell_type': cell_type,
            'source': content.split('\n'),
            'metadata': {}
        }

        if cell_type == 'code':
            new_cell['outputs'] = []
            new_cell['execution_count'] = None

        # Insert
        cells.insert(insert_index, new_cell)

        # Write back
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=1)

        return True, f"Inserted {cell_type} cell at index [{insert_index}]"

    except Exception as e:
        return False, f"Error inserting cell: {e}"


def delete_notebook_cell(path: str, cell_index: int) -> Tuple[bool, str]:
    """
    Delete a cell from the notebook.

    Args:
        path: Path to the notebook
        cell_index: Index of the cell to delete

    Returns:
        Tuple of (success: bool, message: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        cells = notebook.get('cells', [])

        if cell_index < 0 or cell_index >= len(cells):
            return False, f"Cell index {cell_index} out of range (0-{len(cells)-1})"

        deleted_type = cells[cell_index].get('cell_type', 'unknown')
        del cells[cell_index]

        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=1)

        return True, f"Deleted {deleted_type} cell at index [{cell_index}]"

    except Exception as e:
        return False, f"Error deleting cell: {e}"


def move_cell(path: str, from_index: int, to_index: int) -> Tuple[bool, str]:
    """
    Move a cell to a new position.

    Args:
        path: Path to the notebook
        from_index: Current index of the cell
        to_index: Target index for the cell

    Returns:
        Tuple of (success: bool, message: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        cells = notebook.get('cells', [])

        if from_index < 0 or from_index >= len(cells):
            return False, f"Source index {from_index} out of range"

        # Remove from old position
        cell = cells.pop(from_index)

        # Adjust target index if needed
        if to_index > from_index:
            to_index -= 1
        to_index = max(0, min(to_index, len(cells)))

        # Insert at new position
        cells.insert(to_index, cell)

        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=1)

        return True, f"Moved cell from [{from_index}] to [{to_index}]"

    except Exception as e:
        return False, f"Error moving cell: {e}"


def execute_notebook(
    path: str,
    timeout: int = 300,
    kernel: str = None
) -> Tuple[bool, str]:
    """
    Execute all cells in a notebook using nbconvert.

    Requires: jupyter nbconvert installed (pip install nbconvert)

    Args:
        path: Path to the notebook
        timeout: Timeout per cell in seconds
        kernel: Kernel to use (defaults to notebook's kernel)

    Returns:
        Tuple of (success: bool, execution_result: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    if not notebook_path.exists():
        return False, f"Notebook not found: {path}"

    # Build command as list for subprocess (safer than shell string)
    cmd = [
        sys.executable, '-m', 'nbconvert',
        '--to', 'notebook',
        '--execute',
        '--inplace',
        f'--ExecutePreprocessor.timeout={timeout}',
        str(notebook_path)
    ]

    if kernel:
        cmd.append(f'--ExecutePreprocessor.kernel_name={kernel}')

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout + 60  # Extra time for startup
        )

        if result.returncode == 0:
            return True, f"Notebook executed successfully. Check outputs in: {notebook_path}"
        else:
            error = result.stderr or result.stdout or "Unknown error"
            return False, f"Execution failed: {error}"

    except subprocess.TimeoutExpired:
        return False, f"Notebook execution timed out after {timeout}s"
    except FileNotFoundError:
        return False, "nbconvert not installed. Run: pip install nbconvert"
    except Exception as e:
        return False, f"Error executing notebook: {e}"


def create_notebook(
    path: str,
    kernel: str = 'python3',
    initial_cells: List[Dict[str, str]] = None
) -> Tuple[bool, str]:
    """
    Create a new Jupyter notebook.

    Args:
        path: Path for the new notebook
        kernel: Kernel name (default: python3)
        initial_cells: Optional list of initial cells
                      [{'type': 'code', 'content': '...'}, ...]

    Returns:
        Tuple of (success: bool, message: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    if notebook_path.exists():
        return False, f"File already exists: {path}"

    if notebook_path.suffix != '.ipynb':
        notebook_path = notebook_path.with_suffix('.ipynb')

    # Create notebook structure
    notebook = {
        'cells': [],
        'metadata': {
            'kernelspec': {
                'display_name': 'Python 3',
                'language': 'python',
                'name': kernel
            },
            'language_info': {
                'name': 'python',
                'version': '3.10'
            }
        },
        'nbformat': 4,
        'nbformat_minor': 5
    }

    # Add initial cells if provided
    if initial_cells:
        for cell_def in initial_cells:
            cell_type = cell_def.get('type', 'code')
            content = cell_def.get('content', '')

            cell = {
                'cell_type': cell_type,
                'source': content.split('\n'),
                'metadata': {}
            }

            if cell_type == 'code':
                cell['outputs'] = []
                cell['execution_count'] = None

            notebook['cells'].append(cell)

    try:
        notebook_path.parent.mkdir(parents=True, exist_ok=True)
        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=1)

        return True, f"Created notebook: {notebook_path}"

    except Exception as e:
        return False, f"Error creating notebook: {e}"


def convert_notebook(
    path: str,
    output_format: str = 'html',
    output_path: str = None
) -> Tuple[bool, str]:
    """
    Convert notebook to another format using nbconvert.

    Requires: nbconvert installed (pip install nbconvert)

    Args:
        path: Path to the notebook
        output_format: Target format (html, pdf, markdown, script, latex)
        output_path: Optional output path (defaults to same location)

    Returns:
        Tuple of (success: bool, message: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    if not notebook_path.exists():
        return False, f"Notebook not found: {path}"

    valid_formats = ['html', 'pdf', 'markdown', 'script', 'latex', 'rst', 'slides']
    if output_format not in valid_formats:
        return False, f"Invalid format: {output_format}. Use: {valid_formats}"

    cmd = [
        sys.executable, '-m', 'nbconvert',
        '--to', output_format,
        str(notebook_path)
    ]

    if output_path:
        cmd.extend(['--output', output_path])

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode == 0:
            return True, f"Converted to {output_format}: {result.stdout or 'Success'}"
        else:
            return False, f"Conversion failed: {result.stderr or result.stdout}"

    except FileNotFoundError:
        return False, "nbconvert not installed. Run: pip install nbconvert"
    except Exception as e:
        return False, f"Error converting notebook: {e}"


def clear_outputs(path: str) -> Tuple[bool, str]:
    """
    Clear all outputs from notebook cells.

    Args:
        path: Path to the notebook

    Returns:
        Tuple of (success: bool, message: str)
    """
    notebook_path = Path(path).expanduser().resolve()

    try:
        with open(notebook_path, 'r', encoding='utf-8') as f:
            notebook = json.load(f)

        cells = notebook.get('cells', [])
        cleared_count = 0

        for cell in cells:
            if cell.get('cell_type') == 'code':
                if cell.get('outputs'):
                    cell['outputs'] = []
                    cleared_count += 1
                cell['execution_count'] = None

        with open(notebook_path, 'w', encoding='utf-8') as f:
            json.dump(notebook, f, indent=1)

        return True, f"Cleared outputs from {cleared_count} cells"

    except Exception as e:
        return False, f"Error clearing outputs: {e}"


# Tool registry
NOTEBOOK_TOOLS = {
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
}
