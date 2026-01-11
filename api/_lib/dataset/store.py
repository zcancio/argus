"""
Dataset Store - Redis/memory storage for datasets and problem results
"""

from typing import Dict, List, Optional
from datetime import datetime
import uuid
import json
import random

from api._lib.storage import get_redis_client

from .models import (
    Dataset, DatasetSettings, DatasetModels,
    ProblemResult, TestRunResult
)
from .serialization import (
    dataset_to_dict, dict_to_dataset,
    problem_result_to_dict, dict_to_problem_result,
    test_result_to_dict, dict_to_test_result
)

# TTL Configuration (in seconds)
TTL_DRAFT = 30 * 24 * 60 * 60      # 30 days for draft datasets
TTL_PUBLISHED = 365 * 24 * 60 * 60  # 1 year for published datasets


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

        On publish, selects problems in this order:
        1. Mandatory problems (in order, if valid)
        2. Random problems to fill remaining slots up to num_problems
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

        # Build set of valid problem IDs for quick lookup
        valid_ids = {p["problem_id"] for p in all_problems}

        # Start with mandatory problems (filter to valid ones, preserve order)
        mandatory = dataset.settings.mandatory_problems or []
        selected_ids = [pid for pid in mandatory if pid in valid_ids]

        # Determine how many problems we need total
        num_to_select = dataset.settings.num_problems

        if len(selected_ids) >= num_to_select:
            # More mandatory than needed - truncate to first N
            selected_ids = selected_ids[:num_to_select]
        else:
            # Fill remaining slots with random selection
            remaining = num_to_select - len(selected_ids)
            # Exclude already-selected mandatory problems from pool
            selected_set = set(selected_ids)
            available = [p for p in all_problems if p["problem_id"] not in selected_set]
            # Randomly select to fill remaining slots
            random_picks = random.sample(available, min(remaining, len(available)))
            selected_ids.extend([p["problem_id"] for p in random_picks])

        dataset.problem_ids = selected_ids

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
                max_difficulty=source.settings.max_difficulty,
                mandatory_problems=list(source.settings.mandatory_problems)
            ),
            models=DatasetModels(
                human_model=source.models.human_model,
                trusted_model=source.models.trusted_model,
                untrusted_model=source.models.untrusted_model,
                red_team_model=source.models.red_team_model
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


# Global store instance
dataset_store = DatasetStore()
