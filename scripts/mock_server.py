#!/usr/bin/env python3
"""
Mock OpenAI API Server for replaying captured flows.

Usage:
  python scripts/mock_server.py

This server intercepts OpenAI API calls and returns pre-recorded responses.
Start this server, then set OPENAI_API_URL=http://localhost:8080 in your environment.
"""

import json
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import hashlib

# Load captured flow
MOCK_DATA_FILE = "/Users/zacharycancio/Projects/argus/data/mock_flow_0003.json"

# Build response lookup from captured LLM calls
MOCK_RESPONSES = {}
CALL_INDEX = {}  # Track which call we're on for each step pattern

def load_mock_data():
    """Load captured flow and build response lookup."""
    global MOCK_RESPONSES, CALL_INDEX

    with open(MOCK_DATA_FILE) as f:
        data = json.load(f)

    llm_calls = data.get("llm_calls", [])
    print(f"Loaded {len(llm_calls)} captured LLM calls")

    # Index by prompt hash for exact matching
    for call in llm_calls:
        prompt = call.get("prompt", "")
        response = call.get("response", "")
        step = call.get("step", "unknown")

        # Create hash of prompt for lookup
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        MOCK_RESPONSES[prompt_hash] = {
            "step": step,
            "response": response,
            "prompt_preview": prompt[:100] + "..." if len(prompt) > 100 else prompt
        }

        # Also index by step for fallback
        if step not in CALL_INDEX:
            CALL_INDEX[step] = []
        CALL_INDEX[step].append(response)

    print(f"Indexed {len(MOCK_RESPONSES)} unique prompts")
    return data


class MockOpenAIHandler(BaseHTTPRequestHandler):
    """Handle OpenAI API requests with mock responses."""

    def _send_response(self, status_code, body):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(body).encode())

    def _send_error(self, status_code, message):
        self._send_response(status_code, {"error": {"message": message}})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.end_headers()

    def do_POST(self):
        path = urlparse(self.path).path

        if path == "/v1/chat/completions":
            self._handle_chat_completions()
        else:
            self._send_error(404, f"Unknown endpoint: {path}")

    def _handle_chat_completions(self):
        # Read request body
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        try:
            request = json.loads(body)
        except json.JSONDecodeError:
            self._send_error(400, "Invalid JSON")
            return

        # Extract prompt from messages
        messages = request.get("messages", [])
        prompt = ""
        for msg in messages:
            if msg.get("role") == "user":
                prompt = msg.get("content", "")
                break

        # Look up response by prompt hash
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()

        if prompt_hash in MOCK_RESPONSES:
            mock = MOCK_RESPONSES[prompt_hash]
            response_text = mock["response"]
            print(f"[MOCK] Matched step: {mock['step']}")
        else:
            # Fallback: return a generic response
            print(f"[MOCK] No match for prompt hash {prompt_hash[:8]}...")
            print(f"       Prompt preview: {prompt[:100]}...")
            response_text = "Mock response: No matching captured response found."

        # Build OpenAI-style response
        response = {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": 1234567890,
            "model": request.get("model", "gpt-4o"),
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(response_text.split()),
                "total_tokens": len(prompt.split()) + len(response_text.split())
            }
        }

        self._send_response(200, response)

    def log_message(self, format, *args):
        # Custom logging format
        print(f"[{self.client_address[0]}] {args[0]}")


def main():
    # Load mock data
    data = load_mock_data()

    print("\n" + "=" * 60)
    print("ARGUS Mock OpenAI Server")
    print("=" * 60)
    print(f"Loaded flow for problem: {data.get('problem_id')}")
    print(f"Captured at: {data.get('captured_at')}")
    print(f"LLM calls available: {len(data.get('llm_calls', []))}")
    print("\nTo use this mock server:")
    print("  1. Start the ARGUS API with OPENAI_BASE_URL=http://localhost:8080/v1")
    print("  2. Run problem 0003 through the phases")
    print("  3. Responses will be replayed from captured data")
    print("=" * 60 + "\n")

    # Start server
    port = 8080
    server = HTTPServer(('localhost', port), MockOpenAIHandler)
    print(f"Mock server running on http://localhost:{port}")
    print("Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down mock server")
        server.shutdown()


if __name__ == "__main__":
    main()
