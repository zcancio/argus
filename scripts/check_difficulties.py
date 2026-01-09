#!/usr/bin/env python3
"""
Check difficulty ratings for first 100 filtered APPS problems.
Uses OpenAI API with the app's difficulty rating prompt.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from openai import OpenAI

from api._lib.apps import APPSLoader

# Load environment
load_dotenv()

DIFFICULTY_RATING_PROMPT = """Rate the difficulty of this coding problem on a scale of 1-10.

Problem: {problem_text}

Return only a number between 1 and 10."""

def rate_difficulty(client: OpenAI, problem_text: str) -> int:
    """Rate problem difficulty using OpenAI."""
    prompt = DIFFICULTY_RATING_PROMPT.format(problem_text=problem_text)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=10,
        temperature=0
    )

    try:
        rating = int(response.choices[0].message.content.strip().split()[0])
        return max(1, min(10, rating))
    except (ValueError, IndexError):
        return 5  # default


def main():
    # Initialize OpenAI client
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found in environment")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    # Load problems
    print("Loading APPS problems...")
    loader = APPSLoader()

    # Get first 100 problem IDs
    problems_list = loader.list_problems(limit=100)
    print(f"Found {len(problems_list)} problems to rate")

    results = []

    for i, prob_info in enumerate(problems_list):
        problem_id = prob_info["problem_id"]
        problem = loader.load_problem(problem_id)

        if not problem:
            print(f"[{i+1}/100] Problem {problem_id}: FAILED TO LOAD")
            continue

        # Rate difficulty
        difficulty = rate_difficulty(client, problem.question)
        results.append({
            "problem_id": problem_id,
            "difficulty": difficulty
        })

        print(f"[{i+1}/100] Problem {problem_id}: difficulty = {difficulty}")

    # Save results
    output_path = Path(__file__).parent.parent / "data" / "difficulty_ratings.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}")

    # Summary
    difficulties = [r["difficulty"] for r in results]
    print(f"\nSummary:")
    print(f"  Total rated: {len(results)}")
    print(f"  Average difficulty: {sum(difficulties)/len(difficulties):.1f}")
    print(f"  Min: {min(difficulties)}, Max: {max(difficulties)}")

    # Distribution
    print(f"\nDistribution:")
    for d in range(1, 11):
        count = difficulties.count(d)
        bar = "█" * count
        print(f"  {d:2d}: {bar} ({count})")


if __name__ == "__main__":
    main()
