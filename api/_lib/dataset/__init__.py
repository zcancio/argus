"""
Dataset Package for ARGUS Pre-computation

Re-exports all public symbols for backwards compatibility.
"""

# Models
from .models import (
    DatasetSettings,
    DatasetModels,
    LLMCall,
    BackdoorAttempt,
    ATTACK_STRATEGIES,
    StrategyResult,
    ProblemResult,
    TestRunResult,
    Dataset,
)

# Serialization
from .serialization import (
    settings_to_dict,
    dict_to_settings,
    models_to_dict,
    dict_to_models,
    llm_call_to_dict,
    dict_to_llm_call,
    backdoor_attempt_to_dict,
    dict_to_backdoor_attempt,
    strategy_result_to_dict,
    dict_to_strategy_result,
    problem_result_to_dict,
    dict_to_problem_result,
    test_result_to_dict,
    dict_to_test_result,
    dataset_to_dict,
    dict_to_dataset,
)

# Store
from .store import (
    DatasetStore,
    dataset_store,
    TTL_DRAFT,
    TTL_PUBLISHED,
)

# Convenience functions
from .functions import (
    create_dataset,
    get_dataset,
    update_dataset,
    delete_dataset,
    list_datasets,
    publish_dataset,
    duplicate_dataset,
)

__all__ = [
    # Models
    'DatasetSettings',
    'DatasetModels',
    'LLMCall',
    'BackdoorAttempt',
    'ATTACK_STRATEGIES',
    'StrategyResult',
    'ProblemResult',
    'TestRunResult',
    'Dataset',
    # Serialization
    'settings_to_dict',
    'dict_to_settings',
    'models_to_dict',
    'dict_to_models',
    'llm_call_to_dict',
    'dict_to_llm_call',
    'backdoor_attempt_to_dict',
    'dict_to_backdoor_attempt',
    'strategy_result_to_dict',
    'dict_to_strategy_result',
    'problem_result_to_dict',
    'dict_to_problem_result',
    'test_result_to_dict',
    'dict_to_test_result',
    'dataset_to_dict',
    'dict_to_dataset',
    # Store
    'DatasetStore',
    'dataset_store',
    'TTL_DRAFT',
    'TTL_PUBLISHED',
    # Functions
    'create_dataset',
    'get_dataset',
    'update_dataset',
    'delete_dataset',
    'list_datasets',
    'publish_dataset',
    'duplicate_dataset',
]
