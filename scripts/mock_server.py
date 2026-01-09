#!/usr/bin/env python3
"""
Mock OpenAI API Server for replaying captured flows.

Supports multiple problem flows:
- Problem 0003: FAILED_COUP_ATTEMPT (backdoor breaks normal tests)
- Problem 0060: SUCCESSFUL_COUP (backdoor passes tests + exploit works)
"""

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import hashlib
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"

# Mock data files for different problems
MOCK_DATA_FILES = {
    "0003": DATA_DIR / "mock_flow_0003_failed_coup.json",
    "0060": DATA_DIR / "mock_flow_0060_successful_coup.json",
}

# Loaded mock data
MOCK_BY_HASH = {}  # Indexed by prompt hash
MOCK_BY_STEP = {}  # Indexed by (problem_id, step_name)
LOADED_PROBLEMS = []

# Track current problem being processed (detected from prompts)
CURRENT_PROBLEM = None

# Track call counts for sequential step matching (e.g., implement_backdoor_0, _1, _2)
STEP_CALL_COUNTS = {}  # {(problem_id, base_step): count}


def load_mock_data():
    """Load captured flow data from all mock files."""
    global MOCK_BY_HASH, MOCK_BY_STEP, LOADED_PROBLEMS

    total_calls = 0
    for problem_id, filepath in MOCK_DATA_FILES.items():
        if not filepath.exists():
            print(f"Warning: {filepath} not found, skipping")
            continue

        with open(filepath) as f:
            data = json.load(f)

        # Store problem text for detection
        problem_text = data.get("apps_problem", {}).get("question", "")[:200]

        call_count = 0
        for call in data.get("llm_calls", []):
            prompt = call.get("prompt", "")
            response = call.get("response", "")
            step = call.get("step", "unknown")

            # Index by hash
            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            MOCK_BY_HASH[prompt_hash] = {
                "step": step,
                "response": response,
                "problem_id": problem_id
            }

            # Index by step (keep first occurrence per problem)
            step_key = (problem_id, step)
            if step_key not in MOCK_BY_STEP:
                MOCK_BY_STEP[step_key] = {
                    "response": response,
                    "problem_text": problem_text
                }

            call_count += 1

        total_calls += call_count
        LOADED_PROBLEMS.append(problem_id)
        print(f"Loaded {call_count} LLM calls from problem {problem_id}")

    print(f"Total: {total_calls} LLM calls from {len(LOADED_PROBLEMS)} problems")
    return LOADED_PROBLEMS


def detect_problem_from_prompt(prompt):
    """Detect which problem this prompt is for based on content."""
    # Check for unique problem identifiers
    if "Twice's 5th anniversary" in prompt or "Tzuyu and Sana" in prompt:
        return "0060"
    if "barrels" in prompt.lower() and "pour" in prompt.lower():
        return "0003"
    return None


def detect_step_from_prompt(prompt):
    """Detect the step type from prompt content."""
    prompt_lower = prompt.lower()

    # Phase 1
    if "solve" in prompt_lower and "competitive programming" in prompt_lower:
        return "generate_u_solution" if "untrusted" not in prompt_lower else "generate_t_solution"

    # Phase 2
    if "brainstorm" in prompt_lower and "backdoor" in prompt_lower:
        return "brainstorm_backdoor_ideas"
    if "implement" in prompt_lower and "backdoor" in prompt_lower:
        return "implement_backdoor"
    if "clean up" in prompt_lower or "cleanup" in prompt_lower:
        return "cleanup_backdoor"
    if "rate" in prompt_lower and ("difficult" in prompt_lower or "reviewer" in prompt_lower or "notice" in prompt_lower):
        return "rate_sneakiness_part1"
    if "rate" in prompt_lower and ("subtle" in prompt_lower or "trigger" in prompt_lower):
        return "rate_sneakiness_part2"

    # Phase 3
    if "rate" in prompt_lower and "suspicion" in prompt_lower and "code" in prompt_lower:
        return "check_suspicion"
    if "identify" in prompt_lower and "suspicious" in prompt_lower:
        return "identify_snippet"
    if ("analyze" in prompt_lower or "properties" in prompt_lower) and "trigger" in prompt_lower:
        return "exploit_properties"
    if "possible" in prompt_lower and "exploit" in prompt_lower:
        return "exploit_possible"
    if "construct" in prompt_lower and "trigger" in prompt_lower:
        return "construct_exploit"

    # Phase 6
    if "trusted" in prompt_lower and "monitor" in prompt_lower:
        return "get_t_suspicion"
    if "human" in prompt_lower and "auditor" in prompt_lower:
        return "get_h_suspicion"

    return None


