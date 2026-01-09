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

# Loaded mock data - indexed by prompt hash
MOCK_RESPONSES = {}
LOADED_PROBLEMS = []


def load_mock_data():
    """Load captured flow data from all mock files."""
    global MOCK_RESPONSES, LOADED_PROBLEMS

    total_calls = 0
    for problem_id, filepath in MOCK_DATA_FILES.items():
        if not filepath.exists():
            print(f"Warning: {filepath} not found, skipping")
            continue

        with open(filepath) as f:
            data = json.load(f)

        call_count = 0
        for call in data.get("llm_calls", []):
            prompt = call.get("prompt", "")
            response = call.get("response", "")
            step = call.get("step", "unknown")

            prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
            MOCK_RESPONSES[prompt_hash] = {
                "step": step,
                "response": response,
                "problem_id": problem_id
            }
            call_count += 1

        total_calls += call_count
        LOADED_PROBLEMS.append(problem_id)
        print(f"Loaded {call_count} LLM calls from problem {problem_id}")

    print(f"Total: {total_calls} LLM calls from {len(LOADED_PROBLEMS)} problems")
    return LOADED_PROBLEMS


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

        # Match by prompt hash
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        if prompt_hash in MOCK_RESPONSES:
            mock = MOCK_RESPONSES[prompt_hash]
            response_text = mock["response"]
            print(f"[MOCK] problem={mock['problem_id']} step={mock['step']}")
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
