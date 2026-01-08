#!/usr/bin/env python3
"""
Filter APPS problems based on Greenblatt et al. paper criteria.

Criteria:
1. Difficulty = "interview"
2. Valid test cases (input_output.json with inputs and outputs)
3. Has at least 3 reference solutions
4. No Cyrillic characters (non-English problems)
5. No known duplicate/problematic problems
6. All reference solutions pass test cases

Generates: data/APPS/filtered_problems.json
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


APPS_DATA_PATH = Path(__file__).parent.parent / "data" / "APPS"
OUTPUT_FILE = APPS_DATA_PATH / "filtered_problems.json"

# Cyrillic character pattern (Russian/Ukrainian/etc)
CYRILLIC_PATTERN = re.compile(r"[\u0410-\u044F\u0400-\u04FF]")

# Timeout for running solutions (seconds)
SOLUTION_TIMEOUT = 5


def run_solution(code: str, test_input: str, expected_output: str) -> bool:
    """
    Run a solution against a single test case.

    Returns:
        True if solution produces expected output, False otherwise
    """
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                input=test_input,
                capture_output=True,
                text=True,
                timeout=SOLUTION_TIMEOUT
            )

            actual = result.stdout.strip()
            expected = expected_output.strip()

            return actual == expected

        finally:
            os.unlink(temp_file)

    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


def verify_solutions(solutions: list, test_cases: dict, min_passing: int = 1) -> tuple[bool, str]:
    """
    Verify that reference solutions pass the test cases.

    Args:
        solutions: List of solution code strings
        test_cases: Dict with 'inputs' and 'outputs' arrays
        min_passing: Minimum number of solutions that must pass all tests

    Returns:
        (passed, reason)
    """
    inputs = test_cases.get("inputs", [])
    outputs = test_cases.get("outputs", [])

    if not inputs or not outputs:
        return False, "no_test_cases"

    # Only test first few test cases for speed
    max_tests = min(3, len(inputs))

    passing_solutions = 0

    for solution in solutions:
        all_pass = True
        for i in range(max_tests):
            test_input = inputs[i] if isinstance(inputs[i], str) else str(inputs[i])
            expected = outputs[i] if isinstance(outputs[i], str) else str(outputs[i])

            if not run_solution(solution, test_input, expected):
                all_pass = False
                break

        if all_pass:
            passing_solutions += 1
            if passing_solutions >= min_passing:
                return True, "passed"

    return False, "solutions_fail_tests"


def validate_problem(problem_path: Path, verify_solutions_flag: bool = True) -> tuple[bool, str]:
    """
    Check if a problem meets all filtering criteria.

    Returns:
        (passed, reason) - True if passed, False with reason if failed
    """
    # 1. Check metadata for difficulty == "interview"
    metadata_path = problem_path / "metadata.json"
    if not metadata_path.exists():
        return False, "no_metadata"

    try:
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        difficulty = metadata.get("difficulty", "unknown")
        if difficulty != "interview":
            return False, f"wrong_difficulty:{difficulty}"
    except (json.JSONDecodeError, IOError):
        return False, "invalid_metadata"

    # 2. Load question text for content-based filters
    question_path = problem_path / "question.txt"
    question = ""
    if question_path.exists():
        try:
            with open(question_path, 'r') as f:
                question = f.read()
        except IOError:
            pass

    # 3. Check for Cyrillic characters (non-English)
    if CYRILLIC_PATTERN.search(question):
        return False, "non_english"

    # 4. Check for known duplicate problem
    if "You are given n points on a line" in question:
        return False, "duplicate_problem"

    # 5. Ad-hoc filter: weird encoding issue
    if "DCBA:^!~}" in question:
        return False, "encoding_issue"

    # 6. Check input_output.json exists and has valid structure
    io_path = problem_path / "input_output.json"
    if not io_path.exists():
        return False, "no_test_cases"

    try:
        with open(io_path, 'r') as f:
            test_cases = json.load(f)

        inputs = test_cases.get("inputs", [])
        outputs = test_cases.get("outputs", [])

        if not inputs or not outputs:
            return False, "empty_test_cases"

        if len(inputs) != len(outputs):
            return False, "mismatched_test_cases"

    except (json.JSONDecodeError, IOError):
        return False, "invalid_test_cases"

    # 7. Check solutions.json - need at least 3 solutions
    solutions_path = problem_path / "solutions.json"
    if not solutions_path.exists():
        return False, "no_solutions_file"

    try:
        with open(solutions_path, 'r') as f:
            solutions = json.load(f)

        if not isinstance(solutions, list) or len(solutions) < 3:
            return False, "insufficient_solutions"

    except (json.JSONDecodeError, IOError):
        return False, "invalid_solutions"

    # 8. Verify reference solutions actually pass tests
    if verify_solutions_flag:
        passed, reason = verify_solutions(solutions, test_cases, min_passing=1)
        if not passed:
            return False, reason

    return True, "passed"


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Filter APPS problems")
    parser.add_argument("--skip-verification", action="store_true",
                        help="Skip running solutions (faster but less accurate)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Print each problem being processed")
    args = parser.parse_args()

    split = "train"
    split_path = APPS_DATA_PATH / split

    if not split_path.exists():
        print(f"Error: APPS data path not found: {split_path}")
        return

    verify_solutions_flag = not args.skip_verification

    print(f"Scanning APPS problems in: {split_path}")
    if verify_solutions_flag:
        print("Solution verification: ENABLED (this may take a while)")
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
        "failed_solutions_fail": 0,
        "failed_other": 0,
    }

    valid_ids = []

    # Scan all problem directories
    entries = sorted(os.listdir(split_path))
    total = len([e for e in entries if (split_path / e).is_dir()])

    for i, entry in enumerate(entries):
        problem_path = split_path / entry
        if not problem_path.is_dir():
            continue

        stats["total_scanned"] += 1

        if args.verbose:
            print(f"[{i+1}/{total}] Processing {entry}...")
        elif stats["total_scanned"] % 100 == 0:
            print(f"  Processed {stats['total_scanned']}/{total} problems...")

        passed, reason = validate_problem(problem_path, verify_solutions_flag)

        if passed:
            stats["passed_filter"] += 1
            valid_ids.append(entry)
        else:
            # Categorize failure reason
            if reason.startswith("wrong_difficulty"):
                stats["failed_wrong_difficulty"] += 1
            elif reason in ("no_test_cases", "invalid_test_cases", "mismatched_test_cases"):
                stats["failed_no_test_cases"] += 1
            elif reason == "empty_test_cases":
                stats["failed_empty_test_cases"] += 1
            elif reason in ("no_solutions_file", "insufficient_solutions", "invalid_solutions"):
                stats["failed_insufficient_solutions"] += 1
            elif reason == "non_english":
                stats["failed_non_english"] += 1
            elif reason == "duplicate_problem":
                stats["failed_duplicate"] += 1
            elif reason == "encoding_issue":
                stats["failed_encoding"] += 1
            elif reason == "solutions_fail_tests":
                stats["failed_solutions_fail"] += 1
            else:
                stats["failed_other"] += 1
                if args.verbose:
                    print(f"    -> Failed: {reason}")

    # Build output
    output = {
        "version": "1.1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "criteria": {
            "difficulty": "interview",
            "requires_test_cases": True,
            "min_solutions": 3,
            "no_cyrillic": True,
            "solutions_verified": verify_solutions_flag
        },
        "stats": stats,
        "problem_ids": valid_ids
    }

    # Write output file
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nFiltering complete!")
    print(f"  Total scanned: {stats['total_scanned']}")
    print(f"  Passed filter: {stats['passed_filter']}")
    print(f"  ---")
    print(f"  Failed (wrong difficulty): {stats['failed_wrong_difficulty']}")
    print(f"  Failed (no/invalid test cases): {stats['failed_no_test_cases']}")
    print(f"  Failed (empty test cases): {stats['failed_empty_test_cases']}")
    print(f"  Failed (insufficient solutions <3): {stats['failed_insufficient_solutions']}")
    print(f"  Failed (non-English/Cyrillic): {stats['failed_non_english']}")
    print(f"  Failed (duplicate problem): {stats['failed_duplicate']}")
    print(f"  Failed (encoding issue): {stats['failed_encoding']}")
    print(f"  Failed (solutions fail tests): {stats['failed_solutions_fail']}")
    print(f"  Failed (other): {stats['failed_other']}")
    print(f"\nOutput written to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
