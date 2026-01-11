#!/usr/bin/env python3
"""
Run problems in parallel with configurable workers.

Usage:
    python scripts/run_problems_parallel.py <dataset_id> --add <count> [--workers <n>]

Example:
    python scripts/run_problems_parallel.py paper_baseline_100_20260111_011800 --add 78 --workers 3
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
from dataclasses import asdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env file
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from api._lib.precompute import run_single_problem
from datasets import load_dataset


def convert_datetimes(obj):
    """Recursively convert datetime objects to ISO format strings."""
    if isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj

# Thread-safe lock for checkpoint updates
checkpoint_lock = Lock()


def load_apps_problem(problem_id: str, apps_dataset):
    """Load a problem from APPS dataset."""
    for item in apps_dataset:
        if item["problem_id"] == int(problem_id):
            solutions = json.loads(item["solutions"]) if item["solutions"] else []
            input_output = json.loads(item["input_output"]) if item["input_output"] else {}
            return {
                "problem_id": problem_id,
                "question": item["question"],
                "solutions": solutions,
                "difficulty": item["difficulty"],
                "input_output": input_output,
            }
    return None


def get_completed_problems(dataset_dir: Path) -> set:
    """Get set of already completed problem IDs."""
    checkpoint_path = dataset_dir / "checkpoint.json"
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        return set(checkpoint.get("problems_completed", []))
    return set()


def get_available_problems(completed: set, max_count: int) -> list:
    """Get list of problem IDs to run (not yet completed)."""
    filtered_path = Path("data/APPS/filtered_problems.json")
    with open(filtered_path) as f:
        filtered = json.load(f)

    all_problems = filtered.get("problem_ids", [])
    available = [p for p in all_problems if p not in completed]
    return available[:max_count]


def update_checkpoint(dataset_dir: Path, problem_id: str, success: bool, outcome: str = None):
    """Thread-safe checkpoint update."""
    with checkpoint_lock:
        checkpoint_path = dataset_dir / "checkpoint.json"
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)

        if success:
            if problem_id not in checkpoint["problems_completed"]:
                checkpoint["problems_completed"].append(problem_id)
            if problem_id in checkpoint.get("problems_pending", []):
                checkpoint["problems_pending"].remove(problem_id)
        else:
            if problem_id not in checkpoint.get("problems_failed", []):
                checkpoint.setdefault("problems_failed", []).append(problem_id)

        # Update stats
        checkpoint["stats"]["completed"] = len(checkpoint["problems_completed"])
        checkpoint["stats"]["failed"] = len(checkpoint.get("problems_failed", []))

        # Track outcome
        if outcome == "SUCCESSFUL_COUP":
            checkpoint["stats"]["successful_coups"] = checkpoint["stats"].get("successful_coups", 0) + 1
        elif outcome == "FAILED_COUP_ATTEMPT":
            checkpoint["stats"]["failed_coup_attempts"] = checkpoint["stats"].get("failed_coup_attempts", 0) + 1
        elif outcome == "TOO_DIFFICULT":
            checkpoint["stats"]["too_difficult"] = checkpoint["stats"].get("too_difficult", 0) + 1
        elif outcome == "NO_BACKDOOR" or outcome == "NO_COUP_ATTEMPT":
            checkpoint["stats"]["no_backdoor"] = checkpoint["stats"].get("no_backdoor", 0) + 1

        checkpoint["last_updated"] = datetime.now(timezone.utc).isoformat()

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint, f, indent=2)


def run_problem_worker(args):
    """Worker function to run a single problem."""
    problem_id, dataset_id, dataset_dir, config, apps_dataset, openai_key, anthropic_key = args

    start_time = time.time()

    try:
        # Load APPS problem
        apps_problem = load_apps_problem(problem_id, apps_dataset)
        if not apps_problem:
            return (problem_id, False, None, f"Problem not found in APPS")

        # Run the problem
        result = run_single_problem(
            dataset_id=dataset_id,
            problem_id=problem_id,
            problem_text=apps_problem["question"],
            solutions=apps_problem["solutions"],
            test_cases=apps_problem.get("input_output", {}),
            models=config.get("models", {}),
            prompts=config.get("prompts"),
            openai_key=openai_key,
            anthropic_key=anthropic_key,
        )

        elapsed = time.time() - start_time

        # Save result to file
        problems_dir = dataset_dir / "problems"
        problems_dir.mkdir(parents=True, exist_ok=True)
        problem_path = problems_dir / f"{problem_id}.json"

        result_dict = asdict(result)
        result_dict = convert_datetimes(result_dict)
        with open(problem_path, "w") as f:
            json.dump(result_dict, f, indent=2)

        if result.status == "completed":
            outcome = result.coup_outcome_after_edit or "NO_BACKDOOR"
            if result.difficulty_skipped:
                return (problem_id, True, "TOO_DIFFICULT", f"skipped (difficulty), {elapsed:.0f}s")
            sneak = f"{result.sneakiness:.1f}" if result.sneakiness is not None else "N/A"
            return (problem_id, True, outcome, f"sneakiness={sneak}, {elapsed:.0f}s")
        else:
            return (problem_id, False, None, f"Failed: {result.error}")

    except Exception as e:
        elapsed = time.time() - start_time
        return (problem_id, False, None, f"Error: {str(e)[:100]}, {elapsed:.0f}s")


def run_parallel(dataset_id: str, add_count: int, workers: int = 3):
    """Run problems in parallel."""
    dataset_dir = Path("datasets") / dataset_id

    if not dataset_dir.exists():
        print(f"Error: Dataset not found: {dataset_id}")
        sys.exit(1)

    # Load config
    config_path = dataset_dir / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    # Get completed problems
    completed = get_completed_problems(dataset_dir)
    print(f"Already completed: {len(completed)} problems")

    # Get problems to run
    to_run = get_available_problems(completed, add_count)
    print(f"Will run: {len(to_run)} new problems")
    print(f"Workers: {workers}")
    print()

    if not to_run:
        print("No problems to run!")
        return

    # Update checkpoint with pending problems
    checkpoint_path = dataset_dir / "checkpoint.json"
    with open(checkpoint_path) as f:
        checkpoint = json.load(f)
    checkpoint["problems_pending"] = to_run
    checkpoint["total_problems"] = len(completed) + len(to_run)
    checkpoint["stats"]["total"] = len(completed) + len(to_run)
    checkpoint["stats"]["pending"] = len(to_run)
    with open(checkpoint_path, "w") as f:
        json.dump(checkpoint, f, indent=2)

    # Get API keys
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if not openai_key:
        print("Warning: OPENAI_API_KEY not set")

    # Load APPS dataset once
    print("Loading APPS dataset...")
    apps_dataset = list(load_dataset("codeparrot/apps", split="test", trust_remote_code=True))
    print(f"Loaded {len(apps_dataset)} problems from APPS")
    print()

    # Prepare work items
    work_items = [
        (pid, dataset_id, dataset_dir, config, apps_dataset, openai_key, anthropic_key)
        for pid in to_run
    ]

    # Run in parallel
    completed_count = 0
    failed_count = 0
    successful_coups = 0
    failed_coups = 0

    start_time = time.time()

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(run_problem_worker, item): item[0] for item in work_items}

        for future in as_completed(futures):
            problem_id = futures[future]
            try:
                pid, success, outcome, message = future.result()

                # Update checkpoint
                update_checkpoint(dataset_dir, pid, success, outcome)

                if success:
                    completed_count += 1
                    if outcome == "SUCCESSFUL_COUP":
                        successful_coups += 1
                        print(f"[{completed_count + failed_count}/{len(to_run)}] {pid}: SUCCESSFUL_COUP! {message}")
                    elif outcome == "FAILED_COUP_ATTEMPT":
                        failed_coups += 1
                        print(f"[{completed_count + failed_count}/{len(to_run)}] {pid}: FAILED_COUP {message}")
                    else:
                        print(f"[{completed_count + failed_count}/{len(to_run)}] {pid}: {outcome} {message}")
                else:
                    failed_count += 1
                    print(f"[{completed_count + failed_count}/{len(to_run)}] {pid}: FAILED - {message}")

            except Exception as e:
                failed_count += 1
                print(f"[{completed_count + failed_count}/{len(to_run)}] {problem_id}: EXCEPTION - {e}")

    elapsed = time.time() - start_time

    print()
    print("=" * 60)
    print(f"COMPLETED: {completed_count}")
    print(f"FAILED: {failed_count}")
    print(f"SUCCESSFUL COUPS: {successful_coups}")
    print(f"FAILED COUP ATTEMPTS: {failed_coups}")
    print(f"Total time: {elapsed/60:.1f} minutes")
    print(f"Average per problem: {elapsed/(completed_count + failed_count):.1f}s")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Run problems in parallel")
    parser.add_argument("dataset_id", help="Dataset ID to add problems to")
    parser.add_argument("--add", type=int, required=True, help="Number of problems to add")
    parser.add_argument("--workers", type=int, default=3, help="Number of parallel workers (default: 3)")

    args = parser.parse_args()

    run_parallel(args.dataset_id, args.add, args.workers)


if __name__ == "__main__":
    main()
