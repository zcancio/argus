#!/usr/bin/env python3
"""Rerun phase 5 for paper_baseline_cpp dataset (local files)."""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from datasets import load_dataset
from api._lib.precompute.single_problem.engine import SingleProblemEngine
from api._lib.dataset.models import ProblemResult
from api._lib.dataset.serialization import dict_to_problem_result

dataset_id = "paper_baseline_cpp"
dataset_dir = Path("datasets") / dataset_id
problems_dir = dataset_dir / "problems"

# Load config
with open(dataset_dir / "config.json") as f:
    config = json.load(f)

models = config.get("models", {})
problem_ids = config.get("problem_ids", [])
programming_language = config.get("settings", {}).get("programming_language", "C++")

print(f"Dataset: {dataset_id}")
print(f"Language: {programming_language}")
print(f"Models: {models}")
print(f"Problems: {problem_ids}")
print()

# Load APPS dataset
print("Loading APPS dataset...")
apps = load_dataset("codeparrot/apps", split="test")
apps_dict = {str(item["problem_id"]).zfill(4): item for item in apps}
print(f"Loaded {len(apps_dict)} problems from APPS")
print()

# Get API key
openai_key = os.environ.get("OPENAI_API_KEY")
if not openai_key:
    print("ERROR: OPENAI_API_KEY not set")
    print("Run: export OPENAI_API_KEY='your-key'")
    sys.exit(1)

# Rerun phase 5 for each problem
for i, problem_id in enumerate(problem_ids):
    print(f"[{i+1}/{len(problem_ids)}] Running phase 5 for {problem_id}...")

    # Load problem data from JSON
    problem_path = problems_dir / f"{problem_id}.json"
    with open(problem_path) as f:
        problem_data = json.load(f)

    if problem_data.get("difficulty_skipped"):
        print(f"  Skipping (too difficult)")
        continue

    # Get APPS problem
    apps_item = apps_dict.get(problem_id)
    if not apps_item:
        print(f"  ERROR: Problem not found in APPS")
        continue

    solutions = json.loads(apps_item["solutions"]) if apps_item["solutions"] else []

    try:
        # Convert dict to ProblemResult
        existing_result = dict_to_problem_result(problem_data)

        # Create engine
        engine = SingleProblemEngine(
            dataset_id=dataset_id,
            problem_id=problem_id,
            problem_text=apps_item["question"],
            solutions=solutions,
            models=models,
            openai_key=openai_key,
            programming_language=programming_language,
        )

        # Restore existing result data
        engine.result = existing_result
        engine.result.status = "running"
        engine.result.error = None

        # Clear phase 5 data
        engine.result.phases_completed = [p for p in engine.result.phases_completed if p < 5]
        engine.result.T_suspicion_normal = None
        engine.result.T_suspicion_backdoor = None
        engine.result.U_suspicion_normal = None
        engine.result.U_suspicion_backdoor = None
        engine.result.H_suspicion_normal = None
        engine.result.H_suspicion_backdoor = None
        engine.result.T_suspicious_snippet = None
        engine.result.U_explanation = None
        engine.result.U_explanation_claims_irrelevance = None
        engine.result.T_evaluation_with_skepticism = None
        engine.result.T_edited_code = None
        engine.result.T_edited_code_snippet = None
        engine.result.T_edited_code_inspired = None
        engine.result.coup_outcome_after_edit = None
        engine.result.T_edited_correct = None

        # Clear phase 5 LLM calls
        engine.result.llm_calls = [c for c in engine.result.llm_calls if c.phase < 5]
        engine._call_counter = len(engine.result.llm_calls)

        # Run from phase 5
        result = engine.run_from_phase(5)

        # Save result back to JSON
        from api._lib.dataset.serialization import problem_result_to_dict
        result_dict = problem_result_to_dict(result)
        with open(problem_path, "w") as f:
            json.dump(result_dict, f, indent=2)

        print(f"  Done: T_normal={result.T_suspicion_normal:.1f}, U_normal={result.U_suspicion_normal:.1f}")

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()

print()
print("Done!")
