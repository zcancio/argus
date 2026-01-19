"""Simulation Router - Monte Carlo simulation using pre-computed datasets"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from api._lib.simulation import (
    run_simulation,
    SimulationConfig,
    RedTeamConfig,
    BlueTeamConfig,
)

router = APIRouter(prefix="/api", tags=["simulation"])


class SimulationRequest(BaseModel):
    """Request to run a simulation."""
    dataset_id: str

    # Red team config
    backdoor_rate: float = 0.20  # Target % of problems with backdoors
    max_fail_rate: float = 0.10  # Max fail rate on small inputs

    # Blue team config
    monitor_type: str = "trusted"  # "trusted" or "untrusted"
    audit_budget_rate: float = 0.02
    free_start: int = 10
    defer_enabled: bool = False
    defer_rate: float = 0.10
    defer_action: str = "replace"  # "replace" or "edit"

    # Simulation config
    num_trials: int = 2000
    num_problems: Optional[int] = None  # If None, uses 3.33x dataset size (paper ratio)
    coup_subsample_rate: float = 1/12  # Variance reduction (paper default ~8.3%)
    random_seed: Optional[int] = None


@router.post("/simulate")
def run_simulation_endpoint(request: SimulationRequest):
    """
    Run a Monte Carlo simulation using pre-computed dataset results.

    This endpoint makes zero API calls - all data is looked up from
    pre-computed results in the local dataset.
    """
    try:
        config = SimulationConfig(
            red_team=RedTeamConfig(
                backdoor_rate=request.backdoor_rate,
                max_fail_rate=request.max_fail_rate,
            ),
            blue_team=BlueTeamConfig(
                monitor_type=request.monitor_type,
                audit_budget_rate=request.audit_budget_rate,
                free_start=request.free_start,
                defer_enabled=request.defer_enabled,
                defer_rate=request.defer_rate,
                defer_action=request.defer_action,
            ),
            num_trials=request.num_trials,
            num_problems=request.num_problems,
            coup_subsample_rate=request.coup_subsample_rate,
            random_seed=request.random_seed,
        )

        results = run_simulation(request.dataset_id, config)

        return {
            "status": "completed",
            "dataset_id": request.dataset_id,
            "config": {
                "red_team": {
                    "backdoor_rate": request.backdoor_rate,
                    "max_fail_rate": request.max_fail_rate,
                },
                "blue_team": {
                    "audit_budget_rate": request.audit_budget_rate,
                    "free_start": request.free_start,
                    "defer_enabled": request.defer_enabled,
                    "defer_rate": request.defer_rate,
                },
                "num_trials": request.num_trials,
                "num_problems": results.num_problems,  # Use actual value (may be auto-calculated)
                "num_problems_requested": request.num_problems,  # Original request (None = auto)
                "coup_subsample_rate": request.coup_subsample_rate,
            },
            "results": results.to_dict(),
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=500, detail=f"{str(e)}\n{traceback.format_exc()}")
