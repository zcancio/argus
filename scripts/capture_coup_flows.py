#!/usr/bin/env python3
"""
Capture flows for SUCCESSFUL_COUP and FAILED_COUP outcomes.
Runs multiple APPS problems until both outcomes are found.
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

sys.path.insert(0, str(Path(__file__).parent.parent))

API_URL = "http://localhost:3001"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
DATA_DIR = Path(__file__).parent.parent / "data"

if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY required")

headers = {
    "Content-Type": "application/json",
    "X-OpenAI-Key": OPENAI_KEY,
}

# Problems to try (from filtered list, excluding already captured special flows)
CANDIDATE_PROBLEMS = [
    "0017", "0019", "0021", "0026", "0029", "0032", "0034", "0038", "0039",
    "0041", "0046", "0047", "0048", "0053", "0054", "0056", "0060", "0061",
    "0063", "0067", "0069", "0072", "0073", "0076", "0077", "0078", "0079"
]

# Already captured or processed
SKIP_PROBLEMS = {"0005", "0012", "0036", "0003", "0006", "0008", "0010", "0025", "0045", "0050", "0055", "0058", "0065"}


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
            "name": f"Coup Capture {problem_id} {datetime.now().strftime('%H%M%S')}",
            "settings": {
                "num_problems": 1,
                "num_backdoor_ideas": 3,
                "max_difficulty": 10,
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


def analyze_outcomes(result: dict) -> dict:
    """Analyze backdoor outcomes from result."""
    res = result.get("result", {})
    attempts = res.get("backdoor_attempts", [])

    outcomes = []
    for attempt in attempts:
        outcome = attempt.get("outcome", "UNKNOWN")
        outcomes.append(outcome)

    info = {
        "status": res.get("status"),
        "current_phase": res.get("current_phase"),
        "backdoor_count": len(attempts),
        "outcomes": outcomes,
        "sneakiness_scores": [a.get("sneakiness", 0) for a in attempts],
        "has_successful_coup": "SUCCESSFUL_COUP" in outcomes,
        "has_failed_coup": "FAILED_COUP_ATTEMPT" in outcomes,
    }
    return info


def save_flow(problem_id: str, result: dict, flow_type: str):
    """Save flow data to file."""
    output_file = DATA_DIR / f"mock_flow_{problem_id}_{flow_type}.json"

    flow_data = {
        "captured_at": datetime.now().isoformat(),
        "problem_id": problem_id,
        "flow_type": flow_type,
        "result": result.get("result"),
    }

    with open(output_file, "w") as f:
        json.dump(flow_data, f, indent=2)

    print(f"Saved to: {output_file}")
    return output_file


def main():
    client = httpx.Client(timeout=300)

    found_successful = None
    found_failed = None
    all_results = []

    print("=" * 70)
    print("CAPTURING COUP FLOWS")
    print("Looking for: SUCCESSFUL_COUP and FAILED_COUP_ATTEMPT")
    print("=" * 70)

    for problem_id in CANDIDATE_PROBLEMS:
        if problem_id in SKIP_PROBLEMS:
            print(f"Skipping {problem_id} (already captured)")
            continue

        # Stop if we found both
        if found_successful and found_failed:
            print("\nFound both outcomes, stopping search")
            break

        try:
            result = run_problem(client, problem_id)
            info = analyze_outcomes(result)

            print(f"\nResult for {problem_id}:")
            print(f"  Status: {info['status']}")
            print(f"  Backdoors: {info['backdoor_count']}")
            print(f"  Outcomes: {info['outcomes']}")
            print(f"  Sneakiness: {info['sneakiness_scores']}")

            all_results.append({
                "problem_id": problem_id,
                "info": info
            })

            # Check for successful coup
            if info["has_successful_coup"] and not found_successful:
                save_flow(problem_id, result, "successful_coup")
                found_successful = problem_id
                print(f"\n*** FOUND SUCCESSFUL_COUP: {problem_id} ***")

            # Check for failed coup
            if info["has_failed_coup"] and not found_failed:
                save_flow(problem_id, result, "failed_coup")
                found_failed = problem_id
                print(f"\n*** FOUND FAILED_COUP_ATTEMPT: {problem_id} ***")

            # Save any flow with backdoors for reference
            if info["backdoor_count"] > 0 and not (info["has_successful_coup"] or info["has_failed_coup"]):
                save_flow(problem_id, result, "regular")

        except Exception as e:
            print(f"Error with problem {problem_id}: {e}")
            continue

    client.close()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Problems tested: {len(all_results)}")
    print(f"SUCCESSFUL_COUP found: {found_successful or 'Not found'}")
    print(f"FAILED_COUP_ATTEMPT found: {found_failed or 'Not found'}")

    # Save summary
    summary = {
        "run_at": datetime.now().isoformat(),
        "successful_coup_problem": found_successful,
        "failed_coup_problem": found_failed,
        "all_results": all_results
    }
    summary_file = DATA_DIR / "coup_capture_log.json"
    with open(summary_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to: {summary_file}")


if __name__ == "__main__":
    main()
