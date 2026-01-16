"""
Python Code Execution Sandbox

Gemini has a built-in Python sandbox for code execution:
- 30-second STRICT timeout
- Optimized for mathematical computations, data analysis
- Useful for code validation

Use cases:
- Complex calculations Gemini can't do in-context
- Data processing and transformation
- Validating generated code snippets
- Mathematical proofs and derivations
"""

import subprocess
import sys
import os
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
import json


# Gemini script location
GEMINI_SCRIPT = Path.home() / ".claude" / "scripts" / "gemini-account.sh"

# Maximum execution time (Gemini sandbox limit)
MAX_EXECUTION_SECONDS = 30


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


def call_gemini(query: str, account: int = 1, timeout: int = 60) -> Tuple[bool, str]:
    """Call Gemini with timeout for code execution."""
    if not GEMINI_SCRIPT.exists():
        return False, f"gemini-account.sh not found"

    try:
        if sys.platform == 'win32':
            git_bash = get_git_bash()
            if not git_bash:
                return False, "Git Bash not found"
            cmd = [str(git_bash), str(GEMINI_SCRIPT), str(account), query]
        else:
            cmd = ["bash", str(GEMINI_SCRIPT), str(account), query]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.getcwd()
        )

        if result.returncode != 0:
            error = result.stderr.strip() if result.stderr else "Unknown error"
            return False, f"Error: {error}"

        response = result.stdout.strip()
        return bool(response), response or "Empty response"

    except subprocess.TimeoutExpired:
        return False, "Timeout exceeded"
    except Exception as e:
        return False, f"Error: {e}"


