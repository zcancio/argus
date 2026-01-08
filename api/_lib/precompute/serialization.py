"""
Serialization and Persistence for Pre-computation

Contains dict conversion functions and Redis I/O operations.
"""

import json
from dataclasses import asdict
from typing import List, Optional

from api._lib.storage import get_redis_client
from .models import (
    ProblemData, BackdoorProposal, PrecomputeJob, ResumeContext, CoupOutcome
)


# ============================================================================
# DICT CONVERSION HELPERS
# ============================================================================

def problem_to_dict(problem: ProblemData) -> dict:
    """Convert ProblemData to JSON-serializable dict"""
    d = asdict(problem)
    d['coup_outcome'] = problem.coup_outcome.value
    return d


def dict_to_problem(d: dict) -> ProblemData:
    """Convert dict back to ProblemData"""
    d = d.copy()
    d['coup_outcome'] = CoupOutcome(d['coup_outcome'])
    return ProblemData(**d)


def proposal_to_dict(proposal: BackdoorProposal) -> dict:
    """Convert BackdoorProposal to JSON-serializable dict"""
    return asdict(proposal)


def dict_to_proposal(d: dict) -> BackdoorProposal:
    """Convert dict back to BackdoorProposal"""
    return BackdoorProposal(**d)


def job_to_dict(job: PrecomputeJob) -> dict:
    """Convert PrecomputeJob to JSON-serializable dict (without problems)"""
    return {
        "job_id": job.job_id,
        "status": job.status,
        "num_problems": job.num_problems,
        "num_backdoor_ideas": job.num_backdoor_ideas,
        "max_difficulty": job.max_difficulty,
        "human_model": job.human_model,
        "trusted_model": job.trusted_model,
        "untrusted_model": job.untrusted_model,
        "created_at": job.created_at,
        "current_phase": job.current_phase,
        "progress_percent": job.progress_percent,
        "details": job.details,
        "error": job.error,
        "audit_threshold": job.audit_threshold,
        "defer_threshold": job.defer_threshold,
        "custom_prompts": job.custom_prompts,
    }


# ============================================================================
# REDIS I/O OPERATIONS
# ============================================================================

def load_resume_context(job_id: str) -> Optional[ResumeContext]:
    """Load resume context from Redis for a resumable job"""
    redis = get_redis_client()
    if not redis:
        return None

    # Load job metadata
    job_key = f"precompute:job:{job_id}"
    job_data = redis.get(job_key)
    if not job_data:
        return None

    job_dict = json.loads(job_data)

    # Reconstruct PrecomputeJob
    job = PrecomputeJob(
        job_id=job_dict["job_id"],
        status=job_dict["status"],
        num_problems=job_dict["num_problems"],
        num_backdoor_ideas=job_dict["num_backdoor_ideas"],
        max_difficulty=job_dict.get("max_difficulty", 6),
        human_model=job_dict["human_model"],
        trusted_model=job_dict["trusted_model"],
        untrusted_model=job_dict["untrusted_model"],
        created_at=job_dict["created_at"],
        current_phase=job_dict.get("current_phase", ""),
        progress_percent=job_dict.get("progress_percent", 0),
        details=job_dict.get("details", ""),
        error=job_dict.get("error"),
        audit_threshold=job_dict.get("audit_threshold", 0.0),
        defer_threshold=job_dict.get("defer_threshold", 0.0),
    )

    # Load checkpoint state
    checkpoint_key = f"precompute:job:{job_id}:checkpoint"
    checkpoint_data = redis.get(checkpoint_key)

    resume_phase = 1
    phases_completed = []
    if checkpoint_data:
        checkpoint = json.loads(checkpoint_data)
        resume_phase = checkpoint.get("current_phase", 1)
        phases_completed = checkpoint.get("phases_completed", [])

    # Load problems
    problems: List[ProblemData] = []
    problems_key = f"precompute:job:{job_id}:problems"
    problem_data = redis.hgetall(problems_key)
    for problem_json in problem_data.values():
        if isinstance(problem_json, bytes):
            problem_json = problem_json.decode('utf-8')
        problems.append(dict_to_problem(json.loads(problem_json)))

    # Load proposals
    proposals: List[BackdoorProposal] = []
    proposals_key = f"precompute:job:{job_id}:proposals"
    proposal_data = redis.hgetall(proposals_key)
    for proposal_json in proposal_data.values():
        if isinstance(proposal_json, bytes):
            proposal_json = proposal_json.decode('utf-8')
        proposals.append(dict_to_proposal(json.loads(proposal_json)))

    # Find the actual resume point
    resume_item_index = 0

    return ResumeContext(
        job=job,
        problems=problems,
        proposals=proposals,
        resume_phase=resume_phase,
        resume_item_index=resume_item_index,
        phases_completed=phases_completed
    )


def get_checkpoint_status(job_id: str) -> Optional[dict]:
    """Get checkpoint status for a job"""
    redis = get_redis_client()
    if not redis:
        return None

    checkpoint_key = f"precompute:job:{job_id}:checkpoint"
    checkpoint_data = redis.get(checkpoint_key)

    if not checkpoint_data:
        return None

    return json.loads(checkpoint_data)


def list_incomplete_jobs() -> List[str]:
    """List all incomplete/resumable job IDs"""
    redis = get_redis_client()
    if not redis:
        return []

    members = redis.smembers("precompute:jobs:incomplete")
    return [m.decode('utf-8') if isinstance(m, bytes) else m for m in members]


def cleanup_job_data(job_id: str, keep_results: bool = True):
    """Clean up intermediate data for a job"""
    redis = get_redis_client()
    if not redis:
        return

    # Keys to potentially clean
    proposals_key = f"precompute:job:{job_id}:proposals"
    api_cache_key = f"precompute:job:{job_id}:api_calls"
    checkpoint_key = f"precompute:job:{job_id}:checkpoint"

    # Always clean proposals and api cache (intermediate data)
    redis.delete(proposals_key)
    redis.delete(api_cache_key)

    if not keep_results:
        # Also clean final results
        job_key = f"precompute:job:{job_id}"
        problems_key = f"precompute:job:{job_id}:problems"
        index_key = f"precompute:job:{job_id}:problems:index"

        redis.delete(job_key)
        redis.delete(problems_key)
        redis.delete(index_key)
        redis.delete(checkpoint_key)

        # Remove from indexes
        redis.zrem("precompute:jobs:index", job_id)
        redis.srem("precompute:jobs:incomplete", job_id)
