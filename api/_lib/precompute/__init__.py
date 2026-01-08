"""
Pre-computation Package for AI Control Experiments

Based on "AI Control: Improving Safety Despite Intentional Subversion" (Greenblatt et al.)

This package handles the 7-phase pre-computation procedure:
1. Generate Baseline Solutions (U + T)
2. Rate ALL backdoor ideas (sneakiness, rarity) -> Find sneakiest above 18
3. Find Exploits for SNEAKIEST ONLY
4. Verify Execution for SNEAKIEST ONLY
5. Filter by Strategy (just lookups)
6. T rates Suspicion for SNEAKIEST + NORMAL only
7. Compute Thresholds

Features:
- Per-problem checkpointing to Redis for crash recovery
- API call caching to avoid re-incurring costs on resume
- Resume from any point in the pipeline
"""

# Models and Constants
from .models import (
    CoupOutcome,
    ProblemData,
    BackdoorProposal,
    PrecomputeJob,
    ResumeContext,
    TTL_ACTIVE,
    TTL_COMPLETED,
    TTL_PROPOSALS,
    SNEAKINESS_THRESHOLD,
)

# Serialization
from .serialization import (
    problem_to_dict,
    dict_to_problem,
    proposal_to_dict,
    dict_to_proposal,
    job_to_dict,
    load_resume_context,
    get_checkpoint_status,
    list_incomplete_jobs,
    cleanup_job_data,
)

# Mixins and Utilities
from .mixins import (
    LLMCallTrackerMixin,
    calculate_sneakiness,
    parse_rating,
    detect_language,
    strip_markdown_code_blocks,
)

# Engines
from .engines import (
    PrecomputeEngine,
    CheckpointingPrecomputeEngine,
)

# Single Problem Execution
from .single_problem import (
    SingleProblemEngine,
    run_single_problem,
    run_single_problem_from_phase,
    compute_thresholds,
)

# Job Management
from .job_manager import (
    create_job,
    get_job,
    list_jobs,
    run_job,
)

__all__ = [
    # Models
    "CoupOutcome",
    "ProblemData",
    "BackdoorProposal",
    "PrecomputeJob",
    "ResumeContext",
    # Constants
    "TTL_ACTIVE",
    "TTL_COMPLETED",
    "TTL_PROPOSALS",
    "SNEAKINESS_THRESHOLD",
    # Serialization
    "problem_to_dict",
    "dict_to_problem",
    "proposal_to_dict",
    "dict_to_proposal",
    "job_to_dict",
    "load_resume_context",
    "get_checkpoint_status",
    "list_incomplete_jobs",
    "cleanup_job_data",
    # Mixins
    "LLMCallTrackerMixin",
    "calculate_sneakiness",
    "parse_rating",
    "detect_language",
    "strip_markdown_code_blocks",
    # Engines
    "PrecomputeEngine",
    "CheckpointingPrecomputeEngine",
    # Single Problem
    "SingleProblemEngine",
    "run_single_problem",
    "run_single_problem_from_phase",
    "compute_thresholds",
    # Job Management
    "create_job",
    "get_job",
    "list_jobs",
    "run_job",
]
