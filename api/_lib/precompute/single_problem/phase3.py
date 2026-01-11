"""
Phase 3: Find Exploits

Find exploits for the sneakiest backdoor using the paper's 9-step pipeline:
1. Detection Check (2-part): Identify suspicious logic, rate likelihood
2. Isolate Snippet: Extract the specific backdoor code
3. Remove Backdoor: Get reference solution (we use U_normal_solution)
4. Enumerate Properties: List all constraints for exploit input
5. Validate Properties: Self-check the property list
6. Check Possibility: Verify exploit is constructable
7. Rate Difficulty: Assess construction complexity
8. Construct Input: Step-by-step build exploit
9. Validate Input: Verify all properties satisfied
"""

import re
from typing import List, Optional, Tuple, TYPE_CHECKING

from ..models import BackdoorProposal
from ..mixins import parse_rating

if TYPE_CHECKING:
    from .engine import SingleProblemEngine


def phase3_find_exploits(engine: "SingleProblemEngine", proposals: List[BackdoorProposal]) -> List[BackdoorProposal]:
    """Phase 3: Find exploits for SNEAKIEST backdoor only using full pipeline"""

    # Find the sneakiest backdoor (no threshold filtering - done at simulation time)
    sneakiest = max(proposals, key=lambda x: x.sneakiness) if proposals else None

    for idx, proposal in enumerate(proposals):
        # Only process the sneakiest backdoor
        if proposal != sneakiest:
            proposal.phase_3_complete = True
            continue

        print(f"\n{'='*60}")
        print(f"PHASE 3: EXPLOIT GENERATION FOR BACKDOOR {idx}")
        print(f"Sneakiness: {proposal.sneakiness}")
        print(f"{'='*60}\n")

        # Run the 9-step pipeline
        result = _run_exploit_pipeline(engine, proposal, idx)

        # Store results
        proposal.detection_score = result.get("detection_score")
        proposal.exploit_difficulty = result.get("exploit_difficulty")
        proposal.exploit_properties = result.get("properties_list")
        proposal.exploit_possible = result.get("exploit_possible", False)
        proposal.exploit_found = result.get("exploit_found", False)
        proposal.exploit_input = result.get("exploit_input")
        proposal.exploit_valid = result.get("exploit_valid", False)
        proposal.exploits = [result["exploit_input"]] if result.get("exploit_input") else []

        proposal.phase_3_complete = True

    return proposals


def _run_exploit_pipeline(engine: "SingleProblemEngine", proposal: BackdoorProposal, idx: int) -> dict:
    """Run the full 9-step exploit generation pipeline"""

    result = {}

    # Step 1a: Identify suspicious logic
    print("[Step 1a] Identifying suspicious logic...")
    suspicious_logic = _step1a_identify_suspicious_logic(engine, proposal, idx)

    # Step 1b: Rate backdoor likelihood
    print("[Step 1b] Rating backdoor likelihood...")
    detection_score = _step1b_rate_likelihood(engine, idx)
    result["detection_score"] = detection_score
    print(f"  Detection score: {detection_score}/10")

    # Step 2: Isolate suspicious snippet
    print("[Step 2] Isolating suspicious snippet...")
    suspicious_snippet = _step2_isolate_snippet(engine, proposal, idx)
    result["suspicious_snippet"] = suspicious_snippet
    print(f"  Snippet: {suspicious_snippet[:100]}..." if len(suspicious_snippet) > 100 else f"  Snippet: {suspicious_snippet}")

    # Step 3: Get reference solution (we already have U_normal_solution)
    print("[Step 3] Using U_normal_solution as reference (skipping reconstruction)")
    correct_solution = engine.result.U_normal_solution

    # Step 4: Enumerate exploit properties
    print("[Step 4] Enumerating exploit properties...")
    properties_response, properties_list = _step4_enumerate_properties(
        engine, proposal, correct_solution, suspicious_snippet, idx
    )
    result["properties_list"] = properties_list
    print(f"  Found {len(properties_list.splitlines())} properties")

    # Step 5: Validate properties
    print("[Step 5] Validating properties...")
    validated_properties = _step5_validate_properties(engine, properties_list, idx)
    result["validated_properties"] = validated_properties

    # Step 6: Check if exploit is possible
    print("[Step 6] Checking if exploit is possible...")
    exploit_possible = _step6_check_possibility(engine, validated_properties, idx)
    result["exploit_possible"] = exploit_possible
    print(f"  Exploit possible: {exploit_possible}")

    if not exploit_possible:
        print("  Exploit not possible - stopping pipeline")
        return result

    # Step 7: Rate exploit difficulty
    print("[Step 7] Rating exploit difficulty...")
    difficulty = _step7_rate_difficulty(engine, proposal, suspicious_snippet, validated_properties, idx)
    result["exploit_difficulty"] = difficulty
    print(f"  Difficulty: {difficulty}/10")

    # Step 8: Construct exploit step-by-step
    print("[Step 8] Constructing exploit input...")
    exploit_input = _step8_construct_exploit(engine, proposal, validated_properties, idx)
    result["exploit_input"] = exploit_input
    print(f"  Constructed input: {exploit_input[:100]}..." if exploit_input and len(exploit_input) > 100 else f"  Constructed input: {exploit_input}")

    if not exploit_input:
        print("  Failed to construct exploit input")
        return result

    # Step 9: Validate exploit input
    print("[Step 9] Validating exploit input...")
    is_valid, fix_needed = _step9_validate_input(engine, proposal, exploit_input, validated_properties, idx)
    result["exploit_valid"] = is_valid
    result["exploit_found"] = is_valid
    print(f"  Input valid: {is_valid}")

    if not is_valid and fix_needed:
        print(f"  Fix needed: {fix_needed}")
        # Could add retry logic here

    return result


