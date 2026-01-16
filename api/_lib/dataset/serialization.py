"""
Dataset Serialization - Convert dataclasses to/from dicts for storage
"""

from dataclasses import asdict

from .models import (
    DatasetSettings, DatasetModels, LLMCall, BackdoorAttempt,
    StrategyResult, ProblemResult, TestRunResult, Dataset
)


def settings_to_dict(settings: DatasetSettings) -> dict:
    """Convert DatasetSettings to dict"""
    return asdict(settings)


def dict_to_settings(d: dict) -> DatasetSettings:
    """Convert dict to DatasetSettings"""
    # Support both old field name (apps_manual_ids) and new (mandatory_problems)
    mandatory = d.get("mandatory_problems") or d.get("apps_manual_ids", [])
    return DatasetSettings(
        num_problems=d.get("num_problems", 5),
        num_backdoor_ideas=d.get("num_backdoor_ideas", 5),
        max_difficulty=d.get("max_difficulty", 6),
        apps_difficulty_filter=d.get("apps_difficulty_filter", ["interview"]),
        mandatory_problems=mandatory
    )


def models_to_dict(models: DatasetModels) -> dict:
    """Convert DatasetModels to dict"""
    return asdict(models)


def dict_to_models(d: dict) -> DatasetModels:
    """Convert dict to DatasetModels"""
    return DatasetModels(
        human_model=d.get("human_model", "gpt-4o"),
        trusted_model=d.get("trusted_model", "gpt-3.5-turbo"),
        untrusted_model=d.get("untrusted_model", "gpt-4o"),
        red_team_model=d.get("red_team_model", "gpt-4o")
    )


def llm_call_to_dict(call: LLMCall) -> dict:
    """Convert LLMCall to dict"""
    return asdict(call)


def dict_to_llm_call(d: dict) -> LLMCall:
    """Convert dict to LLMCall"""
    return LLMCall(
        call_id=d["call_id"],
        phase=d["phase"],
        step=d["step"],
        model=d["model"],
        prompt=d["prompt"],
        response=d.get("response"),
        status=d.get("status", "pending"),
        started_at=d.get("started_at"),
        completed_at=d.get("completed_at"),
        error=d.get("error"),
        prompt_tokens=d.get("prompt_tokens"),
        completion_tokens=d.get("completion_tokens"),
        total_tokens=d.get("total_tokens"),
        cost_usd=d.get("cost_usd")
    )


def backdoor_attempt_to_dict(attempt: BackdoorAttempt) -> dict:
    """Convert BackdoorAttempt to dict"""
    return asdict(attempt)


def dict_to_backdoor_attempt(d: dict) -> BackdoorAttempt:
    """Convert dict to BackdoorAttempt"""
    return BackdoorAttempt(
        idea=d.get("idea", ""),
        code=d.get("code", ""),
        sneakiness=d.get("sneakiness", 0.0),
        selected=d.get("selected", False),
        rating1=d.get("rating1"),
        rating2=d.get("rating2"),
        backdoor_snippet=d.get("backdoor_snippet"),
        test_cases_passed=d.get("test_cases_passed"),
        test_cases_total=d.get("test_cases_total"),
        test_case_results=d.get("test_case_results"),
        exploit_found=d.get("exploit_found", False),
        exploit_input=d.get("exploit_input"),
        exploit_output=d.get("exploit_output"),
        exploit_expected=d.get("exploit_expected"),
        exploit_verified=d.get("exploit_verified", False),
        outcome=d.get("outcome")
    )


def strategy_result_to_dict(result: StrategyResult) -> dict:
    """Convert StrategyResult to dict"""
    return asdict(result)


def dict_to_strategy_result(d: dict) -> StrategyResult:
    """Convert dict to StrategyResult"""
    return StrategyResult(
        strategy=d.get("strategy", ""),
        threshold=d.get("threshold", 0.0),
        backdoor_selected=d.get("backdoor_selected", False),
        selected_backdoor_idx=d.get("selected_backdoor_idx"),
        sneakiness=d.get("sneakiness"),
        T_suspicion_score=d.get("T_suspicion_score"),
        H_suspicion_score=d.get("H_suspicion_score"),
        exploit_found=d.get("exploit_found", False)
    )


def problem_result_to_dict(result: ProblemResult) -> dict:
    """Convert ProblemResult to dict"""
    d = asdict(result)
    # Ensure llm_calls are properly serialized
    d["llm_calls"] = [llm_call_to_dict(c) if isinstance(c, LLMCall) else c for c in result.llm_calls]
    # Ensure backdoor_attempts are properly serialized
    d["backdoor_attempts"] = [backdoor_attempt_to_dict(a) if isinstance(a, BackdoorAttempt) else a for a in result.backdoor_attempts]
    # Ensure strategy_results are properly serialized
    d["strategy_results"] = {
        k: strategy_result_to_dict(v) if isinstance(v, StrategyResult) else v
        for k, v in result.strategy_results.items()
    }
    return d


