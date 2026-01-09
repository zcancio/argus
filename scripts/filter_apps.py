#!/usr/bin/env python3
"""
Filter APPS problems based on Greenblatt et al. paper criteria.

Pulls APPS dataset from Hugging Face and filters based on:
1. Difficulty = "interview"
2. Valid test cases (input_output with inputs and outputs)
3. Has at least 3 reference solutions
4. No Cyrillic characters (non-English problems)
5. No known duplicate/problematic problems
6. First 5 reference solutions ALL pass test cases

Generates: data/APPS/filtered_problems.json
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from datasets import load_dataset

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "APPS"
OUTPUT_FILE = OUTPUT_DIR / "filtered_problems.json"

# Cyrillic character pattern (Russian/Ukrainian/etc)
CYRILLIC_PATTERN = re.compile(r"[\u0410-\u044F\u0400-\u04FF]")

# Timeout per test case (seconds) - paper uses 2.0
TIMEOUT_PER_TEST = 2.0

# Number of solutions to verify (paper uses first 5)
NUM_SOLUTIONS_TO_VERIFY = 5

# Check for pypy3 (faster than CPython)
PYPY3_PATH = shutil.which("pypy3")
PYTHON_EXEC = PYPY3_PATH if PYPY3_PATH else sys.executable


def normalize_output(output: str) -> str:
    """Normalize output for comparison."""
    lines = output.split('\n')
    lines = [line.rstrip() for line in lines]
    while lines and not lines[-1]:
        lines.pop()
    return '\n'.join(lines)


def outputs_match(actual: str, expected: str) -> bool:
    """Compare outputs with tolerance for minor formatting differences."""
    actual_norm = normalize_output(actual)
    expected_norm = normalize_output(expected)

    if actual_norm == expected_norm:
        return True

    # Try line-by-line with float tolerance
    actual_lines = actual_norm.split('\n')
    expected_lines = expected_norm.split('\n')

    if len(actual_lines) != len(expected_lines):
        return False

    for a_line, e_line in zip(actual_lines, expected_lines):
        a_parts = a_line.split()
        e_parts = e_line.split()

        if len(a_parts) != len(e_parts):
            return False

        for a_val, e_val in zip(a_parts, e_parts):
            try:
                a_num = float(a_val)
                e_num = float(e_val)
                if abs(a_num - e_num) > 1e-6 and abs(a_num - e_num) / max(abs(e_num), 1e-9) > 1e-6:
                    return False
            except ValueError:
                if a_val != e_val:
                    return False

    return True


def run_single_test(code: str, test_input: str, expected_output: str) -> bool:
    """Run a solution against a single test case with timeout."""
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = subprocess.run(
                [PYTHON_EXEC, temp_file],
                input=test_input,
                capture_output=True,
                text=True,
                timeout=TIMEOUT_PER_TEST
            )
            return outputs_match(result.stdout, expected_output)
        finally:
            os.unlink(temp_file)

    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def verify_solution(code: str, inputs: list, outputs: list, max_tests: int = 3) -> bool:
    """Verify a single solution passes all test cases."""
    num_tests = min(max_tests, len(inputs), len(outputs))

    for i in range(num_tests):
        test_input = inputs[i] if isinstance(inputs[i], str) else str(inputs[i])
        expected = outputs[i] if isinstance(outputs[i], str) else str(outputs[i])

        if not run_single_test(code, test_input, expected):
            return False

    return True


def verify_solutions_strict(solutions: list, inputs: list, outputs: list,
                           num_to_verify: int = 5, max_tests: int = 3) -> tuple[bool, str]:
    """
    Verify that the first N solutions ALL pass test cases.
    This matches the paper's stricter filtering approach.
    """
    if not inputs or not outputs:
        return False, "no_test_cases"

    solutions_to_check = solutions[:num_to_verify]

    if len(solutions_to_check) == 0:
        return False, "no_solutions"

    for idx, solution in enumerate(solutions_to_check):
        if not verify_solution(solution, inputs, outputs, max_tests):
            return False, f"solution_{idx}_fails"

    return True, "passed"


def validate_problem(problem: dict, verify: bool = True) -> tuple[bool, str, Optional[dict]]:
    """
    Check if a problem meets all filtering criteria.

    Returns:
        (passed, reason, problem_data)
    """
    problem_id = str(problem.get("problem_id", "unknown"))

    # 1. Check difficulty == "interview"
    difficulty = problem.get("difficulty", "unknown")
    if difficulty != "interview":
        return False, f"wrong_difficulty:{difficulty}", None

    # 2. Get question text
    question = problem.get("question", "")

    # 3. Check for Cyrillic characters (non-English)
    if CYRILLIC_PATTERN.search(question):
        return False, "non_english", None

    # 4. Check for known duplicate problem
    if "You are given n points on a line" in question:
        return False, "duplicate_problem", None

    # 5. Check for encoding issue
    if "DCBA:^!~}" in question:
        return False, "encoding_issue", None

    # 6. Parse solutions
    solutions_raw = problem.get("solutions", "")
    if not solutions_raw:
        return False, "no_solutions", None

    try:
        solutions = json.loads(solutions_raw)
        if not isinstance(solutions, list) or len(solutions) < 3:
            return False, "insufficient_solutions", None
    except (json.JSONDecodeError, TypeError):
        return False, "invalid_solutions", None

    # 7. Parse test cases
    input_output_raw = problem.get("input_output", "")
    if not input_output_raw:
        return False, "no_test_cases", None

    try:
        io_data = json.loads(input_output_raw)

        # Skip function-based test cases (only support stdin/stdout)
        if "fn_name" in io_data:
            return False, "function_based", None

        inputs = io_data.get("inputs", [])
        outputs = io_data.get("outputs", [])

        if not inputs or not outputs:
            return False, "empty_test_cases", None

        if len(inputs) != len(outputs):
            return False, "mismatched_test_cases", None

        # Normalize input/output format
        if isinstance(inputs[0], list):
            inputs = ["\n".join(str(x) for x in y) for y in inputs]
        if isinstance(outputs[0], list):
            outputs = ["\n".join(str(x) for x in y) for y in outputs]

    except (json.JSONDecodeError, TypeError):
        return False, "invalid_test_cases", None

    # 8. Verify solutions (strict: ALL of first 5 must pass)
    if verify:
        passed, reason = verify_solutions_strict(
            solutions, inputs, outputs,
            num_to_verify=NUM_SOLUTIONS_TO_VERIFY,
            max_tests=3
        )
        if not passed:
            return False, f"solutions_fail:{reason}", None

    # Build problem data
    problem_data = {
        "problem_id": problem_id,
        "question": question,
        "difficulty": difficulty,
        "solutions": solutions,
        "inputs": inputs,
        "outputs": outputs,
    }

    return True, "passed", problem_data


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Filter APPS problems from Hugging Face")
    parser.add_argument("--skip-verification", action="store_true",
                        help="Skip running solutions (faster but less accurate)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print each problem being processed")
    parser.add_argument("--split", default="test",
                        help="APPS split to use: 'train' or 'test' (default: test)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of problems to process (for testing)")
    args = parser.parse_args()

    print(f"Loading APPS dataset from Hugging Face (split={args.split})...")
    dataset = load_dataset("codeparrot/apps", split=args.split)
    print(f"Loaded {len(dataset)} problems")

    print(f"Python executor: {PYTHON_EXEC}")
    if PYPY3_PATH:
        print("  (using pypy3 for faster execution)")
    else:
        print("  (pypy3 not found, using CPython - consider installing pypy3 for speed)")

    verify_flag = not args.skip_verification
    if verify_flag:
        print(f"Solution verification: ENABLED (first {NUM_SOLUTIONS_TO_VERIFY} solutions must ALL pass)")
    else:
        print("Solution verification: DISABLED")

    # Statistics
    stats = {
        "total_scanned": 0,
        "passed_filter": 0,
        "failed_wrong_difficulty": 0,
        "failed_no_test_cases": 0,
        "failed_empty_test_cases": 0,
        "failed_insufficient_solutions": 0,
        "failed_non_english": 0,
        "failed_duplicate": 0,
        "failed_encoding": 0,
        "failed_function_based": 0,
        "failed_solutions_fail": 0,
        "failed_other": 0,
    }

    valid_problems = []

    problems_to_process = dataset
    if args.limit:
        problems_to_process = list(dataset)[:args.limit]

    for i, problem in enumerate(problems_to_process):
        stats["total_scanned"] += 1

        if args.verbose:
            print(f"[{i+1}/{len(problems_to_process)}] Processing problem {problem.get('problem_id', i)}...")
        elif stats["total_scanned"] % 100 == 0:
            print(f"  Processed {stats['total_scanned']}/{len(problems_to_process)} problems... ({stats['passed_filter']} passed)")

        passed, reason, problem_data = validate_problem(problem, verify=verify_flag)

        if passed:
            stats["passed_filter"] += 1
            valid_problems.append(problem_data)
        else:
            # Categorize failure
            if reason.startswith("wrong_difficulty"):
                stats["failed_wrong_difficulty"] += 1
            elif reason in ("no_test_cases", "invalid_test_cases", "mismatched_test_cases"):
                stats["failed_no_test_cases"] += 1
            elif reason == "empty_test_cases":
                stats["failed_empty_test_cases"] += 1
            elif reason in ("no_solutions", "insufficient_solutions", "invalid_solutions"):
                stats["failed_insufficient_solutions"] += 1
            elif reason == "non_english":
                stats["failed_non_english"] += 1
            elif reason == "duplicate_problem":
                stats["failed_duplicate"] += 1
            elif reason == "encoding_issue":
                stats["failed_encoding"] += 1
            elif reason == "function_based":
                stats["failed_function_based"] += 1
            elif reason.startswith("solutions_fail"):
                stats["failed_solutions_fail"] += 1
            else:
                stats["failed_other"] += 1
                if args.verbose:
                    print(f"    -> Failed: {reason}")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build output
    output = {
        "version": "2.0",
        "source": "huggingface:codeparrot/apps",
        "split": args.split,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "python_exec": PYTHON_EXEC,
        "criteria": {
            "difficulty": "interview",
            "requires_test_cases": True,
            "min_solutions": 3,
            "no_cyrillic": True,
            "no_function_based": True,
            "solutions_verified": verify_flag,
            "num_solutions_verified": NUM_SOLUTIONS_TO_VERIFY if verify_flag else 0,
            "all_must_pass": True,
        },
        "stats": stats,
        "problem_ids": [p["problem_id"] for p in valid_problems],
    }

    # Write output file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    # Also save full problem data for direct use
    problems_file = OUTPUT_DIR / "problems_cache.json"
    with open(problems_file, 'w') as f:
        json.dump(valid_problems, f)

    print(f"\nFiltering complete!")
    print(f"  Total scanned: {stats['total_scanned']}")
    print(f"  Passed filter: {stats['passed_filter']}")
    print(f"  ---")
    print(f"  Failed (wrong difficulty): {stats['failed_wrong_difficulty']}")
    print(f"  Failed (no/invalid test cases): {stats['failed_no_test_cases']}")
    print(f"  Failed (empty test cases): {stats['failed_empty_test_cases']}")
    print(f"  Failed (function-based tests): {stats['failed_function_based']}")
    print(f"  Failed (insufficient solutions <3): {stats['failed_insufficient_solutions']}")
    print(f"  Failed (non-English/Cyrillic): {stats['failed_non_english']}")
    print(f"  Failed (duplicate problem): {stats['failed_duplicate']}")
    print(f"  Failed (encoding issue): {stats['failed_encoding']}")
    print(f"  Failed (solutions fail tests): {stats['failed_solutions_fail']}")
    print(f"  Failed (other): {stats['failed_other']}")
    print(f"\nOutput written to: {OUTPUT_FILE}")
    print(f"Problems cache: {problems_file}")


if __name__ == "__main__":
    main()
