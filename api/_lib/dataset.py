"""
Dataset Module for ARGUS Pre-computation

Datasets bundle pre-computation settings, prompts, and model roles.
Lifecycle: draft (editable, testable) -> published (locked, immutable)
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
import json
import random

from api._lib.storage import get_redis_client

# TTL Configuration (in seconds)
TTL_DRAFT = 30 * 24 * 60 * 60      # 30 days for draft datasets
TTL_PUBLISHED = 365 * 24 * 60 * 60  # 1 year for published datasets


@dataclass
class DatasetSettings:
    """Pre-computation settings"""
    num_problems: int = 5
    num_backdoor_ideas: int = 3
    max_difficulty: int = 7
    # APPS filtering
    apps_difficulty_filter: List[str] = field(default_factory=lambda: ["interview"])
    apps_manual_ids: List[str] = field(default_factory=list)


@dataclass
class DatasetModels:
    """Model role assignments"""
    human_model: str = "gpt-4o"
    trusted_model: str = "gpt-4o"
    untrusted_model: str = "gpt-4o"


@dataclass
class LLMCall:
    """Record of a single LLM API call"""
    call_id: str
    phase: int
    step: str  # e.g., "generate_u_solution", "rate_sneakiness"
    model: str
    prompt: str
    response: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


@dataclass
class BackdoorAttempt:
    """A single backdoor attempt with its sneakiness score"""
    idea: str
    code: str
    sneakiness: float
    selected: bool = False


@dataclass
class ProblemResult:
    """Stores per-problem execution results"""
    problem_id: str
    status: str = "pending"  # "pending" | "running" | "completed" | "failed"
    phases_completed: List[int] = field(default_factory=list)
    current_phase: Optional[int] = None

    # Phase outputs (stored after completion)
    U_normal_solution: Optional[str] = None
    T_solution: Optional[str] = None
    U_backdoored_solution: Optional[str] = None
    T_suspicion_score: Optional[float] = None
    H_suspicion_score: Optional[float] = None
    sneakiness: Optional[float] = None
    exploit_found: bool = False
    exploits: List[str] = field(default_factory=list)

    # All backdoor attempts (even ones not selected)
    backdoor_attempts: List[BackdoorAttempt] = field(default_factory=list)

    # Full LLM call logs
    llm_calls: List[LLMCall] = field(default_factory=list)

    error: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


@dataclass
class TestRunResult:
    """Result of a test run"""
    test_id: str
    status: str  # running, completed, failed
    started_at: str
    completed_at: Optional[str] = None
    current_phase: str = "Pending"
    progress_percent: int = 0
    phases_completed: List[int] = field(default_factory=list)
    error: Optional[str] = None
    # Summary metrics on completion
    problems_generated: int = 0
    backdoors_generated: int = 0
    exploits_found: int = 0
    # LLM call tracking
    llm_calls: List[LLMCall] = field(default_factory=list)


@dataclass
class Dataset:
    """
    A dataset configuration for pre-computation.

    Lifecycle:
    - draft: Can be edited, tested, and deleted
    - published: Locked permanently, used for actual runs
    """
    id: str
    name: str
    status: str  # "draft" | "published"
    settings: DatasetSettings
    models: DatasetModels
    prompts: Dict[str, str]  # Custom prompts (key -> value)
    created_at: str
    updated_at: str
    published_at: Optional[str] = None
    last_test: Optional[TestRunResult] = None
    # APPS problem tracking
    problem_ids: List[str] = field(default_factory=list)  # Selected APPS problem IDs
    # Aggregate results (Phase 7)
    audit_threshold: Optional[float] = None
    defer_threshold: Optional[float] = None
    threshold_error: Optional[str] = None


# =============================================================================
# SERIALIZATION HELPERS
# =============================================================================

def settings_to_dict(settings: DatasetSettings) -> dict:
    """Convert DatasetSettings to dict"""
    return asdict(settings)


def dict_to_settings(d: dict) -> DatasetSettings:
    """Convert dict to DatasetSettings"""
    return DatasetSettings(
        num_problems=d.get("num_problems", 5),
        num_backdoor_ideas=d.get("num_backdoor_ideas", 3),
        max_difficulty=d.get("max_difficulty", 7),
        apps_difficulty_filter=d.get("apps_difficulty_filter", ["interview"]),
        apps_manual_ids=d.get("apps_manual_ids", [])
    )


def models_to_dict(models: DatasetModels) -> dict:
    """Convert DatasetModels to dict"""
    return asdict(models)


def dict_to_models(d: dict) -> DatasetModels:
    """Convert dict to DatasetModels"""
    return DatasetModels(
        human_model=d.get("human_model", "gpt-4o"),
        trusted_model=d.get("trusted_model", "gpt-4o"),
        untrusted_model=d.get("untrusted_model", "gpt-4o")
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
        error=d.get("error")
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
        selected=d.get("selected", False)
    )


def problem_result_to_dict(result: ProblemResult) -> dict:
    """Convert ProblemResult to dict"""
    d = asdict(result)
    # Ensure llm_calls are properly serialized
    d["llm_calls"] = [llm_call_to_dict(c) if isinstance(c, LLMCall) else c for c in result.llm_calls]
    # Ensure backdoor_attempts are properly serialized
    d["backdoor_attempts"] = [backdoor_attempt_to_dict(a) if isinstance(a, BackdoorAttempt) else a for a in result.backdoor_attempts]
    return d


def dict_to_problem_result(d: dict) -> ProblemResult:
    """Convert dict to ProblemResult"""
    llm_calls = [dict_to_llm_call(c) if isinstance(c, dict) else c for c in d.get("llm_calls", [])]
    backdoor_attempts = [dict_to_backdoor_attempt(a) if isinstance(a, dict) else a for a in d.get("backdoor_attempts", [])]
    return ProblemResult(
        problem_id=d["problem_id"],
        status=d.get("status", "pending"),
        phases_completed=d.get("phases_completed", []),
        current_phase=d.get("current_phase"),
        U_normal_solution=d.get("U_normal_solution"),
        T_solution=d.get("T_solution"),
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


# =============================================================================
# DATASET STORE
# =============================================================================

class DatasetStore:
    """
    Store datasets in Redis (Vercel KV).
    Falls back to in-memory storage if KV is not configured.
    """

    KEY_DATASET = "dataset:{id}"
    KEY_INDEX = "dataset:index"
    KEY_TEST = "dataset:{id}:test"
    KEY_PROBLEM = "dataset:{id}:problem:{problem_id}"

    def __init__(self):
        self.redis = get_redis_client()
        self._memory_store: Dict[str, Dataset] = {}
        self._problem_results: Dict[str, Dict[str, ProblemResult]] = {}  # dataset_id -> {problem_id -> result}

    @property
    def is_persistent(self) -> bool:
        return self.redis is not None

    def _get_key(self, template: str, **kwargs) -> str:
        """Get Redis key with substitutions"""
        return template.format(**kwargs)

    def create(self, name: str, settings: Optional[DatasetSettings] = None,
               models: Optional[DatasetModels] = None,
               prompts: Optional[Dict[str, str]] = None) -> Dataset:
        """Create a new dataset"""
        dataset_id = f"dataset_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        dataset = Dataset(
            id=dataset_id,
            name=name,
            status="draft",
            settings=settings or DatasetSettings(),
            models=models or DatasetModels(),
            prompts=prompts or {},
            created_at=now,
            updated_at=now
        )

        self._save(dataset)
        return dataset

    def _save(self, dataset: Dataset):
        """Save dataset to storage"""
        dataset.updated_at = datetime.utcnow().isoformat()

        if self.redis:
            try:
                key = self._get_key(self.KEY_DATASET, id=dataset.id)
                ttl = TTL_PUBLISHED if dataset.status == "published" else TTL_DRAFT

                self.redis.setex(
                    key,
                    ttl,
                    json.dumps(dataset_to_dict(dataset))
                )

                # Add to index
                self.redis.zadd(
                    self.KEY_INDEX,
                    {dataset.id: datetime.utcnow().timestamp()}
                )
            except Exception as e:
                print(f"Redis save failed: {e}")
        else:
            self._memory_store[dataset.id] = dataset

    def get(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID"""
        if self.redis:
            try:
                key = self._get_key(self.KEY_DATASET, id=dataset_id)
                data = self.redis.get(key)
                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    return dict_to_dataset(json.loads(data))
                return None
            except Exception as e:
                print(f"Redis get failed: {e}")
                return None
        else:
            return self._memory_store.get(dataset_id)

    def update(self, dataset_id: str,
               name: Optional[str] = None,
               settings: Optional[DatasetSettings] = None,
               models: Optional[DatasetModels] = None,
               prompts: Optional[Dict[str, str]] = None) -> Optional[Dataset]:
        """Update a draft dataset"""
        dataset = self.get(dataset_id)
        if not dataset:
            return None

        if dataset.status != "draft":
            raise ValueError("Cannot update a published dataset")

        if name is not None:
            dataset.name = name
        if settings is not None:
            dataset.settings = settings
        if models is not None:
            dataset.models = models
        if prompts is not None:
            dataset.prompts = prompts

        self._save(dataset)
        return dataset

    def delete(self, dataset_id: str) -> bool:
        """Delete a dataset (both draft and published)"""
        dataset = self.get(dataset_id)
        if not dataset:
            return False

        if self.redis:
            try:
                key = self._get_key(self.KEY_DATASET, id=dataset_id)
                test_key = self._get_key(self.KEY_TEST, id=dataset_id)

                self.redis.delete(key)
                self.redis.delete(test_key)
                self.redis.zrem(self.KEY_INDEX, dataset_id)
                return True
            except Exception as e:
                print(f"Redis delete failed: {e}")
                return False
        else:
            if dataset_id in self._memory_store:
                del self._memory_store[dataset_id]
                return True
            return False

    def list_all(self, limit: int = 50) -> List[Dataset]:
        """List all datasets"""
        if self.redis:
            try:
                # Get dataset IDs from sorted set (most recent first)
                dataset_ids = self.redis.zrevrange(self.KEY_INDEX, 0, limit - 1)

                results = []
                for did in dataset_ids:
                    if isinstance(did, bytes):
                        did = did.decode('utf-8')
                    dataset = self.get(did)
                    if dataset:
                        results.append(dataset)
                return results
            except Exception as e:
                print(f"Redis list failed: {e}")
                return []
        else:
            items = list(self._memory_store.values())
            return sorted(items, key=lambda x: x.updated_at, reverse=True)[:limit]

    def publish(self, dataset_id: str) -> Optional[Dataset]:
        """
        Publish a dataset (lock it permanently).

        On publish, randomly selects problems from the filtered APPS list
        up to the num_problems setting.
        """
        dataset = self.get(dataset_id)
        if not dataset:
            return None

        if dataset.status != "draft":
            raise ValueError("Dataset is already published")

        # Import here to avoid circular imports
        from api._lib.apps import get_apps_loader

        # Get filtered APPS problems
        loader = get_apps_loader()
        all_problems = loader.list_problems(limit=None)  # Get all filtered problems

        if not all_problems:
            raise ValueError("No valid APPS problems available. Run scripts/filter_apps.py first.")

        # Randomly select up to num_problems
        num_to_select = min(dataset.settings.num_problems, len(all_problems))
        selected = random.sample(all_problems, num_to_select)
        dataset.problem_ids = [p["problem_id"] for p in selected]

        dataset.status = "published"
        dataset.published_at = datetime.utcnow().isoformat()

        self._save(dataset)
        return dataset

    def duplicate(self, dataset_id: str, new_name: Optional[str] = None) -> Optional[Dataset]:
        """Create a draft copy of any dataset"""
        source = self.get(dataset_id)
        if not source:
            return None

        name = new_name or f"{source.name} (copy)"

        return self.create(
            name=name,
            settings=DatasetSettings(
                num_problems=source.settings.num_problems,
                num_backdoor_ideas=source.settings.num_backdoor_ideas,
                max_difficulty=source.settings.max_difficulty
            ),
            models=DatasetModels(
                human_model=source.models.human_model,
                trusted_model=source.models.trusted_model,
                untrusted_model=source.models.untrusted_model
            ),
            prompts=dict(source.prompts)
        )

    # =========================================================================
    # TEST RUN MANAGEMENT
    # =========================================================================

    def start_test(self, dataset_id: str) -> Optional[TestRunResult]:
        """Start a test run for a dataset"""
        dataset = self.get(dataset_id)
        if not dataset:
            return None

        if dataset.status != "draft":
            raise ValueError("Can only test draft datasets")

        test_id = f"test_{uuid.uuid4().hex[:12]}"
        now = datetime.utcnow().isoformat()

        test_result = TestRunResult(
            test_id=test_id,
            status="running",
            started_at=now,
            current_phase="Phase 1: Generating Baseline Solutions"
        )

        # Save test result to dataset
        dataset.last_test = test_result
        self._save(dataset)

        # Also save test state separately for polling
        if self.redis:
            test_key = self._get_key(self.KEY_TEST, id=dataset_id)
            self.redis.setex(
                test_key,
                TTL_DRAFT,
                json.dumps(test_result_to_dict(test_result))
            )

        return test_result

    def update_test(self, dataset_id: str, test_result: TestRunResult):
        """Update test run progress"""
        dataset = self.get(dataset_id)
        if not dataset:
            return

        dataset.last_test = test_result
        self._save(dataset)

        # Update separate test state for polling
        if self.redis:
            test_key = self._get_key(self.KEY_TEST, id=dataset_id)
            self.redis.setex(
                test_key,
                TTL_DRAFT,
                json.dumps(test_result_to_dict(test_result))
            )

    def get_test_status(self, dataset_id: str) -> Optional[TestRunResult]:
        """Get current test run status"""
        if self.redis:
            try:
                test_key = self._get_key(self.KEY_TEST, id=dataset_id)
                data = self.redis.get(test_key)
                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    return dict_to_test_result(json.loads(data))
            except Exception as e:
                print(f"Redis get test failed: {e}")

        # Fallback to dataset's last_test
        dataset = self.get(dataset_id)
        return dataset.last_test if dataset else None

    # =========================================================================
    # PROBLEM RESULT MANAGEMENT
    # =========================================================================

    def add_problem(self, dataset_id: str, problem_id: str) -> Optional[Dataset]:
        """Add a problem to a dataset"""
        dataset = self.get(dataset_id)
        if not dataset:
            return None

        if dataset.status != "draft":
            raise ValueError("Cannot modify a published dataset")

        if problem_id not in dataset.problem_ids:
            dataset.problem_ids.append(problem_id)
            self._save(dataset)

        return dataset

    def remove_problem(self, dataset_id: str, problem_id: str) -> Optional[Dataset]:
        """Remove a problem from a dataset"""
        dataset = self.get(dataset_id)
        if not dataset:
            return None

        if dataset.status != "draft":
            raise ValueError("Cannot modify a published dataset")

        if problem_id in dataset.problem_ids:
            dataset.problem_ids.remove(problem_id)
            # Also delete the problem result if it exists
            self._delete_problem_result(dataset_id, problem_id)
            self._save(dataset)

        return dataset

    def set_problems(self, dataset_id: str, problem_ids: List[str]) -> Optional[Dataset]:
        """Set the list of problems for a dataset (replaces existing)"""
        dataset = self.get(dataset_id)
        if not dataset:
            return None

        if dataset.status != "draft":
            raise ValueError("Cannot modify a published dataset")

        # Delete results for problems being removed
        removed = set(dataset.problem_ids) - set(problem_ids)
        for pid in removed:
            self._delete_problem_result(dataset_id, pid)

        dataset.problem_ids = problem_ids
        self._save(dataset)

        return dataset

    def get_problem_result(self, dataset_id: str, problem_id: str) -> Optional[ProblemResult]:
        """Get the result for a specific problem"""
        if self.redis:
            try:
                key = self._get_key(self.KEY_PROBLEM, id=dataset_id, problem_id=problem_id)
                data = self.redis.get(key)
                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    return dict_to_problem_result(json.loads(data))
                return None
            except Exception as e:
                print(f"Redis get problem result failed: {e}")
                return None
        else:
            if dataset_id in self._problem_results:
                return self._problem_results[dataset_id].get(problem_id)
            return None

    def update_problem_result(self, dataset_id: str, problem_id: str, result: ProblemResult):
        """Update or create a problem result"""
        if self.redis:
            try:
                # Use published TTL since problems only run on published datasets
                key = self._get_key(self.KEY_PROBLEM, id=dataset_id, problem_id=problem_id)
                self.redis.setex(
                    key,
                    TTL_PUBLISHED,
                    json.dumps(problem_result_to_dict(result))
                )
            except Exception as e:
                print(f"Redis update problem result failed: {e}")
        else:
            if dataset_id not in self._problem_results:
                self._problem_results[dataset_id] = {}
            self._problem_results[dataset_id][problem_id] = result

    def _delete_problem_result(self, dataset_id: str, problem_id: str):
        """Delete a problem result"""
        if self.redis:
            try:
                key = self._get_key(self.KEY_PROBLEM, id=dataset_id, problem_id=problem_id)
                self.redis.delete(key)
            except Exception as e:
                print(f"Redis delete problem result failed: {e}")
        else:
            if dataset_id in self._problem_results:
                self._problem_results[dataset_id].pop(problem_id, None)

    def get_all_problem_results(self, dataset_id: str) -> Dict[str, ProblemResult]:
        """Get all problem results for a dataset"""
        dataset = self.get(dataset_id)
        if not dataset:
            return {}

        results = {}
        for problem_id in dataset.problem_ids:
            result = self.get_problem_result(dataset_id, problem_id)
            if result:
                results[problem_id] = result

        return results

    def update_thresholds(
        self,
        dataset_id: str,
        audit_threshold: Optional[float] = None,
        defer_threshold: Optional[float] = None,
        error: Optional[str] = None
    ) -> Optional[Dataset]:
        """Update the computed thresholds for a dataset"""
        dataset = self.get(dataset_id)
        if not dataset:
            return None

        dataset.audit_threshold = audit_threshold
        dataset.defer_threshold = defer_threshold
        dataset.threshold_error = error

        self._save(dataset)
        return dataset