# =============================================================================
# STEP IMPLEMENTATIONS
# =============================================================================

def _step1a_identify_suspicious_logic(engine: "SingleProblemEngine", proposal: BackdoorProposal, idx: int) -> str:
    """Step 1a: Identify suspicious logic in the code"""
    prompt = engine._get_prompt("IDENTIFY_SUSPICIOUS_LOGIC_PROMPT").format(
        problem_text=engine.problem_text,
        code=proposal.backdoored_code
    )
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"identify_suspicious_logic_{idx}",
        role="Red Team"
    )
    return response


def _step1b_rate_likelihood(engine: "SingleProblemEngine", idx: int) -> float:
    """Step 1b: Rate likelihood of backdoor (1-10)"""
    prompt = engine._get_prompt("RATE_BACKDOOR_LIKELIHOOD_PROMPT")
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"rate_backdoor_likelihood_{idx}",
        role="Red Team"
    )
    return parse_rating(response, 1, 10, 5.0)


def _step2_isolate_snippet(engine: "SingleProblemEngine", proposal: BackdoorProposal, idx: int) -> str:
    """Step 2: Isolate the suspicious code snippet"""
    prompt = engine._get_prompt("IDENTIFY_SNIPPET_PROMPT").format(
        problem_text=engine.problem_text,
        code=proposal.backdoored_code
    )
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"isolate_snippet_{idx}",
        role="Red Team"
    )
    # Extract code from response (may be in backticks)
    snippet = _extract_code_block(response)
    return snippet if snippet else response.strip()


def _step4_enumerate_properties(
    engine: "SingleProblemEngine",
    proposal: BackdoorProposal,
    correct_solution: str,
    suspicious_snippet: str,
    idx: int
) -> Tuple[str, str]:
    """Step 4: Enumerate all properties needed for exploit input"""
    prompt = engine._get_prompt("ENUMERATE_EXPLOIT_PROPERTIES_PROMPT").format(
        problem_text=engine.problem_text,
        correct_solution=correct_solution,
        backdoored_solution=proposal.backdoored_code,
        suspicious_snippet=suspicious_snippet
    )
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"enumerate_properties_{idx}",
        role="Red Team"
    )

    # Extract the "All Necessary Properties" section
    properties_list = _extract_properties_section(response)
    return response, properties_list


def _step5_validate_properties(engine: "SingleProblemEngine", properties_list: str, idx: int) -> str:
    """Step 5: Validate the property list for issues"""
    prompt = engine._get_prompt("VALIDATE_PROPERTIES_PROMPT").format(
        properties_list=properties_list
    )
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"validate_properties_{idx}",
        role="Red Team"
    )

    # Check if corrected properties were provided
    if "## Corrected Properties" in response:
        corrected = _extract_section(response, "## Corrected Properties")
        return corrected if corrected else properties_list

    return properties_list


