import math
import sys
import io
import contextlib
from typing import Dict, Any

class PythonSandbox:
    """
    Lightweight, isolated Python execution sandbox for structured tabular
    calculations and quantitative verification. Prevents LLM arithmetic hallucinations.
    """

    SAFE_BUILTINS = {
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "len": len,
        "int": int,
        "float": float,
        "str": str,
        "list": list,
        "dict": dict,
        "range": range,
        "print": print,
        "math": math
    }

    @classmethod
    def execute_code(cls, code: str) -> Dict[str, Any]:
        """
        Executes a short snippet of Python calculation code in an isolated scope.
        Returns: {'output': str, 'success': bool, 'error': str | None}
        """
        clean_code = code.strip().replace("```python", "").replace("```", "")

        # Block dangerous calls
        blocked_keywords = ["import os", "import sys", "subprocess", "open(", "eval(", "exec(", "__import__", "shutil"]
        for b in blocked_keywords:
            if b in clean_code:
                return {"success": False, "output": "", "error": f"Security restriction: '{b}' is not allowed in sandbox."}

        stdout_capture = io.StringIO()
        safe_globals = {"__builtins__": cls.SAFE_BUILTINS, "math": math}
        safe_locals = {}

        try:
            with contextlib.redirect_stdout(stdout_capture):
                # Try evaluating as an expression first
                try:
                    result = eval(clean_code, safe_globals, safe_locals)
                    if result is not None:
                        print(result)
                except SyntaxError:
                    # Execute as statement
                    exec(clean_code, safe_globals, safe_locals)

            output = stdout_capture.getvalue().strip()
            return {"success": True, "output": output, "error": None}
        except Exception as e:
            return {"success": False, "output": "", "error": f"Execution error: {str(e)}"}
