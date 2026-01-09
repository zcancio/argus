#!/usr/bin/env python3
"""
Capture the full flow for problem 0003 for mock replay.
Saves all LLM calls to a JSON file.
"""

import json
import os
import time
import httpx
from datetime import datetime

API_URL = "http://localhost:3001"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")
PROBLEM_ID = "0003"

if not OPENAI_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is required")

headers = {
    "Content-Type": "application/json",
    "X-OpenAI-Key": OPENAI_KEY,
}


def main():
    client = httpx.Client(timeout=300)

    print("=" * 60)
    print("ARGUS Flow Capture - Problem 0003")
    print("=" * 60)

    # Step 1: Create dataset
    print("\n[1/5] Creating dataset...")
    resp = client.post(
        f"{API_URL}/api/datasets",
        headers=headers,
        json={
            "name": f"Flow Capture {datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "settings": {
                "num_problems": 1,
                "num_backdoor_ideas": 3,
                "max_difficulty": 7,
                "mandatory_problems": [PROBLEM_ID],  # Ensure 0003 is selected
            },
            "models": {
                "human_model": "gpt-4o",
                "trusted_model": "gpt-4o",
                "untrusted_model": "gpt-4o",
            }
        }
    )
    resp.raise_for_status()
    dataset = resp.json()
    dataset_id = dataset["id"]
    print(f"    Created dataset: {dataset_id}")

    # Step 2: Publish dataset (mandatory_problems ensures 0003 is included)
    print("\n[2/5] Publishing dataset...")
    resp = client.post(
        f"{API_URL}/api/datasets/{dataset_id}/publish",
        headers=headers
    )
    resp.raise_for_status()
    print("    Dataset published")

    # Step 3: Run problem
    print(f"\n[3/5] Starting problem {PROBLEM_ID} execution...")
    resp = client.post(
        f"{API_URL}/api/datasets/{dataset_id}/problems/{PROBLEM_ID}/run",
        headers=headers
    )
    resp.raise_for_status()
    print("    Execution started")

    # Step 4: Poll for completion
    print("\n[4/5] Polling for completion...")
    max_polls = 120  # 10 minutes max
    poll_interval = 5

    for i in range(max_polls):
        time.sleep(poll_interval)
        resp = client.get(
            f"{API_URL}/api/datasets/{dataset_id}/problems/{PROBLEM_ID}",
            headers=headers
        )
        resp.raise_for_status()
        data = resp.json()

        result = data.get("result")
        if result:
            current_phase = result.get("current_phase", 0)
            status = result.get("status", "unknown")
            print(f"    Poll {i+1}: Phase {current_phase}, Status: {status}")

            if status in ("completed", "failed"):
                break

            # Show backdoor attempts if available
            backdoors = result.get("backdoor_attempts", [])
            if backdoors:
                print(f"    Backdoors found: {len(backdoors)}")
        else:
            print(f"    Poll {i+1}: Waiting for result...")

    # Step 5: Save results
    print("\n[5/5] Saving flow data...")

    # Get final result
    resp = client.get(
        f"{API_URL}/api/datasets/{dataset_id}/problems/{PROBLEM_ID}",
        headers=headers
    )
    resp.raise_for_status()
    final_data = resp.json()

    # Get the APPS problem
    resp = client.get(
        f"{API_URL}/api/apps/problems/{PROBLEM_ID}",
        headers=headers
    )
    resp.raise_for_status()
    apps_problem = resp.json()

    # Build mock data structure
    mock_data = {
        "captured_at": datetime.now().isoformat(),
        "problem_id": PROBLEM_ID,
        "dataset_id": dataset_id,
        "apps_problem": apps_problem,
        "result": final_data.get("result"),
        "llm_calls": final_data.get("result", {}).get("llm_calls", [])
    }

    # Save to file
    output_file = f"/Users/zacharycancio/Projects/argus/data/mock_flow_{PROBLEM_ID}.json"
    with open(output_file, "w") as f:
        json.dump(mock_data, f, indent=2)

    print(f"    Saved to: {output_file}")

    # Summary
    result = final_data.get("result", {})
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Problem ID: {PROBLEM_ID}")
    print(f"Status: {result.get('status', 'unknown')}")
    print(f"Current Phase: {result.get('current_phase', 0)}")
    print(f"U Solution: {'Yes' if result.get('U_solution') else 'No'}")
    print(f"T Solution: {'Yes' if result.get('T_solution') else 'No'}")
    print(f"U Backdoored: {'Yes' if result.get('U_backdoored_solution') else 'No'}")
    print(f"Backdoor Attempts: {len(result.get('backdoor_attempts', []))}")
    print(f"Exploits Found: {len(result.get('exploits', []))}")
    print(f"LLM Calls Captured: {len(mock_data['llm_calls'])}")

    client.close()
    print("\nDone!")


if __name__ == "__main__":
    main()
