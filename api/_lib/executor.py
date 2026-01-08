"""
Code Execution Module using Piston API

Piston is a self-hosted code execution engine supporting 50+ languages.
https://github.com/engineer-man/piston

Setup:
  docker run -d --name piston -p 2000:2000 --privileged ghcr.io/engineer-man/piston
  docker exec piston piston install python
  docker exec piston piston install gcc
"""

import os
import json
import httpx
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

# Default Piston URL (can be overridden via environment variable)
PISTON_URL = os.environ.get("PISTON_URL", "http://localhost:2000")

# Execution limits
DEFAULT_TIMEOUT = 10  # seconds for API call
DEFAULT_RUN_TIMEOUT = 3000  # milliseconds for code execution (Piston limit)
DEFAULT_COMPILE_TIMEOUT = 10000  # milliseconds for compilation
DEFAULT_MEMORY_LIMIT = 128 * 1024 * 1024  # 128MB


@dataclass
class ExecutionResult:
    """Result of code execution"""
    success: bool
    stdout: str
    stderr: str
    exit_code: int
    compile_output: Optional[str] = None
    error: Optional[str] = None
    timed_out: bool = False


class PistonClient:
    """Client for Piston code execution API"""

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or PISTON_URL
        self._runtimes_cache: Optional[Dict[str, Any]] = None

    def is_available(self) -> bool:
        """Check if Piston server is available"""
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/v2/runtimes")
                return response.status_code == 200
        except Exception:
            return False

    def get_runtimes(self) -> Dict[str, Any]:
        """Get available language runtimes"""
        if self._runtimes_cache is not None:
            return self._runtimes_cache

        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(f"{self.base_url}/api/v2/runtimes")
                response.raise_for_status()
                runtimes = response.json()
                # Index by language name
                self._runtimes_cache = {r["language"]: r for r in runtimes}
                return self._runtimes_cache
        except Exception as e:
            return {}

    def get_language_version(self, language: str) -> Optional[str]:
        """Get the installed version of a language"""
        runtimes = self.get_runtimes()
        if language in runtimes:
            return runtimes[language]["version"]
        return None

    def execute(
        self,
        language: str,
        code: str,
        stdin: str = "",
        args: Optional[list] = None,
        run_timeout: int = DEFAULT_RUN_TIMEOUT,
        compile_timeout: int = DEFAULT_COMPILE_TIMEOUT,
        memory_limit: int = DEFAULT_MEMORY_LIMIT,
    ) -> ExecutionResult:
        """
        Execute code using Piston API

        Args:
            language: Language name (e.g., "python", "c++", "cpp")
            code: Source code to execute
            stdin: Standard input to provide
            args: Command line arguments
            run_timeout: Execution timeout in milliseconds
            compile_timeout: Compilation timeout in milliseconds (for compiled languages)
            memory_limit: Memory limit in bytes

        Returns:
            ExecutionResult with stdout, stderr, and status
        """
        # Normalize language name
        lang = self._normalize_language(language)

        # Get language version
        version = self.get_language_version(lang)
        if not version:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error=f"Language '{language}' not available on Piston server"
            )

        # Build request payload
        payload = {
            "language": lang,
            "version": version,
            "files": [{"content": code}],
            "stdin": stdin,
            "args": args or [],
            "run_timeout": run_timeout,
            "compile_timeout": compile_timeout,
            "compile_memory_limit": memory_limit,
            "run_memory_limit": memory_limit,
        }

        try:
            print(f"\n--- PISTON REQUEST ---")
            print(f"Language: {lang}, Version: {version}")
            print(f"Code length: {len(code)} chars")
            print(f"Stdin length: {len(stdin)} chars")
            print(f"Stdin preview: {stdin[:200]}..." if len(stdin) > 200 else f"Stdin: {stdin}")

            with httpx.Client(timeout=DEFAULT_TIMEOUT + (run_timeout + compile_timeout) / 1000) as client:
                response = client.post(
                    f"{self.base_url}/api/v2/execute",
                    json=payload
                )
                if response.status_code != 200:
                    print(f"Piston error response: {response.text}")
                response.raise_for_status()
                result = response.json()

                # Check for compilation errors (for compiled languages)
                compile_output = None
                if "compile" in result and result["compile"]:
                    compile_result = result["compile"]
                    if compile_result.get("code") != 0:
                        return ExecutionResult(
                            success=False,
                            stdout=compile_result.get("stdout", ""),
                            stderr=compile_result.get("stderr", ""),
                            exit_code=compile_result.get("code", -1),
                            compile_output=compile_result.get("output", ""),
                            error="Compilation failed"
                        )
                    compile_output = compile_result.get("output", "")

                # Get run results
                run_result = result.get("run", {})
                timed_out = run_result.get("signal") == "SIGKILL"

                return ExecutionResult(
                    success=run_result.get("code", -1) == 0,
                    stdout=run_result.get("stdout", ""),
                    stderr=run_result.get("stderr", ""),
                    exit_code=run_result.get("code", -1),
                    compile_output=compile_output,
                    timed_out=timed_out
                )

        except httpx.TimeoutException:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error="Request timed out",
                timed_out=True
            )
        except httpx.HTTPStatusError as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error=f"HTTP error: {e.response.status_code}"
            )
        except Exception as e:
            return ExecutionResult(
                success=False,
                stdout="",
                stderr="",
                exit_code=-1,
                error=str(e)
            )

    def execute_python(self, code: str, stdin: str = "", **kwargs) -> ExecutionResult:
        """Execute Python code"""
        return self.execute("python", code, stdin, **kwargs)

    def execute_cpp(self, code: str, stdin: str = "", **kwargs) -> ExecutionResult:
        """Execute C++ code"""
        return self.execute("c++", code, stdin, **kwargs)

    def _normalize_language(self, language: str) -> str:
        """Normalize language name for Piston API"""
        aliases = {
            "python3": "python",
            "py": "python",
            "cpp": "c++",
            "g++": "c++",
            "gcc": "c",
        }
        return aliases.get(language.lower(), language.lower())


