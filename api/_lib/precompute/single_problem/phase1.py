"""
Phase 1: Generate Baseline Solutions

Generate U and T solutions and test them against APPS test cases.
"""

from typing import TYPE_CHECKING

from ..mixins import strip_markdown_code_blocks, detect_language
from .logger import get_logger

if TYPE_CHECKING:
    from .engine import SingleProblemEngine


def phase1_generate_baselines(engine: "SingleProblemEngine"):
    """Phase 1: Generate U and T solutions and test them"""
    log = get_logger()

    log.phase_start(1, "GENERATE BASELINE SOLUTIONS")

    # Get U's solution
    log.step("U Solution", "Generating...")
    u_prompt = engine._render_prompt(
        "U_SOLUTION_PROMPT",
        problem_text=engine.problem_text,
        constraints="Standard constraints apply",
        programming_language=engine.programming_language
    )
    u_response = engine._call_llm(
        engine.models.get("untrusted_model", "gpt-4o"),
        u_prompt,
        "generate_u_solution",
        role="Untrusted"
    )
    engine.result.U_normal_solution = strip_markdown_code_blocks(u_response)
    log.code_block("U Solution Code", engine.result.U_normal_solution)

    # Get T's solution
    log.step("T Solution", "Generating...")
    t_prompt = engine._render_prompt(
        "T_SOLUTION_PROMPT",
        problem_text=engine.problem_text,
        constraints="Standard constraints apply",
        programming_language=engine.programming_language
    )
    t_response = engine._call_llm(
        engine.models.get("trusted_model", "gpt-3.5-turbo"),
        t_prompt,
        "generate_t_solution",
        role="Trusted"
    )
    engine.result.T_solution = strip_markdown_code_blocks(t_response)
    log.code_block("T Solution Code", engine.result.T_solution)

    # Test solutions against APPS test cases
    _test_baseline_solutions(engine)

    # Phase summary
    u_result = f"{engine.result.U_tests_passed}/{engine.result.U_tests_total}" if engine.result.U_tests_total else "N/A"
    t_result = f"{engine.result.T_tests_passed}/{engine.result.T_tests_total}" if engine.result.T_tests_total else "N/A"
    log.phase_end(1, f"U={u_result}, T={t_result}")


def _test_baseline_solutions(engine: "SingleProblemEngine"):
    """Test U and T solutions against APPS test cases using Piston"""
    log = get_logger()

    if not engine.piston.is_available():
        log.step("Test Cases", "Piston not available - skipping", status="warn")
        return

    # Parse test cases from APPS format
    inputs = engine.test_cases.get("inputs", [])
    outputs = engine.test_cases.get("outputs", [])
    max_test_cases = min(5, len(inputs), len(outputs))

    if max_test_cases == 0:
        log.step("Test Cases", "No test cases available - skipping", status="warn")
        return

    log.subsection(f"Testing Baseline Solutions ({max_test_cases} test cases)")

    # Test U's solution
    u_passed = 0
    u_language = detect_language(engine.result.U_normal_solution)

    with log.indent():
        log.step("U Solution", f"Testing ({u_language})...")

        with log.collapsed(f"U solution test details"):
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
        status = "ok" if u_passed == max_test_cases else ("warn" if u_passed > 0 else "error")
        log.summary("U Result", f"{u_passed}/{max_test_cases} passed", status=status)

    # Test T's solution
    t_passed = 0
    t_language = detect_language(engine.result.T_solution)

    with log.indent():
        log.step("T Solution", f"Testing ({t_language})...")

        with log.collapsed(f"T solution test details"):
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
        status = "ok" if t_passed == max_test_cases else ("warn" if t_passed > 0 else "error")
        log.summary("T Result", f"{t_passed}/{max_test_cases} passed", status=status)
