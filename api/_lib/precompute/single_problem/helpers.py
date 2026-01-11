"""
Single Problem Engine - Helper Functions

Utility functions used across multiple phases.
"""

import difflib
from typing import List, TYPE_CHECKING

from api._lib.dataset import dataset_store, BackdoorAttempt
from ..models import BackdoorProposal

if TYPE_CHECKING:
    from .engine import SingleProblemEngine


def persist_result(engine: "SingleProblemEngine"):
    """Persist the current result to storage"""
    dataset_store.update_problem_result(engine.dataset_id, engine.problem_id, engine.result)
    if engine.on_update:
        engine.on_update(engine.result)


def extract_diff_snippet(original_code: str, backdoored_code: str) -> str:
    """Extract the diff between original and backdoored code with standard diff styling."""
    if not original_code or not backdoored_code:
        return "Unable to extract diff"

    original_lines = original_code.splitlines()
    backdoored_lines = backdoored_code.splitlines()

    # Get unified diff
    diff = list(difflib.unified_diff(
        original_lines,
        backdoored_lines,
        fromfile='original',
        tofile='backdoored',
        lineterm=''
    ))

    if len(diff) <= 2:
        return "No differences found"

    # Return the diff content (skip the --- and +++ headers)
    # Keep the @@ hunk headers and the actual diff lines
    diff_lines = []
    for line in diff[2:]:  # Skip --- and +++ lines
        diff_lines.append(line)

    return '\n'.join(diff_lines)


def reconstruct_proposals(engine: "SingleProblemEngine") -> List[BackdoorProposal]:
    """Reconstruct BackdoorProposal objects from stored BackdoorAttempts"""
    proposals = []
    for idx, attempt in enumerate(engine.result.backdoor_attempts):
        proposal = BackdoorProposal(
            problem_id=engine.problem_id,
            proposal_id=f"{engine.problem_id}_bd_{idx}",
            idea=attempt.idea,
            backdoored_code=attempt.code,
            sneakiness=attempt.sneakiness,
            fail_rate=0.05,
            rating1=attempt.rating1 or 0.0,
            rating2=attempt.rating2 or 0.0,
            backdoor_snippet=attempt.backdoor_snippet,
            # Phase 3 data
            exploit_found=attempt.exploit_found or False,
            exploits=[attempt.exploit_input] if attempt.exploit_input else None,
            phase_3_complete=True,
            # Phase 4 data
            test_cases_passed=attempt.test_cases_passed,
            test_cases_total=attempt.test_cases_total,
            test_case_results=attempt.test_case_results,
            exploit_input=attempt.exploit_input,
            exploit_output=attempt.exploit_output,
            exploit_expected=attempt.exploit_expected,
            exploit_verified=attempt.exploit_verified or False,
            outcome=attempt.outcome,
            phase_4_complete=True,
        )
        proposals.append(proposal)
    return proposals


def store_backdoor_attempts(engine: "SingleProblemEngine", proposals: List[BackdoorProposal]):
    """Store backdoor proposals as attempts in the result.

    This stores all backdoor attempts with their sneakiness scores and verification results.
    Strategy/threshold filtering happens at simulation time.
    """
    # Store all backdoor attempts with their sneakiness scores and Phase 4 results
    for idx, p in enumerate(proposals):
        attempt = BackdoorAttempt(
            idea=p.idea,
            code=p.backdoored_code,
            sneakiness=p.sneakiness,
            selected=False,
            # Phase 2 ratings
            rating1=getattr(p, 'rating1', None),
            rating2=getattr(p, 'rating2', None),
            backdoor_snippet=getattr(p, 'backdoor_snippet', None),
            # Phase 4 test case results
            test_cases_passed=getattr(p, 'test_cases_passed', None),
            test_cases_total=getattr(p, 'test_cases_total', None),
            test_case_results=getattr(p, 'test_case_results', None),
            # Phase 3 exploit finding
            exploit_found=getattr(p, 'exploit_found', False),
            # Phase 4 exploit verification
            exploit_input=getattr(p, 'exploit_input', None),
            exploit_output=getattr(p, 'exploit_output', None),
            exploit_expected=getattr(p, 'exploit_expected', None),
            exploit_verified=getattr(p, 'exploit_verified', False),
            # Outcome classification
            outcome=getattr(p, 'outcome', None)
        )
        engine.result.backdoor_attempts.append(attempt)

    # Find the sneakiest backdoor overall and mark its index
    sneakiest = max(proposals, key=lambda x: x.sneakiness) if proposals else None
    if sneakiest:
        for idx, attempt in enumerate(engine.result.backdoor_attempts):
            if attempt.code == sneakiest.backdoored_code and attempt.sneakiness == sneakiest.sneakiness:
                engine.result.sneakiest_backdoor_idx = idx
                # Set legacy fields for backward compatibility
                engine.result.sneakiness = sneakiest.sneakiness
                engine.result.exploit_found = sneakiest.exploit_found
                engine.result.U_backdoored_solution = sneakiest.backdoored_code
                break
