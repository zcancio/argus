#!/usr/bin/env python3
"""
Rerun a dataset from a specific phase.

Usage:
    python scripts/rerun_dataset_from_phase.py <source_dataset> <new_dataset_name> <from_phase>

Example:
    python scripts/rerun_dataset_from_phase.py paper_baseline_100_20260109_195952 paper_baseline_100_20260110_183400 2
"""

import os
import sys
import json
import shutil
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api._lib.precompute import run_single_problem_from_phase
from datasets import load_dataset


def copy_dataset(source_id: str, new_id: str) -> Path:
    """Copy a dataset to a new location."""
    datasets_dir = Path("datasets")
    source_dir = datasets_dir / source_id
    new_dir = datasets_dir / new_id

    if not source_dir.exists():
        raise ValueError(f"Source dataset not found: {source_id}")

    if new_dir.exists():
        raise ValueError(f"Target dataset already exists: {new_id}")

    # Copy the entire directory
    shutil.copytree(source_dir, new_dir)

    # Update config.json with new name
    config_path = new_dir / "config.json"
    if config_path.exists():
        with open(config_path) as f:
            config = json.load(f)
        config["name"] = new_id
        config["created_at"] = datetime.utcnow().isoformat()
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)

    return new_dir


def reset_problems_for_rerun(dataset_dir: Path, from_phase: int):
    """Reset problem files to prepare for re-run from a specific phase."""
    problems_dir = dataset_dir / "problems"

    for problem_file in problems_dir.glob("*.json"):
        with open(problem_file) as f:
            problem = json.load(f)

        # Keep phases before from_phase
        problem["phases_completed"] = [p for p in problem.get("phases_completed", []) if p < from_phase]
        problem["current_phase"] = from_phase - 1 if from_phase > 1 else 0
        problem["status"] = "pending"

        # Clear phase-specific data based on from_phase
        if from_phase <= 2:
            problem["backdoor_attempts"] = []
            problem["sneakiest_backdoor_idx"] = None
            problem["sneakiness"] = None
            problem["exploit_found"] = False

        if from_phase <= 5:
            problem["T_suspicion_normal"] = None
            problem["T_suspicion_backdoor"] = None
            problem["H_suspicion_normal"] = None
            problem["H_suspicion_backdoor"] = None
            problem["U_suspicion_normal"] = None
            problem["U_suspicion_backdoor"] = None
            problem["T_edited_code"] = None
            problem["coup_outcome_after_edit"] = None
            problem["T_edited_correct"] = None

        # Clear strategy_results (deprecated but clean it up)
        problem["strategy_results"] = {}

        with open(problem_file, "w") as f:
            json.dump(problem, f, indent=2)

    # Reset checkpoint
    checkpoint_path = dataset_dir / "checkpoint.json"
    if checkpoint_path.exists():
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        checkpoint["phases_completed"] = []
        checkpoint["current_phase"] = from_phase
        checkpoint["progress_percent"] = 0
        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint, f, indent=2)

    # Reset summary
    summary_path = dataset_dir / "summary.json"
    if summary_path.exists():
        with open(summary_path) as f:
            summary = json.load(f)
        summary["stats"]["completed"] = 0
        summary["stats"]["pending"] = summary["stats"]["total"]
        summary["stats"]["successful_coups"] = 0
        summary["stats"]["failed_coup_attempts"] = 0
        summary["stats"]["no_backdoor"] = 0
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)


def load_apps_problem(problem_id: str):
    """Load a problem from APPS dataset."""
    apps = load_dataset("codeparrot/apps", split="test", trust_remote_code=True)

    for item in apps:
        if item["problem_id"] == int(problem_id):
            solutions = json.loads(item["solutions"]) if item["solutions"] else []
            return {
                "problem_id": problem_id,
                "question": item["question"],
                "solutions": solutions,
                "difficulty": item["difficulty"],
            }

    raise ValueError(f"Problem {problem_id} not found in APPS dataset")


def run_dataset_from_phase(
    source_id: str,
    new_id: str,
    from_phase: int,
    openai_key: str = None,
    anthropic_key: str = None,
):
    """Copy dataset and re-run all problems from a specific phase."""

    print(f"Copying dataset {source_id} to {new_id}...")
    new_dir = copy_dataset(source_id, new_id)
    print(f"  Created: {new_dir}")

    print(f"Resetting problems for re-run from phase {from_phase}...")
    reset_problems_for_rerun(new_dir, from_phase)

    # Load config
    config_path = new_dir / "config.json"
    with open(config_path) as f:
        config = json.load(f)

    models = config.get("models", {})
    problem_ids = config.get("problem_ids", [])
    prompts = config.get("prompts", {})

    print(f"Found {len(problem_ids)} problems to process")
    print(f"Models: {models}")
    print()

    # Process each problem
    completed = 0
    failed = 0

    for i, problem_id in enumerate(problem_ids):
        print(f"[{i+1}/{len(problem_ids)}] Processing problem {problem_id}...")

        try:
            # Load APPS problem data
            apps_problem = load_apps_problem(problem_id)

            # Check if problem was skipped due to difficulty
            problem_path = new_dir / "problems" / f"{problem_id}.json"
            with open(problem_path) as f:
                problem_data = json.load(f)

            if problem_data.get("difficulty_skipped"):
                print(f"  Skipping (too difficult)")
                completed += 1
                continue

            # Run from phase
            result = run_single_problem_from_phase(
                dataset_id=new_id,
                problem_id=problem_id,
                problem_text=apps_problem["question"],
                solutions=apps_problem["solutions"],
                models=models,
                from_phase=from_phase,
                prompts=prompts if prompts else None,
                openai_key=openai_key,
                anthropic_key=anthropic_key,
            )

            if result.status == "completed":
                print(f"  Completed: sneakiness={result.sneakiness}")
                completed += 1
            else:
                print(f"  Failed: {result.error}")
                failed += 1

        except Exception as e:
            print(f"  Error: {e}")
            failed += 1

        # Small delay to avoid rate limiting
        time.sleep(0.5)

    print()
    print(f"Done! Completed: {completed}, Failed: {failed}")
    print(f"Results saved to: {new_dir}")


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)

    source_id = sys.argv[1]
    new_id = sys.argv[2]
    from_phase = int(sys.argv[3])

    # Get API keys from environment
    openai_key = os.environ.get("OPENAI_API_KEY")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")

    if not openai_key:
        print("Warning: OPENAI_API_KEY not set")
    if not anthropic_key:
        print("Warning: ANTHROPIC_API_KEY not set")

    run_dataset_from_phase(
        source_id=source_id,
        new_id=new_id,
        from_phase=from_phase,
        openai_key=openai_key,
        anthropic_key=anthropic_key,
    )


if __name__ == "__main__":
    main()