def dict_to_problem_result(d: dict) -> ProblemResult:
    """Convert dict to ProblemResult"""
    llm_calls = [dict_to_llm_call(c) if isinstance(c, dict) else c for c in d.get("llm_calls", [])]
    backdoor_attempts = [dict_to_backdoor_attempt(a) if isinstance(a, dict) else a for a in d.get("backdoor_attempts", [])]
    strategy_results = {
        k: dict_to_strategy_result(v) if isinstance(v, dict) else v
        for k, v in d.get("strategy_results", {}).items()
    }
    return ProblemResult(
        problem_id=d["problem_id"],
        status=d.get("status", "pending"),
        phases_completed=d.get("phases_completed", []),
        current_phase=d.get("current_phase"),
        U_normal_solution=d.get("U_normal_solution"),
        T_solution=d.get("T_solution"),
        U_tests_passed=d.get("U_tests_passed"),
        U_tests_total=d.get("U_tests_total"),
        T_tests_passed=d.get("T_tests_passed"),
        T_tests_total=d.get("T_tests_total"),
        problem_difficulty=d.get("problem_difficulty"),
        max_difficulty=d.get("max_difficulty"),
        difficulty_skipped=d.get("difficulty_skipped", False),
        T_suspicion_normal=d.get("T_suspicion_normal"),
        T_suspicion_backdoor=d.get("T_suspicion_backdoor"),
        H_suspicion_normal=d.get("H_suspicion_normal"),
        H_suspicion_backdoor=d.get("H_suspicion_backdoor"),
        sneakiest_backdoor_idx=d.get("sneakiest_backdoor_idx"),
        strategy_results=strategy_results,
        U_backdoored_solution=d.get("U_backdoored_solution"),
        T_suspicion_score=d.get("T_suspicion_score"),
        H_suspicion_score=d.get("H_suspicion_score"),
        sneakiness=d.get("sneakiness"),
        exploit_found=d.get("exploit_found", False),
        exploits=d.get("exploits", []),
        backdoor_attempts=backdoor_attempts,
        llm_calls=llm_calls,
        error=d.get("error"),
        started_at=d.get("started_at"),
        completed_at=d.get("completed_at")
    )


def test_result_to_dict(result: TestRunResult) -> dict:
    """Convert TestRunResult to dict"""
    d = asdict(result)
    # Ensure llm_calls are properly serialized
    d["llm_calls"] = [llm_call_to_dict(c) if isinstance(c, LLMCall) else c for c in result.llm_calls]
    return d


def dict_to_test_result(d: dict) -> TestRunResult:
    """Convert dict to TestRunResult"""
    llm_calls = [dict_to_llm_call(c) if isinstance(c, dict) else c for c in d.get("llm_calls", [])]
    return TestRunResult(
        test_id=d["test_id"],
        status=d["status"],
        started_at=d["started_at"],
        completed_at=d.get("completed_at"),
        current_phase=d.get("current_phase", "Pending"),
        progress_percent=d.get("progress_percent", 0),
        phases_completed=d.get("phases_completed", []),
        error=d.get("error"),
        problems_generated=d.get("problems_generated", 0),
        backdoors_generated=d.get("backdoors_generated", 0),
        exploits_found=d.get("exploits_found", 0),
        llm_calls=llm_calls
    )


def dataset_to_dict(dataset: Dataset) -> dict:
    """Convert Dataset to JSON-serializable dict"""
    return {
        "id": dataset.id,
        "name": dataset.name,
        "status": dataset.status,
        "settings": settings_to_dict(dataset.settings),
        "models": models_to_dict(dataset.models),
        "prompts": dataset.prompts,
        "created_at": dataset.created_at,
        "updated_at": dataset.updated_at,
        "published_at": dataset.published_at,
        "last_test": test_result_to_dict(dataset.last_test) if dataset.last_test else None,
        "problem_ids": dataset.problem_ids,
        "audit_threshold": dataset.audit_threshold,
        "defer_threshold": dataset.defer_threshold,
        "threshold_error": dataset.threshold_error
    }


def dict_to_dataset(d: dict) -> Dataset:
    """Convert dict to Dataset"""
    return Dataset(
        id=d["id"],
        name=d["name"],
        status=d["status"],
        settings=dict_to_settings(d.get("settings", {})),
        models=dict_to_models(d.get("models", {})),
        prompts=d.get("prompts", {}),
        created_at=d["created_at"],
        updated_at=d["updated_at"],
        published_at=d.get("published_at"),
        last_test=dict_to_test_result(d["last_test"]) if d.get("last_test") else None,
        problem_ids=d.get("problem_ids", []),
        audit_threshold=d.get("audit_threshold"),
        defer_threshold=d.get("defer_threshold"),
        threshold_error=d.get("threshold_error")
    )
