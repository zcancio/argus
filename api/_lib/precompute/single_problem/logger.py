"""
Collapsible Logger for Single Problem Engine

Provides structured output with one-line summaries that can expand to show details.
Uses ANSI escape codes for terminal formatting.
"""

import sys
from contextlib import contextmanager
from typing import Optional, List
from io import StringIO


class CollapsibleLogger:
    """Logger that captures output into collapsible sections."""

    # ANSI escape codes
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._indent_level = 0
        self._current_section: Optional[str] = None
        self._section_buffer: List[str] = []
        self._capturing = False

    def _indent(self) -> str:
        return "  " * self._indent_level

    def section(self, title: str, icon: str = ""):
        """Print a section header."""
        prefix = f"{icon} " if icon else ""
        print(f"\n{self.BOLD}{prefix}{title}{self.RESET}")

    def subsection(self, title: str):
        """Print a subsection header."""
        print(f"\n{self._indent()}{self.CYAN}{title}{self.RESET}")

    def step(self, name: str, result: str = "", status: str = "ok"):
        """Print a step with result on same line."""
        status_color = {
            "ok": self.GREEN,
            "warn": self.YELLOW,
            "error": self.RED,
            "info": self.RESET,
        }.get(status, self.RESET)

        if result:
            print(f"{self._indent()}[{name}] {status_color}{result}{self.RESET}")
        else:
            print(f"{self._indent()}[{name}]")

    def detail(self, text: str):
        """Print detail text (only in verbose mode)."""
        if self.verbose:
            for line in text.split("\n"):
                print(f"{self._indent()}{self.DIM}{line}{self.RESET}")

    def summary(self, label: str, value: str, status: str = "info"):
        """Print a summary line with label: value format."""
        status_color = {
            "ok": self.GREEN,
            "warn": self.YELLOW,
            "error": self.RED,
            "info": self.RESET,
        }.get(status, self.RESET)
        print(f"{self._indent()}{label}: {status_color}{value}{self.RESET}")

    def code_block(self, title: str, code: str, max_lines: int = 10):
        """Print a code block (truncated in non-verbose mode)."""
        lines = code.strip().split("\n")
        if self.verbose or len(lines) <= max_lines:
            print(f"{self._indent()}{self.DIM}--- {title} ---{self.RESET}")
            for line in lines:
                print(f"{self._indent()}{self.DIM}{line}{self.RESET}")
        else:
            print(f"{self._indent()}{self.DIM}--- {title} ({len(lines)} lines, showing first {max_lines}) ---{self.RESET}")
            for line in lines[:max_lines]:
                print(f"{self._indent()}{self.DIM}{line}{self.RESET}")
            print(f"{self._indent()}{self.DIM}...{self.RESET}")

    @contextmanager
    def collapsed(self, summary: str, expand_on_error: bool = True):
        """
        Context manager for collapsible output.

        In non-verbose mode: Shows only the summary line
        In verbose mode: Shows all output within the block

        Usage:
            with logger.collapsed("Testing solutions"):
                # All print statements here are captured
                print("Running test 1...")
                print("Running test 2...")
        """
        buffer = StringIO()
        old_stdout = sys.stdout

        try:
            if not self.verbose:
                sys.stdout = buffer

            yield buffer

        except Exception as e:
            # On error, always show the output
            sys.stdout = old_stdout
            if buffer.getvalue():
                print(f"{self._indent()}{self.DIM}{buffer.getvalue()}{self.RESET}")
            raise

        finally:
            sys.stdout = old_stdout

            # In verbose mode, output was already printed
            # In non-verbose mode, we show just the summary
            if not self.verbose:
                captured = buffer.getvalue().strip()
                if captured:
                    # Count key metrics from output
                    lines = captured.split("\n")
                    # Show summary with line count hint
                    print(f"{self._indent()}{summary} {self.DIM}({len(lines)} lines){self.RESET}")

    @contextmanager
    def indent(self):
        """Increase indent level for nested output."""
        self._indent_level += 1
        try:
            yield
        finally:
            self._indent_level -= 1

    def phase_start(self, phase_num: int, phase_name: str):
        """Print phase start banner."""
        print(f"\n{'='*60}")
        print(f"{self.BOLD}PHASE {phase_num}: {phase_name}{self.RESET}")
        print(f"{'='*60}")

    def phase_end(self, phase_num: int, result: str, status: str = "ok"):
        """Print phase end summary."""
        status_color = {
            "ok": self.GREEN,
            "warn": self.YELLOW,
            "error": self.RED,
        }.get(status, self.RESET)
        print(f"{status_color}Phase {phase_num} complete: {result}{self.RESET}")


# Global logger instance
_logger: Optional[CollapsibleLogger] = None


def get_logger() -> CollapsibleLogger:
    """Get the global logger instance."""
    global _logger
    if _logger is None:
        _logger = CollapsibleLogger(verbose=False)
    return _logger


def set_verbose(verbose: bool):
    """Set the global logger verbosity."""
    global _logger
    if _logger is None:
        _logger = CollapsibleLogger(verbose=verbose)
    else:
        _logger.verbose = verbose


def reset_logger():
    """Reset the global logger."""
    global _logger
    _logger = None
