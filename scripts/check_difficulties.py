#!/usr/bin/env python3
"""
Check difficulty ratings for first 100 filtered APPS problems.
Uses LLM API with the app's difficulty rating prompt.

Supports custom endpoints encoded in model names:
- gpt-4o -> calls OpenAI as normal
- ollama.bantay.co/llama3.1:8b -> calls https://ollama.bantay.co/v1/
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

from api._lib.apps import APPSLoader
from api._lib.llm import LLMClient

# Load environment
load_dotenv()

# Default model - can be overridden via command line or environment
DEFAULT_MODEL = os.getenv("DIFFICULTY_MODEL", "gpt-4o")

DIFFICULTY_RATING_PROMPT = """Rate the difficulty of this coding problem on a scale of 1-10.

Problem: {problem_text}

Return only a number between 1 and 10."""

def rate_difficulty(client: LLMClient, model: str, problem_text: str) -> int:
    """Rate problem difficulty using LLM."""
    prompt = DIFFICULTY_RATING_PROMPT.format(problem_text=problem_text)

    response = client.complete(model, prompt, max_tokens=10)

    try:
        rating = int(response.strip().split()[0])
        return max(1, min(10, rating))
    except (ValueError, IndexError):
        return 5  # default


def main():
    # Get model from command line or environment
    model = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_MODEL

    # Initialize LLM client (handles custom endpoints automatically)
    client = LLMClient()

    if not client.is_available(model):
        print(f"Error: Model {model} is not available (missing API key or invalid endpoint)")
        sys.exit(1)

    print(f"Using model: {model}")

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
        difficulty = rate_difficulty(client, model, problem.question)
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
