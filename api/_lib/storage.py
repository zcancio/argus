"""
Storage module for ARGUS - uses Vercel KV (Redis) for persistence
"""

import os
import json
from typing import Optional
from datetime import datetime


def get_redis_client():
    """Get Redis client for Vercel KV."""
    kv_url = os.environ.get("KV_URL")
    
    if not kv_url:
        return None
    
    try:
        import redis
        return redis.from_url(kv_url)
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return None


class ExperimentStore:
    """
    Store experiment results in Vercel KV.
    Falls back to in-memory storage if KV is not configured.
    """
    
    def __init__(self):
        self.redis = get_redis_client()
        self._memory_store = {}  # Fallback for local dev
    
    @property
    def is_persistent(self) -> bool:
        return self.redis is not None
    
    def save(self, experiment_id: str, data: dict) -> bool:
        """Save experiment result."""
        data["saved_at"] = datetime.now().isoformat()
        
        if self.redis:
            try:
                # Store the experiment
                self.redis.set(
                    f"experiment:{experiment_id}",
                    json.dumps(data),
                    ex=60 * 60 * 24 * 30  # 30 day expiry
                )
                # Add to index for listing
                self.redis.zadd(
                    "experiments:index",
                    {experiment_id: datetime.now().timestamp()}
                )
                return True
            except Exception as e:
                print(f"Redis save failed: {e}")
                return False
        else:
            self._memory_store[experiment_id] = data
            return True
    
    def get(self, experiment_id: str) -> Optional[dict]:
        """Get experiment by ID."""
        if self.redis:
            try:
                data = self.redis.get(f"experiment:{experiment_id}")
                return json.loads(data) if data else None
            except Exception as e:
                print(f"Redis get failed: {e}")
                return None
        else:
            return self._memory_store.get(experiment_id)
    
    def list_all(self, limit: int = 50) -> list:
        """List recent experiments."""
        if self.redis:
            try:
                # Get experiment IDs from sorted set (most recent first)
                exp_ids = self.redis.zrevrange("experiments:index", 0, limit - 1)
                
                results = []
                for exp_id in exp_ids:
                    if isinstance(exp_id, bytes):
                        exp_id = exp_id.decode()
                    data = self.get(exp_id)
                    if data:
                        results.append(data)
                return results
            except Exception as e:
                print(f"Redis list failed: {e}")
                return []
        else:
            # Memory fallback - return most recent
            items = list(self._memory_store.values())
            return sorted(items, key=lambda x: x.get("saved_at", ""), reverse=True)[:limit]
    
    def get_pareto_data(self) -> list:
        """Get data for Pareto frontier visualization."""
        experiments = self.list_all(limit=100)
        points = []
        
        for exp in experiments:
            metrics = exp.get("metrics", {})
            config = exp.get("config", {})
            points.append({
                "experiment_id": exp.get("experiment_id"),
                "protocol": config.get("protocol"),
                "safety_rate": metrics.get("safety_rate", 0),
                "usefulness_rate": metrics.get("usefulness_rate", 0),
                "attack_catch_rate": metrics.get("attack_catch_rate", 0),
                "false_positive_rate": metrics.get("false_positive_rate", 0),
            })
        
        return points
    
    def delete(self, experiment_id: str) -> bool:
        """Delete an experiment."""
        if self.redis:
            try:
                self.redis.delete(f"experiment:{experiment_id}")
                self.redis.zrem("experiments:index", experiment_id)
                return True
            except Exception as e:
                print(f"Redis delete failed: {e}")
                return False
        else:
            if experiment_id in self._memory_store:
                del self._memory_store[experiment_id]
                return True
            return False


# Global store instance
store = ExperimentStore()