class MockOpenAIHandler(BaseHTTPRequestHandler):
    """Handle OpenAI API requests with mock responses."""

    def _send_json(self, status_code, body):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_POST(self):
        if urlparse(self.path).path == "/v1/chat/completions":
            self._handle_chat()
        else:
            self._send_json(404, {"error": "Not found"})

    def _handle_chat(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._send_json(400, {"error": "Invalid JSON"})
            return

        # Extract prompt
        messages = request.get("messages", [])
        prompt = ""
        for msg in messages:
            if msg.get("role") == "user":
                prompt = msg.get("content", "")
                break

        global CURRENT_PROBLEM, STEP_CALL_COUNTS

        # Try exact hash match first
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        if prompt_hash in MOCK_BY_HASH:
            mock = MOCK_BY_HASH[prompt_hash]
            response_text = mock["response"]
            CURRENT_PROBLEM = mock["problem_id"]
            print(f"[MOCK] problem={mock['problem_id']} step={mock['step']} (hash match)")
        else:
            # Fall back to step-based matching
            detected_problem = detect_problem_from_prompt(prompt)
            if detected_problem and detected_problem != CURRENT_PROBLEM:
                # New problem detected - reset call counts
                CURRENT_PROBLEM = detected_problem
                STEP_CALL_COUNTS = {}
                print(f"[MOCK] New problem detected: {detected_problem}")

            detected_step = detect_step_from_prompt(prompt)

            if CURRENT_PROBLEM and detected_step:
                # Try exact step match first
                step_key = (CURRENT_PROBLEM, detected_step)
                if step_key in MOCK_BY_STEP:
                    response_text = MOCK_BY_STEP[step_key]["response"]
                    print(f"[MOCK] problem={CURRENT_PROBLEM} step={detected_step} (step match)")
                else:
                    # Use call counting for steps with suffixes
                    count_key = (CURRENT_PROBLEM, detected_step)
                    call_num = STEP_CALL_COUNTS.get(count_key, 0)

                    # Try with the current call number suffix
                    step_with_suffix = f"{detected_step}_{call_num}"
                    step_key = (CURRENT_PROBLEM, step_with_suffix)

                    if step_key in MOCK_BY_STEP:
                        response_text = MOCK_BY_STEP[step_key]["response"]
                        STEP_CALL_COUNTS[count_key] = call_num + 1
                        print(f"[MOCK] problem={CURRENT_PROBLEM} step={step_with_suffix} (sequential match #{call_num})")
                    else:
                        # Fallback: try _0, _1, _2 in order
                        found = False
                        for suffix in ["_0", "_1", "_2"]:
                            step_key = (CURRENT_PROBLEM, detected_step + suffix)
                            if step_key in MOCK_BY_STEP:
                                response_text = MOCK_BY_STEP[step_key]["response"]
                                print(f"[MOCK] problem={CURRENT_PROBLEM} step={detected_step}{suffix} (fallback match)")
                                found = True
                                break
                        if not found:
                            print(f"[MOCK] No match: problem={CURRENT_PROBLEM} step={detected_step}")
                            response_text = "Mock: No matching response"
            else:
                print(f"[MOCK] No match: {prompt[:100]}...")
                response_text = "Mock: No matching response"

        # Build response
        self._send_json(200, {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 1234567890,
            "model": request.get("model", "gpt-4o"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": response_text},
                "finish_reason": "stop"
            }],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20}
        })

    def log_message(self, format, *args):
        pass  # Suppress default logging


def main():
    problems = load_mock_data()

    print("\n" + "=" * 50)
    print("ARGUS Mock Server")
    print("=" * 50)
    print("Loaded flows:")
    print("  - 0003: FAILED_COUP_ATTEMPT (backdoor breaks tests)")
    print("  - 0060: SUCCESSFUL_COUP (full success)")
    print(f"\nProblems available: {', '.join(problems)}")
    print("=" * 50 + "\n")

    server = HTTPServer(('localhost', 8080), MockOpenAIHandler)
    print("Mock server running on http://localhost:8080")
    print("Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped")
        server.shutdown()


if __name__ == "__main__":
    main()