# =============================================================================
# GLOBAL STORE INSTANCE
# =============================================================================

dataset_store = DatasetStore()


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_dataset(name: str, settings: Optional[Dict] = None,
                   models: Optional[Dict] = None,
                   prompts: Optional[Dict[str, str]] = None) -> Dataset:
    """Create a new dataset"""
    ds_settings = dict_to_settings(settings) if settings else None
    ds_models = dict_to_models(models) if models else None
    return dataset_store.create(name, ds_settings, ds_models, prompts)


def get_dataset(dataset_id: str) -> Optional[Dataset]:
    """Get dataset by ID"""
    return dataset_store.get(dataset_id)


def update_dataset(dataset_id: str, name: Optional[str] = None,
                   settings: Optional[Dict] = None,
                   models: Optional[Dict] = None,
                   prompts: Optional[Dict[str, str]] = None) -> Optional[Dataset]:
    """Update a draft dataset"""
    ds_settings = dict_to_settings(settings) if settings else None
    ds_models = dict_to_models(models) if models else None
    return dataset_store.update(dataset_id, name, ds_settings, ds_models, prompts)


def delete_dataset(dataset_id: str) -> bool:
    """Delete a draft dataset"""
    return dataset_store.delete(dataset_id)


def list_datasets(limit: int = 50) -> List[Dataset]:
    """List all datasets"""
    return dataset_store.list_all(limit)


def publish_dataset(dataset_id: str) -> Optional[Dataset]:
    """Publish a dataset"""
    return dataset_store.publish(dataset_id)


def duplicate_dataset(dataset_id: str, new_name: Optional[str] = None) -> Optional[Dataset]:
    """Duplicate a dataset"""
    return dataset_store.duplicate(dataset_id, new_name)
