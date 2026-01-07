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


@dataclass
class DatasetModels:
    """Model role assignments"""
    human_model: str = "gpt-4o"
    trusted_model: str = "gpt-4o"
    untrusted_model: str = "gpt-4o"


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
        max_difficulty=d.get("max_difficulty", 7)
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


def test_result_to_dict(result: TestRunResult) -> dict:
    """Convert TestRunResult to dict"""
    return asdict(result)


def dict_to_test_result(d: dict) -> TestRunResult:
    """Convert dict to TestRunResult"""
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
        exploits_found=d.get("exploits_found", 0)
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
        "last_test": test_result_to_dict(dataset.last_test) if dataset.last_test else None
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
        last_test=dict_to_test_result(d["last_test"]) if d.get("last_test") else None
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

    def __init__(self):
        self.redis = get_redis_client()
        self._memory_store: Dict[str, Dataset] = {}

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
        """Delete a draft dataset"""
        dataset = self.get(dataset_id)
        if not dataset:
            return False

        if dataset.status != "draft":
            raise ValueError("Cannot delete a published dataset")

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
        """Publish a dataset (lock it permanently)"""
        dataset = self.get(dataset_id)
        if not dataset:
            return None

        if dataset.status != "draft":
            raise ValueError("Dataset is already published")

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
