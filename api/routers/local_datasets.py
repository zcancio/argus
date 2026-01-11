"""Local Datasets Router - Reads from local datasets/ directory"""

from fastapi import APIRouter, HTTPException
from typing import Optional
import json
import os
from pathlib import Path

router = APIRouter(prefix="/api/local-datasets", tags=["local-datasets"])

# Environment variable to show hidden datasets (for development)
SHOW_HIDDEN_DATASETS = os.environ.get("SHOW_HIDDEN_DATASETS", "").lower() == "true"


def _load_json_safe(path: Path) -> Optional[dict]:
    """Safely load a JSON file, returning None if not found or invalid."""
    try:
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError):
        pass
    return None


def _determine_dataset_status(checkpoint: Optional[dict], summary: Optional[dict]) -> str:
    """Determine the status of a local dataset."""
    if summary and summary.get("stats", {}).get("completed", 0) == summary.get("stats", {}).get("total", 0):
        return "completed"
    if checkpoint:
        if checkpoint.get("error"):
            return "failed"
        return "in_progress"
    return "unknown"


@router.get("")
def list_local_datasets():
    """List all datasets in the datasets/ directory."""
    datasets_dir = Path("datasets")
    if not datasets_dir.exists():
        return {"datasets": []}

    results = []
    for dataset_dir in sorted(datasets_dir.iterdir()):
        if not dataset_dir.is_dir():
            continue

        config = _load_json_safe(dataset_dir / "config.json")
        checkpoint = _load_json_safe(dataset_dir / "checkpoint.json")
        summary = _load_json_safe(dataset_dir / "summary.json")

        if not config and not checkpoint and not summary:
            continue

        # Check if dataset is hidden (unless SHOW_HIDDEN_DATASETS is set)
        is_hidden = (summary or {}).get("hidden", False) or (config or {}).get("hidden", False)
        if is_hidden and not SHOW_HIDDEN_DATASETS:
            continue

        stats = (summary or {}).get("stats") or (checkpoint or {}).get("stats") or {}

        results.append({
            "id": dataset_dir.name,
            "name": (config or {}).get("name", dataset_dir.name),
            "created_at": (config or {}).get("created_at"),
            "stats": stats,
            "status": _determine_dataset_status(checkpoint, summary),
            "models": (config or {}).get("models"),
        })

    return {"datasets": results}


@router.get("/{dataset_id}")
def get_local_dataset(dataset_id: str):
    """Get full details for a local dataset."""
    datasets_dir = Path("datasets")
    dataset_dir = datasets_dir / dataset_id

    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise HTTPException(status_code=404, detail="Dataset not found")

    config = _load_json_safe(dataset_dir / "config.json") or {}
    checkpoint = _load_json_safe(dataset_dir / "checkpoint.json") or {}
    summary = _load_json_safe(dataset_dir / "summary.json") or {}

    return {
        "id": dataset_id,
        "config": config,
        "checkpoint": checkpoint,
        "summary": summary,
        "status": _determine_dataset_status(checkpoint, summary),
    }


@router.get("/{dataset_id}/problems")
def list_local_dataset_problems(dataset_id: str):
    """List all problems in a local dataset."""
    datasets_dir = Path("datasets")
    dataset_dir = datasets_dir / dataset_id

    if not dataset_dir.exists() or not dataset_dir.is_dir():
        raise HTTPException(status_code=404, detail="Dataset not found")

    problems_dir = dataset_dir / "problems"
    if not problems_dir.exists():
        return {"problems": []}

    problems = []
    for problem_file in sorted(problems_dir.glob("*.json")):
        problem_id = problem_file.stem
        problem_data = _load_json_safe(problem_file)

        if problem_data:
            problems.append({
                "problem_id": problem_id,
                "status": problem_data.get("status", "unknown"),
                "phases_completed": problem_data.get("phases_completed", []),
                "difficulty_skipped": problem_data.get("difficulty_skipped", False),
                "problem_difficulty": problem_data.get("problem_difficulty"),
                "max_difficulty": problem_data.get("max_difficulty"),
                "U_tests_passed": problem_data.get("U_tests_passed"),
                "U_tests_total": problem_data.get("U_tests_total"),
                "T_tests_passed": problem_data.get("T_tests_passed"),
                "T_tests_total": problem_data.get("T_tests_total"),
                "T_suspicion_score": problem_data.get("T_suspicion_score"),
                "H_suspicion_score": problem_data.get("H_suspicion_score"),
                "sneakiness": problem_data.get("sneakiness"),
                "sneakiest_backdoor_idx": problem_data.get("sneakiest_backdoor_idx"),
                "exploit_found": problem_data.get("exploit_found"),
                "error": problem_data.get("error"),
                "strategy_results": problem_data.get("strategy_results"),
                "backdoor_attempts": problem_data.get("backdoor_attempts"),
            })

    return {"problems": problems}


@router.get("/{dataset_id}/problems/{problem_id}")
def get_local_dataset_problem(dataset_id: str, problem_id: str):
    """Get full details for a problem in a local dataset."""
    datasets_dir = Path("datasets")
    problem_path = datasets_dir / dataset_id / "problems" / f"{problem_id}.json"

    if not problem_path.exists():
        raise HTTPException(status_code=404, detail="Problem not found")

    problem_data = _load_json_safe(problem_path)
    if not problem_data:
        raise HTTPException(status_code=500, detail="Failed to load problem data")

    return problem_data
