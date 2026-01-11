"""APPS Problem Browser Router"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from api._lib.apps import get_apps_loader

router = APIRouter(prefix="/api/apps", tags=["apps"])


class APPSFilterRequest(BaseModel):
    """Request to filter APPS problems"""
    difficulty: Optional[list] = None  # ["introductory", "interview", "competition"]
    limit: Optional[int] = 50
    offset: Optional[int] = 0


@router.get("/problems")
def list_apps_problems(
    difficulty: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List/filter APPS problems.

    Query params:
    - difficulty: Comma-separated list of difficulty levels (e.g., "interview,competition")
    - limit: Maximum number to return (default 50)
    - offset: Skip this many problems (for pagination)
    """
    try:
        loader = get_apps_loader()

        # Parse difficulty filter
        diff_filter = None
        if difficulty:
            diff_filter = [d.strip() for d in difficulty.split(",")]

        problems = loader.list_problems(
            difficulty=diff_filter,
            limit=limit,
            offset=offset
        )

        # Get total count for pagination
        total = loader.count_problems(difficulty=diff_filter)

        return {
            "problems": problems,
            "total": total,
            "limit": limit,
            "offset": offset,
            "difficulties": loader.get_difficulties()
        }

    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/problems/{problem_id}")
def get_apps_problem(problem_id: str):
    """Get a specific APPS problem by ID."""
    try:
        loader = get_apps_loader()
        problem = loader.load_problem(problem_id)

        if not problem:
            raise HTTPException(status_code=404, detail=f"Problem {problem_id} not found")

        return problem.to_dict()

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")
