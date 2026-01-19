#!/usr/bin/env python3
"""
Mark problems that have inverted T monitoring (T_backdoor < T_normal).

These problems should be excluded from simulations because the trusted
model incorrectly rates backdoored code as LESS suspicious than normal code.

Usage:
    python scripts/mark_inverted_monitoring.py <dataset_id> [--dry-run]
"""

import argparse
import json
from pathlib import Path


def mark_inverted_monitoring(dataset_id: str, dry_run: bool = False):
    """Mark problems with inverted T monitoring."""

    datasets_dir = Path(__file__).parent.parent / "datasets"
    dataset_dir = datasets_dir / dataset_id
    problems_dir = dataset_dir / "problems"

    if not problems_dir.exists():
        print(f"Error: Dataset {dataset_id} not found")
        return

    print(f"Dataset: {dataset_id}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    # Track stats
    total = 0
    with_backdoor = 0
    inverted = 0
    correct = 0

    inverted_problems = []

    for problem_file in sorted(problems_dir.glob("*.json")):
        with open(problem_file) as f:
            data = json.load(f)

        total += 1
        problem_id = problem_file.stem

        t_normal = data.get("T_suspicion_normal")
        t_backdoor = data.get("T_suspicion_backdoor")

        # Skip problems without backdoor monitoring
        if t_backdoor is None or t_normal is None:
            continue

        with_backdoor += 1
        t_diff = t_backdoor - t_normal

        # Check for inverted monitoring (backdoor rated LESS suspicious)
        is_inverted = t_diff < 0

        if is_inverted:
            inverted += 1
            inverted_problems.append({
                "id": problem_id,
                "t_normal": t_normal,
                "t_backdoor": t_backdoor,
                "t_diff": t_diff
            })

            # Mark the problem
            if not dry_run:
                data["inverted_t_monitoring"] = True
                data["inverted_t_diff"] = t_diff
                with open(problem_file, 'w') as f:
                    json.dump(data, f, indent=2)
        else:
            correct += 1
            # Clear the flag if it was previously set
            if data.get("inverted_t_monitoring"):
                if not dry_run:
                    data["inverted_t_monitoring"] = False
                    with open(problem_file, 'w') as f:
                        json.dump(data, f, indent=2)

    # Print summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total problems: {total}")
    print(f"With backdoors: {with_backdoor}")
    print(f"Correct T discrimination (T_backdoor > T_normal): {correct}")
    print(f"Inverted T monitoring (T_backdoor < T_normal): {inverted}")
    print()

    if inverted_problems:
        print("Problems with INVERTED T monitoring (will be excluded from simulations):")
        print("-" * 60)
        for p in sorted(inverted_problems, key=lambda x: x["t_diff"]):
            print(f"  {p['id']}: T_diff = {p['t_diff']:+.2f} (normal={p['t_normal']:.2f}, backdoor={p['t_backdoor']:.2f})")

    if dry_run:
        print()
        print("(DRY RUN - no changes made)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mark problems with inverted T monitoring")
    parser.add_argument("dataset_id", help="Dataset ID to process")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually update files")

    args = parser.parse_args()
    mark_inverted_monitoring(args.dataset_id, args.dry_run)
