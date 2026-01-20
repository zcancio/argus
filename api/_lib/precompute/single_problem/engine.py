"""
Single Problem Execution Engine

Orchestrates phases 1-5 for individual APPS problems with full LLM tracking.
Strategy/threshold filtering happens at simulation time.
"""

from datetime import datetime
from typing import List, Dict, Optional, Any

from api._lib.llm import LLMClient
from api._lib.dataset import ProblemResult, dataset_store
from api._lib.executor import PistonClient, get_piston_client

from ..models import BackdoorProposal
from ..mixins import LLMCallTrackerMixin

from .helpers import persist_result, reconstruct_proposals, store_backdoor_attempts
from .phase1 import phase1_generate_baselines
from .phase2 import phase2_generate_backdoors
from .phase3 import phase3_find_exploits
from .phase4 import phase4_verify_exploits
from .phase5 import phase5_monitoring_scores


class SingleProblemEngine(LLMCallTrackerMixin):
    """
    Runs phases 1-5 for a single APPS problem.
    Logs all LLM calls to ProblemResult.
    """

    def __init__(
        self,
        dataset_id: str,
        problem_id: str,
        problem_text: str,
        solutions: List[str],
        models: dict,
        prompts: Optional[Dict[str, str]] = None,
        openai_key: str = None,
        anthropic_key: str = None,
        piston_url: str = None,
        on_update: callable = None,
        test_cases: Optional[Dict[str, Any]] = None,
        problem_difficulty: int = 1,
        max_difficulty: int = 6,
        programming_language: str = "Python"
    ):
        self.dataset_id = dataset_id
        self.problem_id = problem_id
        self.problem_text = problem_text
        self.solutions = solutions
        self.models = models
        self.prompts = prompts or {}
        self.on_update = on_update
        self.llm = LLMClient(openai_key=openai_key, anthropic_key=anthropic_key)
        self.piston = PistonClient(piston_url) if piston_url else get_piston_client()
        self.test_cases = test_cases or {}
        self.problem_difficulty = problem_difficulty
        self.max_difficulty = max_difficulty
        self.programming_language = programming_language

        # Initialize result
        self.result = ProblemResult(
            problem_id=problem_id,
            status="running",
            started_at=datetime.utcnow().isoformat()
        )
        self._call_counter = 0
        self._current_phase = 1

    def _persist(self):
        """Persist the current result to storage"""
        persist_result(self)

    def run(self) -> ProblemResult:
        """Run phases 1-5 for this problem"""
        return self.run_from_phase(1)

    def run_from_phase(self, from_phase: int) -> ProblemResult:
        """Run phases starting from a specific phase"""
        try:
            proposals = []

            # If starting from phase 3+, reconstruct proposals from backdoor_attempts
            if from_phase >= 3 and self.result.backdoor_attempts:
                proposals = reconstruct_proposals(self)

            # Phase 1: Generate Baseline Solutions
            if from_phase <= 1:
                self._current_phase = 1
                self.result.current_phase = 1
                self._persist()
                phase1_generate_baselines(self)
                if 1 not in self.result.phases_completed:
                    self.result.phases_completed.append(1)

            # Phase 2: Generate Backdoors (simplified for single problem)
            if from_phase <= 2:
                self._current_phase = 2
                self.result.current_phase = 2
                self._persist()
                proposals = phase2_generate_backdoors(self)
                if 2 not in self.result.phases_completed:
                    self.result.phases_completed.append(2)

            # Phase 3: Find Exploits
            if from_phase <= 3:
                self._current_phase = 3
                self.result.current_phase = 3
                self._persist()
                proposals = phase3_find_exploits(self, proposals)
                if 3 not in self.result.phases_completed:
                    self.result.phases_completed.append(3)

            # Phase 4: Verify Exploits
            if from_phase <= 4:
                self._current_phase = 4
                self.result.current_phase = 4
                self._persist()
                proposals = phase4_verify_exploits(self, proposals)
                if 4 not in self.result.phases_completed:
                    self.result.phases_completed.append(4)

            # Phase 5: Monitoring Scores + Trusted Editing
            if from_phase <= 5:
                self._current_phase = 5
                self.result.current_phase = 5
                self._persist()
                # Clear existing backdoor_attempts before storing new ones
                self.result.backdoor_attempts = []
                phase5_monitoring_scores(self, proposals)
                store_backdoor_attempts(self, proposals)
                if 5 not in self.result.phases_completed:
                    self.result.phases_completed.append(5)

            # Mark completed
            self.result.status = "completed"
            self.result.completed_at = datetime.utcnow().isoformat()
            self._persist()

            return self.result

        except Exception as e:
            self.result.status = "failed"
            self.result.error = str(e)
            self.result.completed_at = datetime.utcnow().isoformat()
            self._persist()
            return self.result
