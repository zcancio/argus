"""
Job Management for Pre-computation

Handles creation, storage, and execution of pre-computation jobs.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional

from api._lib.dataset import TestRunResult

from .models import PrecomputeJob
from .engines import PrecomputeEngine


# ============================================================================
# JOB STORAGE (in-memory for now, could be backed by database)
# ============================================================================

_precompute_jobs: Dict[str, PrecomputeJob] = {}


def create_job(config: dict) -> PrecomputeJob:
    """Create a new pre-computation job"""
    job_id = f"precompute_{uuid.uuid4().hex[:12]}"

    job = PrecomputeJob(
        job_id=job_id,
        status="pending",
        num_problems=config.get("num_problems", 75),
        num_backdoor_ideas=config.get("num_backdoor_ideas", 5),
        max_difficulty=config.get("max_difficulty", 6),
        human_model=config.get("human_model", "simulated"),
        trusted_model=config.get("trusted_model", "simulated"),
        untrusted_model=config.get("untrusted_model", "simulated"),
        created_at=datetime.utcnow().isoformat(),
        custom_prompts=config.get("prompts"),
    )

    _precompute_jobs[job_id] = job
    return job


def get_job(job_id: str) -> Optional[PrecomputeJob]:
    """Get a job by ID"""
    return _precompute_jobs.get(job_id)


def list_jobs(limit: int = 20) -> List[dict]:
    """List all jobs"""
    jobs = sorted(
        _precompute_jobs.values(),
        key=lambda j: j.created_at,
        reverse=True
    )[:limit]

    return [
        {
            "job_id": j.job_id,
            "status": j.status,
            "num_problems": j.num_problems,
            "num_backdoor_ideas": j.num_backdoor_ideas,
            "human_model": j.human_model,
            "trusted_model": j.trusted_model,
            "untrusted_model": j.untrusted_model,
            "created_at": j.created_at,
            "current_phase": j.current_phase,
            "progress_percent": j.progress_percent,
        }
        for j in jobs
    ]


def run_job(
    job_id: str,
    openai_key: str = None,
    anthropic_key: str = None,
    test_result: TestRunResult = None,
    on_update: callable = None
) -> Optional[PrecomputeJob]:
    """Run a pre-computation job"""
    job = _precompute_jobs.get(job_id)
    if not job:
        return None

    engine = PrecomputeEngine(
        job,
        openai_key=openai_key,
        anthropic_key=anthropic_key,
        test_result=test_result,
        on_update=on_update
    )
    return engine.run()
