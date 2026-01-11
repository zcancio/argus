"""
Phase 1: Generate Baseline Solutions

Generate U and T solutions and test them against APPS test cases.
"""

from typing import TYPE_CHECKING

from ..mixins import strip_markdown_code_blocks, detect_language

if TYPE_CHECKING:
    from .engine import SingleProblemEngine


def phase1_generate_baselines(engine: "SingleProblemEngine"):
    """Phase 1: Generate U and T solutions and test them"""
    # Get U's solution
    u_prompt = engine._get_prompt("U_SOLUTION_PROMPT").format(
        problem_text=engine.problem_text,
        constraints="Standard constraints apply"
    )
    u_response = engine._call_llm(
        engine.models.get("untrusted_model", "gpt-4o"),
        u_prompt,
        "generate_u_solution",
        role="Untrusted"
    )
    engine.result.U_normal_solution = strip_markdown_code_blocks(u_response)

    # Get T's solution
    t_prompt = engine._get_prompt("T_SOLUTION_PROMPT").format(
        problem_text=engine.problem_text,
        constraints="Standard constraints apply"
    )
    t_response = engine._call_llm(
        engine.models.get("trusted_model", "gpt-3.5-turbo"),
        t_prompt,
        "generate_t_solution",
        role="Trusted"
    )
    engine.result.T_solution = strip_markdown_code_blocks(t_response)

    # Test solutions against APPS test cases
    _test_baseline_solutions(engine)


def _test_baseline_solutions(engine: "SingleProblemEngine"):
    """Test U and T solutions against APPS test cases using Piston"""
    if not engine.piston.is_available():
        print("Piston not available - skipping baseline solution tests")
        return

    # Parse test cases from APPS format
    inputs = engine.test_cases.get("inputs", [])
    outputs = engine.test_cases.get("outputs", [])
    max_test_cases = min(5, len(inputs), len(outputs))

    if max_test_cases == 0:
        print("No test cases available - skipping baseline solution tests")
        return

    print(f"\n{'='*60}")
    print(f"TESTING BASELINE SOLUTIONS ({max_test_cases} test cases)")
    print(f"{'='*60}")

    # Test U's solution
    u_passed = 0
    u_language = detect_language(engine.result.U_normal_solution)
    print(f"\n--- Testing U solution (language: {u_language}) ---")
    print(f"Code:\n{engine.result.U_normal_solution}\n")

    for tc_idx in range(max_test_cases):
        tc_input = str(inputs[tc_idx]) if tc_idx < len(inputs) else ""
        tc_expected = str(outputs[tc_idx]).strip() if tc_idx < len(outputs) else ""

        result = engine.piston.execute(
            language=u_language,
            code=engine.result.U_normal_solution,
            stdin=tc_input,
            run_timeout=3000
        )

        tc_actual = result.stdout.strip() if result.success else ""
        tc_passed = tc_actual == tc_expected and not result.error and not result.timed_out

        if tc_passed:
            u_passed += 1
            print(f"  Test {tc_idx + 1}: PASS")
        else:
            print(f"  Test {tc_idx + 1}: FAIL")
            print(f"    Expected: {tc_expected[:100]}")
            print(f"    Actual: {tc_actual[:100]}")
            if result.error:
                print(f"    Error: {result.error}")

    engine.result.U_tests_passed = u_passed
    engine.result.U_tests_total = max_test_cases
    print(f"U solution: {u_passed}/{max_test_cases} tests passed")

    # Test T's solution
    t_passed = 0
    t_language = detect_language(engine.result.T_solution)
    print(f"\n--- Testing T solution (language: {t_language}) ---")
    print(f"Code:\n{engine.result.T_solution}\n")

    for tc_idx in range(max_test_cases):
        tc_input = str(inputs[tc_idx]) if tc_idx < len(inputs) else ""
        tc_expected = str(outputs[tc_idx]).strip() if tc_idx < len(outputs) else ""

        result = engine.piston.execute(
            language=t_language,
            code=engine.result.T_solution,
            stdin=tc_input,
            run_timeout=3000
        )

        tc_actual = result.stdout.strip() if result.success else ""
        tc_passed = tc_actual == tc_expected and not result.error and not result.timed_out

        if tc_passed:
            t_passed += 1
            print(f"  Test {tc_idx + 1}: PASS")
        else:
            print(f"  Test {tc_idx + 1}: FAIL")
            print(f"    Expected: {tc_expected[:100]}")
            print(f"    Actual: {tc_actual[:100]}")
            if result.error:
                print(f"    Error: {result.error}")

    engine.result.T_tests_passed = t_passed
    engine.result.T_tests_total = max_test_cases
    print(f"T solution: {t_passed}/{max_test_cases} tests passed")
    print(f"{'='*60}\n")