def execute_python(
    code: str,
    description: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Execute Python code in Gemini's built-in sandbox.

    Args:
        code: Python code to execute
        description: Optional description of what the code does
        account: Gemini account to use (1 or 2)

    Returns:
        Tuple of (success: bool, execution_result: str)

    IMPORTANT:
        - Maximum execution time: 30 seconds (STRICT)
        - Optimize code for efficiency
        - Avoid infinite loops or long operations
    """
    desc_note = f"\nDescription: {description}" if description else ""

    prompt = f"""Execute this Python code in the sandbox:
{desc_note}

```python
{code}
```

Execute the code and return:
1. stdout output
2. Return value (if any)
3. Any errors or exceptions
4. Execution time

Format:
```
STDOUT:
[output]

RETURN VALUE:
[value]

ERRORS:
[any errors, or "None"]

EXECUTION TIME:
[time in seconds]
```

Note: Code must complete within 30 seconds."""

    return call_gemini(prompt, account, timeout=60)


def calculate(
    expression: str,
    precision: int = 10,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Perform mathematical calculations using Python.

    Args:
        expression: Mathematical expression or calculation
        precision: Decimal precision for results
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, result: str)
    """
    prompt = f"""Calculate the following using Python:

Expression: {expression}

Use appropriate Python libraries (math, decimal, numpy if needed).
Return result with up to {precision} decimal places precision.

Provide:
1. The calculation setup
2. The result
3. Verification or alternate method if applicable
4. Any mathematical notes or caveats"""

    return call_gemini(prompt, account)


def analyze_data(
    data: str,
    analysis: str = "descriptive",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Analyze data using Python's data analysis capabilities.

    Args:
        data: Data as CSV, JSON, or Python list/dict literal
        analysis: Type of analysis ("descriptive", "correlation", "regression", "custom")
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, analysis_result: str)
    """
    analysis_code = {
        "descriptive": """
- Count, mean, std, min, max, quartiles
- Distribution shape
- Missing value analysis""",
        "correlation": """
- Correlation matrix
- Significant correlations
- Visualization description""",
        "regression": """
- Linear regression fit
- R-squared
- Coefficients and significance""",
        "custom": "Perform the most appropriate analysis for this data type"
    }

    prompt = f"""Analyze this data using Python:

Data:
{data}

Analysis type: {analysis}
{analysis_code.get(analysis, analysis_code['custom'])}

Write and execute Python code to analyze this data.
Use pandas and scipy as appropriate.

Return:
1. Code used
2. Analysis results
3. Interpretation
4. Visualizations (described if can't display)"""

    return call_gemini(prompt, account, timeout=90)


def validate_code(
    code: str,
    language: str = "python",
    test_inputs: list = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Validate code by executing it with test inputs.

    Args:
        code: Code to validate
        language: Programming language (currently only Python supported)
        test_inputs: Optional list of test inputs
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, validation_result: str)
    """
    if language.lower() != "python":
        return False, f"Only Python code execution is supported, got: {language}"

    test_note = ""
    if test_inputs:
        test_note = f"\nTest with these inputs: {test_inputs}"

    prompt = f"""Validate this {language} code by executing it:

```{language}
{code}
```
{test_note}

1. Check syntax validity
2. Execute the code
3. Test with provided inputs (if any)
4. Test with edge cases
5. Report any errors or issues

Provide:
- Syntax check: PASS/FAIL
- Execution: PASS/FAIL
- Test results: for each test case
- Issues found: list of problems
- Suggestions: improvements recommended"""

    return call_gemini(prompt, account, timeout=90)


def solve_equation(
    equation: str,
    variable: str = "x",
    method: str = "auto",
    account: int = 1
) -> Tuple[bool, str]:
    """
    Solve mathematical equations using Python.

    Args:
        equation: Equation to solve (e.g., "x**2 - 4 = 0")
        variable: Variable to solve for
        method: "symbolic" (sympy), "numeric" (scipy), or "auto"
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, solution: str)
    """
    prompt = f"""Solve this equation using Python:

Equation: {equation}
Solve for: {variable}
Method preference: {method}

Use sympy for symbolic solutions or scipy for numeric solutions.

Provide:
1. Solution(s)
2. Verification by substitution
3. Method used
4. Domain restrictions (if any)
5. Step-by-step solution (brief)"""

    return call_gemini(prompt, account)


def run_simulation(
    description: str,
    iterations: int = 1000,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Run a Monte Carlo or other simulation.

    Args:
        description: Description of what to simulate
        iterations: Number of iterations (keep reasonable for 30s limit)
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, simulation_results: str)
    """
    # Cap iterations to avoid timeout
    iterations = min(iterations, 100000)

    prompt = f"""Run a simulation in Python:

Simulation: {description}
Iterations: {iterations}

IMPORTANT: Code must complete within 30 seconds.

Write efficient Python code to simulate this scenario.

Provide:
1. Simulation code
2. Results summary
3. Distribution of outcomes
4. Confidence intervals
5. Key insights"""

    return call_gemini(prompt, account, timeout=60)


def generate_and_test(
    specification: str,
    test_cases: list = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Generate Python code from specification and test it.

    Args:
        specification: Description of what the code should do
        test_cases: Optional list of test cases as dicts with 'input' and 'expected'
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, code_and_results: str)
    """
    test_note = ""
    if test_cases:
        test_note = f"\n\nTest cases:\n{json.dumps(test_cases, indent=2)}"

    prompt = f"""Generate Python code from this specification:

Specification: {specification}
{test_note}

1. Generate clean, efficient Python code
2. Execute the code
3. Run all test cases
4. Verify correctness

Provide:
- Generated code
- Test results (PASS/FAIL for each)
- Any issues or edge cases found
- Performance notes"""

    return call_gemini(prompt, account, timeout=90)


def debug_code(
    code: str,
    error_message: str = None,
    account: int = 1
) -> Tuple[bool, str]:
    """
    Debug Python code by executing and analyzing errors.

    Args:
        code: Code with potential bugs
        error_message: Known error message (if any)
        account: Gemini account to use

    Returns:
        Tuple of (success: bool, debug_result: str)
    """
    error_note = f"\nKnown error: {error_message}" if error_message else ""

    prompt = f"""Debug this Python code:

```python
{code}
```
{error_note}

1. Execute the code to reproduce issues
2. Identify all bugs/errors
3. Provide fixed code
4. Explain each fix

Provide:
- Bugs found: [list]
- Root causes: [explanations]
- Fixed code: [corrected version]
- Verification: [test results of fix]"""

    return call_gemini(prompt, account, timeout=60)


# Tool registry
CODE_EXECUTION_TOOLS = {
    "execute_python": execute_python,
    "calculate": calculate,
    "analyze_data": analyze_data,
    "validate_code": validate_code,
    "solve_equation": solve_equation,
    "run_simulation": run_simulation,
    "generate_and_test": generate_and_test,
    "debug_code": debug_code,
}
