"""Precompute Router"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional

from api._lib.precompute import (
    create_job, get_job, list_jobs, run_job,
    PrecomputeJob, CheckpointingPrecomputeEngine,
    load_resume_context, get_checkpoint_status,
    list_incomplete_jobs, cleanup_job_data
)

router = APIRouter(prefix="/api/precompute", tags=["precompute"])


class PromptTemplates(BaseModel):
    """Custom prompt templates for pre-computation phases"""
    # Phase 1 - Baseline Solutions
    U_SOLUTION_PROMPT: Optional[str] = None
    T_SOLUTION_PROMPT: Optional[str] = None

    # Phase 2 - Generate Backdoors
    DIFFICULTY_RATING_PROMPT: Optional[str] = None
    BACKDOOR_IDEAS_PROMPT: Optional[str] = None
    IMPLEMENT_BACKDOOR_PROMPT: Optional[str] = None
    CLEANUP_BACKDOOR_PROMPT: Optional[str] = None
    RATE_SNEAKINESS_PART1_PROMPT: Optional[str] = None
    RATE_SNEAKINESS_PART2_PROMPT: Optional[str] = None
    ESTIMATE_TRIGGER_RATE_PROMPT: Optional[str] = None

    # Phase 3 - Find Exploits
    SUSPICION_CHECK_PROMPT: Optional[str] = None
    IDENTIFY_SNIPPET_PROMPT: Optional[str] = None
    RECONSTRUCT_ORIGINAL_PROMPT: Optional[str] = None
    EXPLOIT_PROPERTIES_PROMPT: Optional[str] = None
    EXPLOIT_POSSIBLE_PROMPT: Optional[str] = None
    CONSTRUCT_EXPLOIT_PROMPT: Optional[str] = None
    VERIFY_EXPLOIT_PROMPT: Optional[str] = None

    # Phase 5 - Monitoring Scores
    T_SUSPICION_PROMPT: Optional[str] = None
    H_SUSPICION_PROMPT: Optional[str] = None


class PrecomputeRequest(BaseModel):
    num_problems: int = 75
    num_backdoor_ideas: int = 5
    max_difficulty: int = 6
    human_model: str = "simulated"
    trusted_model: str = "simulated"
    untrusted_model: str = "simulated"
    prompts: Optional[PromptTemplates] = None


@router.post("/start")
def start_precompute(
    config: PrecomputeRequest,
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key"),
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
):
    """Start a pre-computation job."""
    try:
        # Convert prompts to dict if provided
        job_config = config.model_dump()
        if config.prompts:
            # Extract only non-None prompts
            prompts_dict = {
                k: v for k, v in config.prompts.model_dump().items()
                if v is not None
            }
            job_config['prompts'] = prompts_dict if prompts_dict else None
        else:
            job_config['prompts'] = None

        # Create the job
        job = create_job(job_config)

        # Run it (synchronously for now - could be async in production)
        result = run_job(job.job_id, openai_key=x_openai_key, anthropic_key=x_anthropic_key)

        if not result:
            raise HTTPException(status_code=500, detail="Failed to start job")

        return {
            "job_id": result.job_id,
            "status": result.status,
            "num_problems": result.num_problems,
            "num_backdoor_ideas": result.num_backdoor_ideas,
            "human_model": result.human_model,
            "trusted_model": result.trusted_model,
            "untrusted_model": result.untrusted_model,
            "created_at": result.created_at,
            "current_phase": result.current_phase,
            "progress_percent": result.progress_percent,
        }

    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/jobs")
def list_precompute_jobs():
    """List all pre-computation jobs."""
    return {"jobs": list_jobs()}


@router.get("/jobs/{job_id}")
def get_precompute_job(job_id: str):
    """Get details of a specific pre-computation job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "job_id": job.job_id,
        "status": job.status,
        "num_problems": job.num_problems,
        "num_backdoor_ideas": job.num_backdoor_ideas,
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
        "problem_count": len(job.problems) if job.problems else 0,
    }


@router.post("/jobs/{job_id}/resume")
def resume_precompute_job(
    job_id: str,
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key"),
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
):
    """Resume an incomplete pre-computation job."""
    try:
        # Load resume context from Redis
        resume_context = load_resume_context(job_id)
        if not resume_context:
            raise HTTPException(
                status_code=404,
                detail="Job not found or no checkpoint data available"
            )

        if resume_context.job.status not in ("resumable", "failed", "running"):
            raise HTTPException(
                status_code=400,
                detail=f"Job cannot be resumed (status: {resume_context.job.status})"
            )

        # Create engine with resume context and run
        engine = CheckpointingPrecomputeEngine(
            job=resume_context.job,
            resume_context=resume_context
        )
        result = engine.run()

        return {
            "job_id": result.job_id,
            "status": result.status,
            "num_problems": result.num_problems,
            "num_backdoor_ideas": result.num_backdoor_ideas,
            "human_model": result.human_model,
            "trusted_model": result.trusted_model,
            "untrusted_model": result.untrusted_model,
            "created_at": result.created_at,
            "current_phase": result.current_phase,
            "progress_percent": result.progress_percent,
            "details": result.details,
            "error": result.error,
            "resumed": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/jobs/{job_id}/checkpoint")
def get_precompute_checkpoint(job_id: str):
    """Get checkpoint details for a pre-computation job."""
    checkpoint = get_checkpoint_status(job_id)
    if not checkpoint:
        raise HTTPException(status_code=404, detail="Checkpoint not found")

    return checkpoint


@router.get("/incomplete")
def get_incomplete_jobs():
    """List all incomplete/resumable pre-computation jobs."""
    job_ids = list_incomplete_jobs()

    # Get details for each incomplete job
    incomplete_jobs = []
    for job_id in job_ids:
        checkpoint = get_checkpoint_status(job_id)
        if checkpoint:
            incomplete_jobs.append({
                "job_id": job_id,
                "current_phase": checkpoint.get("phase_name", "Unknown"),
                "progress_percent": checkpoint.get("progress_percent", 0),
                "checkpoint_time": checkpoint.get("checkpoint_time"),
                "phases_completed": checkpoint.get("phases_completed", []),
            })

    return {"incomplete_jobs": incomplete_jobs}


@router.delete("/jobs/{job_id}/cleanup")
def cleanup_precompute_job(job_id: str, keep_results: bool = True):
    """Clean up intermediate data for a pre-computation job."""
    try:
        cleanup_job_data(job_id, keep_results=keep_results)
        return {
            "status": "cleaned",
            "job_id": job_id,
            "kept_results": keep_results
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