def verify_exploit(
    code: str,
    exploit_input: str,
    expected_output: str,
    language: str = "python",
    piston_url: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Verify if an exploit input triggers incorrect behavior.

    Args:
        code: The (potentially backdoored) code to test
        exploit_input: The crafted input that should trigger the backdoor
        expected_output: The correct output for this input
        language: Programming language of the code
        piston_url: Optional Piston server URL

    Returns:
        Tuple of (exploit_works: bool, actual_output: str)
        exploit_works is True if the code produces DIFFERENT output than expected
    """
    client = PistonClient(piston_url)

    if not client.is_available():
        return False, "Piston server not available"

    result = client.execute(language, code, exploit_input)

    if not result.success and result.error:
        # Execution failed - could be the backdoor causing a crash
        return True, f"Execution failed: {result.error}"

    if result.timed_out:
        # Timeout could indicate an infinite loop backdoor
        return True, "Execution timed out"

    actual_output = result.stdout.strip()
    expected_clean = expected_output.strip()

    # Exploit is verified if output differs from expected
    exploit_works = actual_output != expected_clean

    return exploit_works, actual_output


def test_solution_correctness(
    code: str,
    test_cases: list,
    language: str = "python",
    piston_url: Optional[str] = None
) -> Tuple[bool, int, int]:
    """
    Test if a solution passes all test cases.

    Args:
        code: The code to test
        test_cases: List of {"input": str, "output": str} dicts
        language: Programming language
        piston_url: Optional Piston server URL

    Returns:
        Tuple of (all_passed: bool, passed_count: int, total_count: int)
    """
    client = PistonClient(piston_url)

    if not client.is_available():
        return False, 0, len(test_cases)

    passed = 0
    for tc in test_cases:
        result = client.execute(language, code, tc["input"])

        if result.success:
            actual = result.stdout.strip()
            expected = tc["output"].strip()
            if actual == expected:
                passed += 1

    return passed == len(test_cases), passed, len(test_cases)


# Global client instance
_default_client: Optional[PistonClient] = None


def get_piston_client() -> PistonClient:
    """Get or create the default Piston client"""
    global _default_client
    if _default_client is None:
        _default_client = PistonClient()
    return _default_client
