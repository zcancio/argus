"""
Dataset Convenience Functions - Wrappers around DatasetStore methods
"""

from typing import Dict, List, Optional

from .models import Dataset
from .serialization import dict_to_settings, dict_to_models
from .store import dataset_store


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
