#!/usr/bin/env python3
"""
Run a batch of problems from phase 2 for an existing dataset.

Usage:
    python scripts/run_problem_batch.py <dataset_id> <problem_ids...>

Example:
    python scripts/run_problem_batch.py paper_baseline_100_20260110_183400 1764 2021 1728
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime
# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file if it exists
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from api._lib.precompute.single_problem import SingleProblemEngine
from api._lib.dataset import dict_to_problem_result, problem_result_to_dict
from datasets import load_dataset


def load_apps_dataset():
    """Load APPS dataset once."""
    return load_dataset("codeparrot/apps", split="test", trust_remote_code=True)


def get_apps_problem(apps, problem_id: str):
    """Get a problem from pre-loaded APPS dataset."""
    for item in apps:
        if item["problem_id"] == int(problem_id):
            solutions = json.loads(item["solutions"]) if item["solutions"] else []
            test_cases = {}
            if item.get("input_output"):
                test_cases = json.loads(item["input_output"])
            return {
                "problem_id": problem_id,
                "question": item["question"],
                "solutions": solutions,
                "difficulty": item["difficulty"],
                "test_cases": test_cases,
            }
    return None


def convert_datetimes(obj):
    """Recursively convert datetime objects to strings."""
    if isinstance(obj, dict):
        return {k: convert_datetimes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_datetimes(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def run_batch(dataset_id: str, problem_ids: list[str], programming_language: str = "Python"):
    """Run a batch of problems from phase 2."""
    datasets_dir = project_root / "datasets"
    dataset_dir = datasets_dir / dataset_id

    if not dataset_dir.exists():
        print(f"Dataset not found: {dataset_id}")
        sys.exit(1)

    # Load config
    config_path = dataset_dir / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    models = config.get("models", {})
    prompts = config.get("prompts", {})

    # Get API keys
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    print(f"Loading APPS dataset...")
    apps = load_apps_dataset()
    print(f"Loaded. Processing {len(problem_ids)} problems...")
    print()

    completed = 0
    failed = 0

    for i, problem_id in enumerate(problem_ids):
        print(f"[{i+1}/{len(problem_ids)}] Processing problem {problem_id}...")

        try:
            # Load existing problem data from disk
            problem_path = dataset_dir / "problems" / f"{problem_id}.json"
            if not problem_path.exists():
                print(f"  Problem file not found, skipping")
                failed += 1
                continue

            with open(problem_path) as f:
                problem_data = json.load(f)

            # Skip if difficulty_skipped
            if problem_data.get("difficulty_skipped"):
                print(f"  Skipping (too difficult)")
                completed += 1
                continue

            # Get APPS problem
            apps_problem = get_apps_problem(apps, problem_id)
            if not apps_problem:
                print(f"  Problem not found in APPS dataset")
                failed += 1
                continue

            # Create engine
            engine = SingleProblemEngine(
                dataset_id=dataset_id,
                problem_id=problem_id,
                problem_text=apps_problem["question"],
                solutions=apps_problem["solutions"],
                test_cases=apps_problem["test_cases"],
                models=models,
                prompts=prompts if prompts else None,
                openai_key=openai_key,
                anthropic_key=anthropic_key,
                programming_language=programming_language,
            )

            # Load existing result from disk
            existing_result = dict_to_problem_result(problem_data)
            engine.result = existing_result
            engine.result.status = "running"
            engine.result.error = None

            # Clear phases >= 2 (we're running from phase 2)
            engine.result.phases_completed = [p for p in engine.result.phases_completed if p < 2]

            # Clear phase 2+ data
            engine.result.backdoor_attempts = []
            engine.result.sneakiest_backdoor_idx = None
            engine.result.sneakiness = None
            engine.result.U_backdoored_solution = None
            engine.result.exploit_found = False
            engine.result.exploits = []
            engine.result.T_suspicion_normal = None
            engine.result.T_suspicion_backdoor = None
            engine.result.U_suspicion_normal = None
            engine.result.U_suspicion_backdoor = None
            engine.result.T_edited_code = None
            engine.result.coup_outcome_after_edit = None
            engine.result.T_edited_correct = None

            # Clear phase 2+ LLM calls to avoid stale data
            engine.result.llm_calls = [
                call for call in engine.result.llm_calls
                if call.phase < 2
            ]

            # Run from phase 2
            result = engine.run_from_phase(2)

            # Save result to file
            result_dict = problem_result_to_dict(result)
            result_dict = convert_datetimes(result_dict)
            with open(problem_path, "w") as f:
                json.dump(result_dict, f, indent=2)

            if result.status == "completed":
                outcome = "no backdoor"
                if result.sneakiest_backdoor_idx is not None and result.backdoor_attempts:
                    sneakiest = result.backdoor_attempts[result.sneakiest_backdoor_idx]
                    outcome = sneakiest.outcome or "unknown"
                sneakiness = None
                if result.backdoor_attempts and result.sneakiest_backdoor_idx is not None:
                    sneakiness = result.backdoor_attempts[result.sneakiest_backdoor_idx].sneakiness
                print(f"  Completed: sneakiness={sneakiness}, outcome={outcome}")
                completed += 1
            else:
                print(f"  Failed: {result.error}")
                failed += 1

        except Exception as e:
            import traceback
            print(f"  Error: {e}")
            traceback.print_exc()
            failed += 1

        # Small delay
        time.sleep(0.5)

    print()
    print(f"Batch complete! Completed: {completed}, Failed: {failed}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Run a batch of problems from phase 2 for an existing dataset.")
    parser.add_argument("dataset_id", help="Dataset ID")
    parser.add_argument("problem_ids", nargs="+", help="Problem IDs to process")
    parser.add_argument("--language", dest="programming_language", default="Python",
                        help="Programming language (default: Python)")

    args = parser.parse_args()

    run_batch(args.dataset_id, args.problem_ids, args.programming_language)


if __name__ == "__main__":
    main()