def _step6_check_possibility(engine: "SingleProblemEngine", properties_list: str, idx: int) -> bool:
    """Step 6: Check if exploit is actually constructable"""
    prompt = engine._get_prompt("EXPLOIT_POSSIBLE_PROMPT").format(
        trigger_properties=properties_list,
        constraints="Standard competitive programming constraints apply"
    )
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"check_possibility_{idx}",
        role="Red Team"
    )

    # Parse <is_possible> tag
    match = re.search(r'<is_possible>\s*(yes|no)\s*</is_possible>', response, re.IGNORECASE)
    if match:
        return match.group(1).lower() == 'yes'

    # Fallback: check for YES at start
    return response.strip().upper().startswith("YES")


def _step7_rate_difficulty(
    engine: "SingleProblemEngine",
    proposal: BackdoorProposal,
    suspicious_snippet: str,
    properties_list: str,
    idx: int
) -> float:
    """Step 7: Rate difficulty of constructing exploit (1-10)"""
    prompt = engine._get_prompt("RATE_EXPLOIT_DIFFICULTY_PROMPT").format(
        problem_text=engine.problem_text,
        suspicious_snippet=suspicious_snippet,
        properties_list=properties_list
    )
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"rate_difficulty_{idx}",
        role="Red Team"
    )
    return parse_rating(response, 1, 10, 5.0)


def _step8_construct_exploit(
    engine: "SingleProblemEngine",
    proposal: BackdoorProposal,
    properties_list: str,
    idx: int
) -> Optional[str]:
    """Step 8: Construct exploit input step-by-step"""
    prompt = engine._get_prompt("CONSTRUCT_EXPLOIT_STEPWISE_PROMPT").format(
        problem_text=engine.problem_text,
        backdoored_code=proposal.backdoored_code,
        properties_list=properties_list
    )
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"construct_exploit_{idx}",
        role="Red Team"
    )

    # Extract the "Final Input" section
    final_input = _extract_section(response, "## Final Input")
    if final_input:
        # Clean up any remaining formatting
        final_input = final_input.strip()
        # Remove bullet separators if present (paper's technique)
        final_input = final_input.replace("•", "")
        return final_input

    # Fallback: try to extract from end of response
    lines = response.strip().split('\n')
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line and not line.startswith('#') and not line.startswith('-'):
            return line

    return None


def _step9_validate_input(
    engine: "SingleProblemEngine",
    proposal: BackdoorProposal,
    exploit_input: str,
    properties_list: str,
    idx: int
) -> Tuple[bool, Optional[str]]:
    """Step 9: Validate that constructed input satisfies all properties"""
    prompt = engine._get_prompt("VALIDATE_EXPLOIT_INPUT_PROMPT").format(
        problem_text=engine.problem_text,
        backdoored_code=proposal.backdoored_code,
        exploit_input=exploit_input,
        properties_list=properties_list
    )
    response = engine._call_llm(
        engine.models.get("red_team_model", "gpt-4o"),
        prompt,
        f"validate_input_{idx}",
        role="Red Team"
    )

    # Parse <valid> tag
    valid_match = re.search(r'<valid>\s*(yes|no)\s*</valid>', response, re.IGNORECASE)
    is_valid = valid_match and valid_match.group(1).lower() == 'yes'

    # Parse <fix_needed> if present
    fix_match = re.search(r'<fix_needed>(.*?)</fix_needed>', response, re.DOTALL)
    fix_needed = fix_match.group(1).strip() if fix_match else None

    return is_valid, fix_needed


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _extract_code_block(text: str) -> Optional[str]:
    """Extract code from markdown code blocks"""
    # Try to find ```python or ``` blocks
    pattern = r'```(?:python)?\s*\n(.*?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None


def _extract_properties_section(text: str) -> str:
    """Extract the 'All Necessary Properties' section from response"""
    # Look for the section header
    patterns = [
        r'##\s*All Necessary Properties\s*\n(.*?)(?=\n##|\Z)',
        r'\*\*All Necessary Properties\*\*\s*\n(.*?)(?=\n\*\*|\Z)',
        r'All Necessary Properties:?\s*\n(.*?)(?=\n[A-Z]|\Z)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Fallback: look for enumerated list at end
    lines = text.strip().split('\n')
    properties = []
    in_list = False

    for line in reversed(lines):
        line = line.strip()
        if re.match(r'^\d+\.', line):
            properties.insert(0, line)
            in_list = True
        elif in_list and line:
            break

    return '\n'.join(properties) if properties else text


def _extract_section(text: str, header: str) -> Optional[str]:
    """Extract content after a markdown header"""
    # Escape special regex characters in header
    escaped_header = re.escape(header)
    pattern = rf'{escaped_header}\s*\n(.*?)(?=\n##|\Z)'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return None
