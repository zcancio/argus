"""Datasets Router - Dataset management and problem execution"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import threading
import logging
import os

from api._lib.dataset import (
    dataset_store, Dataset, DatasetSettings, DatasetModels,
    dataset_to_dict, dict_to_settings, dict_to_models,
    create_dataset, get_dataset, update_dataset, delete_dataset,
    list_datasets, publish_dataset, duplicate_dataset,
    problem_result_to_dict,
    dict_to_problem_result, dict_to_backdoor_attempt,
    dict_to_strategy_result, dict_to_llm_call,
    ProblemResult, BackdoorAttempt, StrategyResult, LLMCall,
)
from api._lib.apps import get_apps_loader
from api._lib.precompute import (
    create_job, run_job,
    run_single_problem, run_single_problem_from_phase, compute_thresholds
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/datasets", tags=["datasets"])


# =============================================================================
# REQUEST MODELS
# =============================================================================

class DatasetSettingsModel(BaseModel):
    """Dataset settings for pre-computation"""
    num_problems: int = 5
    num_backdoor_ideas: int = 3
    max_difficulty: int = 6
    mandatory_problems: List[str] = []


class DatasetModelsModel(BaseModel):
    """Model role assignments"""
    human_model: str = "gpt-4o"
    trusted_model: str = "gpt-3.5-turbo"
    untrusted_model: str = "gpt-4o"
    red_team_model: str = "gpt-4o"


class DatasetCreateRequest(BaseModel):
    """Request to create a new dataset"""
    name: str
    settings: Optional[DatasetSettingsModel] = None
    models: Optional[DatasetModelsModel] = None
    prompts: Optional[dict] = None


class DatasetUpdateRequest(BaseModel):
    """Request to update a dataset"""
    name: Optional[str] = None
    settings: Optional[DatasetSettingsModel] = None
    models: Optional[DatasetModelsModel] = None
    prompts: Optional[dict] = None


class DatasetDuplicateRequest(BaseModel):
    """Request to duplicate a dataset"""
    new_name: Optional[str] = None


class AddProblemsRequest(BaseModel):
    """Request to add problems to a dataset"""
    problem_ids: list  # List of APPS problem IDs


class SetProblemsRequest(BaseModel):
    """Request to set the problem list for a dataset"""
    problem_ids: list  # List of APPS problem IDs


class RunFromPhaseRequest(BaseModel):
    from_phase: int


class ImportProblemResultRequest(BaseModel):
    """Request body for importing a pre-computed problem result."""
    problem_id: str
    status: str = "completed"
    phases_completed: List[int] = []
    U_normal_solution: Optional[str] = None
    T_solution: Optional[str] = None
    U_tests_passed: Optional[int] = None
    U_tests_total: Optional[int] = None
    T_tests_passed: Optional[int] = None
    T_tests_total: Optional[int] = None
    problem_difficulty: Optional[int] = None
    max_difficulty: Optional[int] = None
    difficulty_skipped: bool = False
    T_suspicion_normal: Optional[float] = None
    T_suspicion_backdoor: Optional[float] = None
    H_suspicion_normal: Optional[float] = None
    H_suspicion_backdoor: Optional[float] = None
    sneakiest_backdoor_idx: Optional[int] = None
    strategy_results: Optional[Dict[str, Any]] = None
    backdoor_attempts: Optional[List[Dict[str, Any]]] = None
    llm_calls: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ImportThresholdsRequest(BaseModel):
    """Request body for importing computed thresholds."""
    audit_threshold: Optional[float] = None
    defer_threshold: Optional[float] = None


# =============================================================================
# DATASET CRUD ENDPOINTS
# =============================================================================

@router.get("")
def list_all_datasets():
    """List all datasets."""
    datasets = list_datasets(limit=50)
    return {
        "datasets": [dataset_to_dict(d) for d in datasets],
        "storage": "persistent" if dataset_store.is_persistent else "in-memory"
    }


@router.post("")
def create_new_dataset(request: DatasetCreateRequest):
    """Create a new dataset."""
    try:
        settings = request.settings.model_dump() if request.settings else None
        models = request.models.model_dump() if request.models else None

        dataset = create_dataset(
            name=request.name,
            settings=settings,
            models=models,
            prompts=request.prompts
        )

        return dataset_to_dict(dataset)

    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/{dataset_id}")
def get_single_dataset(dataset_id: str):
    """Get a specific dataset by ID."""
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return dataset_to_dict(dataset)


@router.put("/{dataset_id}")
def update_existing_dataset(dataset_id: str, request: DatasetUpdateRequest):
    """Update a draft dataset."""
    try:
        settings = request.settings.model_dump() if request.settings else None
        models = request.models.model_dump() if request.models else None

        dataset = update_dataset(
            dataset_id=dataset_id,
            name=request.name,
            settings=settings,
            models=models,
            prompts=request.prompts
        )

        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return dataset_to_dict(dataset)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.delete("/{dataset_id}")
def delete_existing_dataset(dataset_id: str):
    """Delete a dataset (both draft and published)."""
    try:
        success = delete_dataset(dataset_id)
        if not success:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return {"status": "deleted", "dataset_id": dataset_id}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =============================================================================
# DATASET TEST ENDPOINTS
# =============================================================================

@router.post("/{dataset_id}/test")
def start_dataset_test(
    dataset_id: str,
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key"),
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
):
    """Start a test run for a dataset (1 problem through all 7 phases)."""
    try:
        logger.info(f"[TEST] Received headers - OpenAI key: {'present' if x_openai_key else 'missing'}, Anthropic key: {'present' if x_anthropic_key else 'missing'}")

        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset.status != "draft":
            raise HTTPException(status_code=400, detail="Can only test draft datasets")

        # Start test run
        test_result = dataset_store.start_test(dataset_id)
        if not test_result:
            raise HTTPException(status_code=500, detail="Failed to start test")

        # Create a pre-compute job with num_problems=1 using dataset config
        job_config = {
            "num_problems": 1,  # Test mode: only 1 problem
            "num_backdoor_ideas": dataset.settings.num_backdoor_ideas,
            "max_difficulty": dataset.settings.max_difficulty,
            "human_model": dataset.models.human_model,
            "trusted_model": dataset.models.trusted_model,
            "untrusted_model": dataset.models.untrusted_model,
            "red_team_model": dataset.models.red_team_model,
            "prompts": dataset.prompts if dataset.prompts else None,
        }

        job = create_job(job_config)

        # Run test in background thread so we can return immediately
        def run_test_async():
            try:
                # Create update callback to persist LLM call progress
                def on_update(updated_result):
                    dataset_store.update_test(dataset_id, updated_result)

                result = run_job(
                    job.job_id,
                    openai_key=x_openai_key,
                    anthropic_key=x_anthropic_key,
                    test_result=test_result,
                    on_update=on_update
                )

                if result:
                    # Update test result with completion
                    from datetime import datetime
                    test_result.status = "completed" if result.status == "completed" else "failed"
                    test_result.completed_at = datetime.utcnow().isoformat()
                    test_result.current_phase = result.current_phase
                    test_result.progress_percent = result.progress_percent
                    test_result.phases_completed = [1, 2, 3, 4, 5, 6, 7] if result.status == "completed" else []
                    test_result.error = result.error
                    test_result.problems_generated = len(result.problems) if result.problems else 0

                    # Count backdoors and exploits
                    backdoors = sum(1 for p in result.problems if p.U_backdoored_solution) if result.problems else 0
                    exploits = sum(1 for p in result.problems if p.exploits) if result.problems else 0
                    test_result.backdoors_generated = backdoors
                    test_result.exploits_found = exploits

                    dataset_store.update_test(dataset_id, test_result)
            except Exception as e:
                logger.error(f"[TEST] Background test failed: {e}")
                test_result.status = "failed"
                test_result.error = str(e)
                dataset_store.update_test(dataset_id, test_result)

        # Start background thread
        thread = threading.Thread(target=run_test_async, daemon=True)
        thread.start()

        # Return immediately - frontend will poll GET endpoint for updates
        return {
            "test_id": test_result.test_id,
            "status": test_result.status,
            "current_phase": test_result.current_phase,
            "progress_percent": test_result.progress_percent,
            "phases_completed": test_result.phases_completed,
            "problems_generated": 0,
            "backdoors_generated": 0,
            "exploits_found": 0,
            "error": None,
            "llm_calls": []
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/{dataset_id}/test")
def get_dataset_test_status(dataset_id: str):
    """Get test run status for a dataset."""
    test_result = dataset_store.get_test_status(dataset_id)
    if not test_result:
        raise HTTPException(status_code=404, detail="No test run found")

    # Serialize LLM calls
    llm_calls = []
    for call in test_result.llm_calls:
        llm_calls.append({
            "call_id": call.call_id,
            "phase": call.phase,
            "step": call.step,
            "model": call.model,
            "prompt": call.prompt,
            "response": call.response,
            "status": call.status,
            "started_at": call.started_at,
            "completed_at": call.completed_at,
            "error": call.error
        })

    return {
        "test_id": test_result.test_id,
        "status": test_result.status,
        "started_at": test_result.started_at,
        "completed_at": test_result.completed_at,
        "current_phase": test_result.current_phase,
        "progress_percent": test_result.progress_percent,
        "phases_completed": test_result.phases_completed,
        "problems_generated": test_result.problems_generated,
        "backdoors_generated": test_result.backdoors_generated,
        "exploits_found": test_result.exploits_found,
        "error": test_result.error,
        "llm_calls": llm_calls
    }


# =============================================================================
# DATASET PUBLISH/DUPLICATE ENDPOINTS
# =============================================================================

@router.post("/{dataset_id}/publish")
def publish_existing_dataset(dataset_id: str):
    """Publish a dataset (lock it permanently)."""
    try:
        dataset = publish_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return dataset_to_dict(dataset)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{dataset_id}/duplicate")
def duplicate_existing_dataset(dataset_id: str, request: DatasetDuplicateRequest):
    """Create a draft copy of any dataset."""
    try:
        dataset = duplicate_dataset(dataset_id, request.new_name)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        return dataset_to_dict(dataset)

    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


# =============================================================================
# DATASET PROBLEM MANAGEMENT ENDPOINTS
# =============================================================================

@router.get("/{dataset_id}/problems")
def get_dataset_problems(dataset_id: str):
    """Get all problems in a dataset with their results."""
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Get all problem results
    results = dataset_store.get_all_problem_results(dataset_id)

    # Build response with problem info and results
    problems_data = []
    loader = get_apps_loader()

    for problem_id in dataset.problem_ids:
        problem_info = {"problem_id": problem_id}

        # Try to get APPS problem metadata
        apps_problem = loader.load_problem(problem_id)
        if apps_problem:
            problem_info["difficulty"] = apps_problem.difficulty
            problem_info["question_preview"] = apps_problem.question[:200] + "..." if len(apps_problem.question) > 200 else apps_problem.question

        # Get result if exists
        result = results.get(problem_id)
        if result:
            problem_info["result"] = problem_result_to_dict(result)
        else:
            problem_info["result"] = None

        problems_data.append(problem_info)

    return {
        "dataset_id": dataset_id,
        "problems": problems_data,
        "total": len(dataset.problem_ids)
    }


@router.post("/{dataset_id}/problems")
def add_dataset_problems(dataset_id: str, request: AddProblemsRequest):
    """Add problems to a dataset."""
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset.status != "draft":
            raise HTTPException(status_code=400, detail="Cannot modify a published dataset")

        # Validate problem IDs
        loader = get_apps_loader()
        valid_results = loader.validate_problem_ids(request.problem_ids)

        invalid = [pid for pid, valid in valid_results.items() if not valid]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid problem IDs: {', '.join(invalid)}"
            )

        # Add each problem
        for problem_id in request.problem_ids:
            dataset_store.add_problem(dataset_id, problem_id)

        # Get updated dataset
        dataset = get_dataset(dataset_id)

        return {
            "dataset_id": dataset_id,
            "problem_ids": dataset.problem_ids,
            "total": len(dataset.problem_ids)
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.put("/{dataset_id}/problems")
def set_dataset_problems(dataset_id: str, request: SetProblemsRequest):
    """Set the complete list of problems for a dataset (replaces existing)."""
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset.status != "draft":
            raise HTTPException(status_code=400, detail="Cannot modify a published dataset")

        # Validate problem IDs
        loader = get_apps_loader()
        valid_results = loader.validate_problem_ids(request.problem_ids)

        invalid = [pid for pid, valid in valid_results.items() if not valid]
        if invalid:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid problem IDs: {', '.join(invalid)}"
            )

        # Set problems
        dataset = dataset_store.set_problems(dataset_id, request.problem_ids)

        return {
            "dataset_id": dataset_id,
            "problem_ids": dataset.problem_ids,
            "total": len(dataset.problem_ids)
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.delete("/{dataset_id}/problems/{problem_id}")
def remove_dataset_problem(dataset_id: str, problem_id: str):
    """Remove a problem from a dataset."""
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if problem_id not in dataset.problem_ids:
            raise HTTPException(status_code=404, detail="Problem not in dataset")

        dataset = dataset_store.remove_problem(dataset_id, problem_id)

        return {
            "status": "removed",
            "dataset_id": dataset_id,
            "problem_id": problem_id,
            "remaining": len(dataset.problem_ids)
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.get("/{dataset_id}/problems/{problem_id}")
def get_dataset_problem_result(dataset_id: str, problem_id: str):
    """Get the result and logs for a specific problem."""
    dataset = get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    if problem_id not in dataset.problem_ids:
        raise HTTPException(status_code=404, detail="Problem not in dataset")

    result = dataset_store.get_problem_result(dataset_id, problem_id)

    # Get APPS problem info
    loader = get_apps_loader()
    apps_problem = loader.load_problem(problem_id)

    response = {
        "problem_id": problem_id,
        "apps_problem": apps_problem.to_dict() if apps_problem else None,
        "result": problem_result_to_dict(result) if result else None
    }

    return response


# =============================================================================
# PROBLEM EXECUTION ENDPOINTS
# =============================================================================

@router.post("/{dataset_id}/problems/{problem_id}/run")
def run_dataset_problem(
    dataset_id: str,
    problem_id: str,
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key"),
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
):
    """Run phases 1-6 for a single problem. Only allowed for published datasets."""
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset.status != "published":
            raise HTTPException(
                status_code=400,
                detail="Cannot run problems on draft datasets. Publish the dataset first."
            )

        if problem_id not in dataset.problem_ids:
            raise HTTPException(status_code=404, detail="Problem not in dataset")

        # Load APPS problem
        loader = get_apps_loader()
        apps_problem = loader.load_problem(problem_id)
        if not apps_problem:
            raise HTTPException(status_code=404, detail=f"APPS problem {problem_id} not found")

        # Build models dict
        models = {
            "human_model": dataset.models.human_model,
            "trusted_model": dataset.models.trusted_model,
            "untrusted_model": dataset.models.untrusted_model,
            "red_team_model": dataset.models.red_team_model
        }

        # Run in background thread
        def run_problem_async():
            try:
                run_single_problem(
                    dataset_id=dataset_id,
                    problem_id=problem_id,
                    problem_text=apps_problem.question,
                    solutions=apps_problem.solutions,
                    models=models,
                    prompts=dataset.prompts if dataset.prompts else None,
                    openai_key=x_openai_key,
                    anthropic_key=x_anthropic_key,
                    piston_url=os.environ.get("PISTON_URL"),
                    test_cases=apps_problem.test_cases,
                    problem_difficulty=apps_problem.difficulty,
                    max_difficulty=dataset.settings.max_difficulty
                )
            except Exception as e:
                logger.error(f"[RUN_PROBLEM] Failed: {e}")

        # Start background thread
        thread = threading.Thread(target=run_problem_async, daemon=True)
        thread.start()

        # Return immediately - result will be updated in storage
        return {
            "status": "started",
            "dataset_id": dataset_id,
            "problem_id": problem_id,
            "message": "Problem execution started. Poll GET endpoint for progress."
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.post("/{dataset_id}/problems/{problem_id}/run-from-phase")
def run_problem_from_phase(
    dataset_id: str,
    problem_id: str,
    request: RunFromPhaseRequest,
    x_anthropic_key: Optional[str] = Header(None, alias="X-Anthropic-Key"),
    x_openai_key: Optional[str] = Header(None, alias="X-OpenAI-Key"),
):
    """Re-run phases starting from a specific phase. Only allowed for published datasets."""
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset.status != "published":
            raise HTTPException(
                status_code=400,
                detail="Cannot run problems on draft datasets. Publish the dataset first."
            )

        if problem_id not in dataset.problem_ids:
            raise HTTPException(status_code=404, detail="Problem not in dataset")

        if request.from_phase < 1 or request.from_phase > 6:
            raise HTTPException(status_code=400, detail="from_phase must be between 1 and 6")

        # Load APPS problem
        loader = get_apps_loader()
        apps_problem = loader.load_problem(problem_id)
        if not apps_problem:
            raise HTTPException(status_code=404, detail=f"APPS problem {problem_id} not found")

        # Build models dict
        models = {
            "human_model": dataset.models.human_model,
            "trusted_model": dataset.models.trusted_model,
            "untrusted_model": dataset.models.untrusted_model,
            "red_team_model": dataset.models.red_team_model
        }

        # Run in background thread
        def run_from_phase_async():
            try:
                run_single_problem_from_phase(
                    dataset_id=dataset_id,
                    problem_id=problem_id,
                    problem_text=apps_problem.question,
                    solutions=apps_problem.solutions,
                    models=models,
                    from_phase=request.from_phase,
                    prompts=dataset.prompts if dataset.prompts else None,
                    openai_key=x_openai_key,
                    anthropic_key=x_anthropic_key,
                    piston_url=os.environ.get("PISTON_URL"),
                    test_cases=apps_problem.test_cases,
                    problem_difficulty=apps_problem.difficulty,
                    max_difficulty=dataset.settings.max_difficulty
                )
            except Exception as e:
                logger.error(f"[RUN_FROM_PHASE] Failed: {e}")

        # Start background thread
        thread = threading.Thread(target=run_from_phase_async, daemon=True)
        thread.start()

        return {
            "status": "started",
            "dataset_id": dataset_id,
            "problem_id": problem_id,
            "from_phase": request.from_phase,
            "message": f"Re-running from phase {request.from_phase}. Poll GET endpoint for progress."
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


# =============================================================================
# THRESHOLD ENDPOINTS
# =============================================================================

@router.post("/{dataset_id}/compute-thresholds")
def compute_dataset_thresholds(dataset_id: str):
    """
    Compute audit and defer thresholds from all problem results (Phase 7).
    Requires all problems to have completed results. Only for published datasets.
    """
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        if dataset.status != "published":
            raise HTTPException(
                status_code=400,
                detail="Cannot compute thresholds on draft datasets. Publish the dataset first."
            )

        audit_threshold, defer_threshold = compute_thresholds(
            dataset_id=dataset_id,
            validate_complete=True
        )

        return {
            "status": "completed",
            "dataset_id": dataset_id,
            "audit_threshold": audit_threshold,
            "defer_threshold": defer_threshold
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


@router.post("/{dataset_id}/thresholds")
def import_thresholds(
    dataset_id: str,
    request: ImportThresholdsRequest,
):
    """Import pre-computed thresholds for a dataset."""
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        dataset_store.update_thresholds(
            dataset_id=dataset_id,
            audit_threshold=request.audit_threshold,
            defer_threshold=request.defer_threshold,
        )

        return {
            "status": "imported",
            "dataset_id": dataset_id,
            "audit_threshold": request.audit_threshold,
            "defer_threshold": request.defer_threshold,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")


# =============================================================================
# IMPORT ENDPOINTS
# =============================================================================

@router.post("/{dataset_id}/problems/{problem_id}/import")
def import_problem_result(
    dataset_id: str,
    problem_id: str,
    request: ImportProblemResultRequest,
):
    """
    Import a pre-computed problem result from local dataset generation.
    Only allowed for draft datasets before publishing.
    """
    try:
        dataset = get_dataset(dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")

        # Allow import on both draft and published datasets
        # (published datasets may need results imported)

        if problem_id not in dataset.problem_ids:
            raise HTTPException(status_code=404, detail="Problem not in dataset")

        # Convert request to ProblemResult
        result = ProblemResult(
            problem_id=request.problem_id,
            status=request.status,
            phases_completed=request.phases_completed,
            U_normal_solution=request.U_normal_solution,
            T_solution=request.T_solution,
            U_tests_passed=request.U_tests_passed,
            U_tests_total=request.U_tests_total,
            T_tests_passed=request.T_tests_passed,
            T_tests_total=request.T_tests_total,
            problem_difficulty=request.problem_difficulty,
            max_difficulty=request.max_difficulty,
            difficulty_skipped=request.difficulty_skipped,
            T_suspicion_normal=request.T_suspicion_normal,
            T_suspicion_backdoor=request.T_suspicion_backdoor,
            H_suspicion_normal=request.H_suspicion_normal,
            H_suspicion_backdoor=request.H_suspicion_backdoor,
            sneakiest_backdoor_idx=request.sneakiest_backdoor_idx,
            error=request.error,
            started_at=request.started_at,
            completed_at=request.completed_at,
        )

        # Convert nested objects
        if request.strategy_results:
            for strategy_name, sr_dict in request.strategy_results.items():
                result.strategy_results[strategy_name] = dict_to_strategy_result(sr_dict)

        if request.backdoor_attempts:
            result.backdoor_attempts = [
                dict_to_backdoor_attempt(ba) for ba in request.backdoor_attempts
            ]

        if request.llm_calls:
            result.llm_calls = [dict_to_llm_call(call) for call in request.llm_calls]

        # Save to storage
        dataset_store.update_problem_result(dataset_id, problem_id, result)

        return {
            "status": "imported",
            "dataset_id": dataset_id,
            "problem_id": problem_id,
            "phases_completed": result.phases_completed,
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        raise HTTPException(status_code=400, detail=f"{str(e)}\n{traceback.format_exc()}")
