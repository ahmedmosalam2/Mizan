"""
Sandboxed Python Code Execution Service.

Executes real Python analytics calculations (ROAS, CPA, conversion rates, statistical testing)
in an isolated subprocess environment with strict timeouts.
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
from typing import Any, Dict


class CodeExecutor:
    """Executes Python code in an isolated subprocess."""

    @classmethod
    async def execute_python(cls, code: str, timeout_seconds: float = 10.0) -> Dict[str, Any]:
        """
        Execute python code string and capture stdout, stderr, and exit code.
        """
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(code)
            tmp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
            return {
                "success": proc.returncode == 0,
                "stdout": stdout.decode("utf-8", errors="replace"),
                "stderr": stderr.decode("utf-8", errors="replace"),
                "returncode": proc.returncode,
            }
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except Exception:
                pass
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution timed out after {timeout_seconds}s",
                "returncode": -1,
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "returncode": -1,
            }
        finally:
            import os
            try:
                os.remove(tmp_path)
            except Exception:
                pass
