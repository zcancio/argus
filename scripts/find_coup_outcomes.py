#!/usr/bin/env python3
"""
Run capture flows until we find both successful_coup and failed_coup outcomes.
Stops after max_tries or when both outcomes are found.
"""

import json
import os
import time
import httpx
import sys
from datetime import datetime
from pathlib import Path

# Load .env file
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), value)

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api._lib.apps import APPSLoader

API_URL = "http://localhost:3001"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
MAX_TRIES = 10

if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY required")

headers = {
    "Content-Type": "application/json",
    "X-OpenAI-Key": OPENAI_KEY,
}


def run_problem(client: httpx.Client, problem_id: str) -> dict:
    """Run a single problem and return the result."""
    print(f"\n{'='*60}")
    print(f"Running problem {problem_id}")
    print('='*60)

    # Create dataset
    print("[1/4] Creating dataset...")
    resp = client.post(
        f"{API_URL}/api/datasets",
        headers=headers,
        json={
            "name": f"Coup Test {problem_id} {datetime.now().strftime('%H%M%S')}",
            "settings": {
                "num_problems": 1,
                "num_backdoor_ideas": 3,
                "max_difficulty": 10,  # Allow all difficulties
                "mandatory_problems": [problem_id],
            },
            "models": {
                "human_model": "gpt-4o",
                "trusted_model": "gpt-4o",
                "untrusted_model": "gpt-4o",
                "red_team_model": "gpt-4o",
            }
        }
    )
    resp.raise_for_status()
    dataset = resp.json()
    dataset_id = dataset["id"]
    print(f"    Dataset: {dataset_id}")

    # Publish
    print("[2/4] Publishing...")
    resp = client.post(f"{API_URL}/api/datasets/{dataset_id}/publish", headers=headers)
    resp.raise_for_status()

    # Run
    print("[3/4] Running problem...")
    resp = client.post(f"{API_URL}/api/datasets/{dataset_id}/problems/{problem_id}/run", headers=headers)
    resp.raise_for_status()

    # Poll for completion
    print("[4/4] Waiting for completion...")
    max_polls = 120
    for i in range(max_polls):
        time.sleep(5)
        resp = client.get(f"{API_URL}/api/datasets/{dataset_id}/problems/{problem_id}", headers=headers)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("result")

        if result:
            status = result.get("status", "unknown")
            phase = result.get("current_phase", 0)
            print(f"    Poll {i+1}: Phase {phase}, Status: {status}")

            if status in ("completed", "failed"):
                break
        else:
            print(f"    Poll {i+1}: Waiting...")

    # Get final result
    resp = client.get(f"{API_URL}/api/datasets/{dataset_id}/problems/{problem_id}", headers=headers)
    resp.raise_for_status()
    return resp.json()


def extract_outcomes(result: dict) -> list:
    """Extract coup outcomes from backdoor attempts."""
    outcomes = []
    backdoor_attempts = result.get("result", {}).get("backdoor_attempts", [])
    for attempt in backdoor_attempts:
        outcome = attempt.get("outcome", "unknown")
        outcomes.append(outcome)
    return outcomes


def main():
    # Load filtered problems
    print("Loading filtered APPS problems...")
    loader = APPSLoader()
    problems = loader.list_problems(limit=50)  # Get more than we need
    problem_ids = [p["problem_id"] for p in problems]
    print(f"Found {len(problem_ids)} problems")

    client = httpx.Client(timeout=300)

    found_successful = None
    found_failed = None
    results_log = []

    for i, problem_id in enumerate(problem_ids):
        if i >= MAX_TRIES:
            print(f"\nReached max tries ({MAX_TRIES})")
            break

        if found_successful and found_failed:
            print(f"\nFound both outcomes!")
            break

        try:
            result = run_problem(client, problem_id)
            outcomes = extract_outcomes(result)

            print(f"\nOutcomes for problem {problem_id}: {outcomes}")

            # Check for outcomes we need
            has_successful = "SUCCESSFUL_COUP" in outcomes
            has_failed = "FAILED_COUP_ATTEMPT" in outcomes

            results_log.append({
                "problem_id": problem_id,
                "outcomes": outcomes,
                "has_successful_coup": has_successful,
                "has_failed_coup": has_failed,
            })

            if has_successful and not found_successful:
                found_successful = problem_id
                print(f"*** Found SUCCESSFUL_COUP: problem {problem_id}")

            if has_failed and not found_failed:
                found_failed = problem_id
                print(f"*** Found FAILED_COUP_ATTEMPT: problem {problem_id}")

            # Save full result for reference
            output_file = Path(__file__).parent.parent / "data" / f"mock_flow_{problem_id}.json"
            with open(output_file, "w") as f:
                json.dump({
                    "captured_at": datetime.now().isoformat(),
                    "problem_id": problem_id,
                    "result": result.get("result"),
                    "outcomes": outcomes,
                }, f, indent=2)

        except Exception as e:
            print(f"Error running problem {problem_id}: {e}")
            results_log.append({
                "problem_id": problem_id,
                "error": str(e),
            })

    client.close()

    # Save results log
    log_file = Path(__file__).parent.parent / "data" / "coup_outcomes_log.json"
    with open(log_file, "w") as f:
        json.dump({
            "run_at": datetime.now().isoformat(),
            "found_successful_coup": found_successful,
            "found_failed_coup": found_failed,
            "results": results_log,
        }, f, indent=2)

    # Print summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Problems tested: {len(results_log)}")
    print(f"SUCCESSFUL_COUP found: {found_successful or 'None'}")
    print(f"FAILED_COUP_ATTEMPT found: {found_failed or 'None'}")
    print(f"\nResults saved to: {log_file}")

    if found_successful and found_failed:
        print("\n*** SUCCESS: Found both outcome types! ***")
        print(f"  - Use problem {found_successful} for successful_coup tests")
        print(f"  - Use problem {found_failed} for failed_coup tests")


if __name__ == "__main__":
    main()
