"""Subprocess code execution engine for Python and PowerShell scripts.

Executes scripts safely in subprocesses with configurable timeouts, capturing stdout, stderr,
and return codes to enable LLM self-correction.
"""

import os
import sys
import tempfile
import subprocess
import time
import ast
from typing import Dict, Any, Optional

try:
    from langchain_core.tools import tool
except ImportError:
    def tool(func):
        return func


def validate_python_syntax(code_string: str) -> Dict[str, Any]:
    """Validates Python code syntax using ast.parse().

    Returns:
        Dict with 'valid': bool, 'error': str (if invalid), 'line': int (if invalid).
    """
    try:
        ast.parse(code_string)
        return {"valid": True, "error": None, "line": None}
    except SyntaxError as se:
        return {
            "valid": False,
            "error": f"SyntaxError: {se.msg} at line {se.lineno}, col {se.offset}",
            "line": se.lineno,
            "text": se.text
        }
    except Exception as e:
        return {"valid": False, "error": f"AST Parse Error: {str(e)}", "line": None}



def execute_code(
    script: str,
    language: str = "python",
    timeout: int = 30,
    cwd: Optional[str] = None
) -> Dict[str, Any]:
    """Executes code in Python or PowerShell with subprocess controls.

    Args:
        script: Source code string to execute.
        language: Execution language ('python', 'py', 'powershell', 'ps1').
        timeout: Execution timeout limit in seconds (default 30).
        cwd: Current working directory for execution.

    Returns:
        Dict containing returncode, stdout, stderr, execution_time, timed_out flag, and status.
    """
    lang = language.lower().strip()
    suffix = ".py" if lang in ("python", "py") else ".ps1"
    
    if cwd is None:
        cwd = os.getcwd()

    temp_script = None
    start_time = time.time()
    
    try:
        # Create temp file to avoid CLI escaping issues with multi-line scripts
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8") as f:
            f.write(script)
            temp_script = f.name

        if lang in ("python", "py"):
            cmd = [sys.executable, temp_script]
        elif lang in ("powershell", "ps1"):
            cmd = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", temp_script]
        else:
            return {
                "returncode": -1,
                "stdout": "",
                "stderr": f"Unsupported language: '{language}'. Supported: 'python', 'powershell'.",
                "execution_time": 0.0,
                "timed_out": False,
                "success": False
            }

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=timeout
        )
        
        exec_time = round(time.time() - start_time, 3)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "execution_time": exec_time,
            "timed_out": False,
            "success": (result.returncode == 0)
        }

    except subprocess.TimeoutExpired as te:
        exec_time = round(time.time() - start_time, 3)
        stdout_str = te.stdout if isinstance(te.stdout, str) else (te.stdout.decode("utf-8", "replace") if te.stdout else "")
        stderr_str = te.stderr if isinstance(te.stderr, str) else (te.stderr.decode("utf-8", "replace") if te.stderr else "")
        return {
            "returncode": -1,
            "stdout": stdout_str,
            "stderr": f"{stderr_str}\n[Execution Timed Out after {timeout} seconds]",
            "execution_time": exec_time,
            "timed_out": True,
            "success": False
        }
    except Exception as e:
        exec_time = round(time.time() - start_time, 3)
        return {
            "returncode": -1,
            "stdout": "",
            "stderr": f"System Execution Error: {type(e).__name__}: {str(e)}",
            "execution_time": exec_time,
            "timed_out": False,
            "success": False
        }
    finally:
        if temp_script and os.path.exists(temp_script):
            try:
                os.remove(temp_script)
            except OSError:
                pass


def format_execution_result(res: Dict[str, Any], script_snippet: str = "") -> str:
    """Formats execution result dictionary into a clean markdown block for LLM evaluation.

    Args:
        res: Result dictionary returned by execute_code.
        script_snippet: Brief context snippet of script executed.

    Returns:
        Formatted output string.
    """
    status = "SUCCESS" if res["success"] else ("TIMED OUT" if res["timed_out"] else "FAILED")
    output = [
        f"=== Code Execution Result ({status}) ===",
        f"Return Code: {res['returncode']} | Execution Time: {res['execution_time']}s"
    ]
    
    if res["stdout"].strip():
        output.append("\n--- STDOUT ---")
        output.append(res["stdout"].strip())
    else:
        output.append("\n--- STDOUT ---\n(empty)")

    if res["stderr"].strip():
        output.append("\n--- STDERR ---")
        output.append(res["stderr"].strip())

    if not res["success"]:
        output.append("\n[Self-Correction Hint: Review STDERR and returncode above to diagnose script error]")

    return "\n".join(output)


@tool
def run_python_script(script: str, timeout: int = 30) -> str:
    """Executes a Python script in a subprocess with timeout control and returns formatted stdout/stderr.

    Args:
        script: Python code to execute.
        timeout: Timeout limit in seconds (default 30).

    Returns:
        Formatted execution details including return code, stdout, stderr, and timing.
    """
    res = execute_code(script=script, language="python", timeout=timeout)
    return format_execution_result(res, script)


@tool
def run_powershell_script(script: str, timeout: int = 30) -> str:
    """Executes a PowerShell script in a subprocess with timeout control and returns formatted stdout/stderr.

    Args:
        script: PowerShell code to execute.
        timeout: Timeout limit in seconds (default 30).

    Returns:
        Formatted execution details including return code, stdout, stderr, and timing.
    """
    res = execute_code(script=script, language="powershell", timeout=timeout)
    return format_execution_result(res, script)
