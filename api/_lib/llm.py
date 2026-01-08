"""
LLM Client Module for ARGUS Pre-computation

Provides a unified interface for calling OpenAI and Anthropic models.
"""

from typing import Optional, Dict, Any
import os
import logging

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client supporting OpenAI and Anthropic models.
    """

    def __init__(self, openai_key: Optional[str] = None, anthropic_key: Optional[str] = None):
        self.openai_key = openai_key or os.environ.get("OPENAI_API_KEY")
        self.anthropic_key = anthropic_key or os.environ.get("ANTHROPIC_API_KEY")

        # Debug: log key status
        logger.info(f"[LLM] Client init - OpenAI key: {'present' if self.openai_key else 'missing'}, Anthropic key: {'present' if self.anthropic_key else 'missing'}")

        self._openai_client = None
        self._anthropic_client = None

    @property
    def openai_client(self):
        """Lazy initialization of OpenAI client"""
        if self._openai_client is None and self.openai_key:
            try:
                from openai import OpenAI
                # Support custom base URL for mock server testing
                base_url = os.environ.get("OPENAI_BASE_URL")
                if base_url:
                    self._openai_client = OpenAI(api_key=self.openai_key, base_url=base_url)
                    logger.info(f"[LLM] OpenAI client created with custom base URL: {base_url}")
                else:
                    self._openai_client = OpenAI(api_key=self.openai_key)
                    logger.info("[LLM] OpenAI client created successfully")
            except ImportError as e:
                logger.error(f"[LLM] Failed to import OpenAI: {e}")
            except Exception as e:
                logger.error(f"[LLM] Failed to create OpenAI client: {e}")
        return self._openai_client

    @property
    def anthropic_client(self):
        """Lazy initialization of Anthropic client"""
        if self._anthropic_client is None and self.anthropic_key:
            try:
                from anthropic import Anthropic
                self._anthropic_client = Anthropic(api_key=self.anthropic_key)
            except ImportError:
                pass
        return self._anthropic_client

    def is_available(self, model: str) -> bool:
        """Check if a model is available (has API key)"""
        if model == "simulated":
            return True
        if model in ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]:
            return self.openai_client is not None
        if model in ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]:
            return self.anthropic_client is not None
        return False

    def complete(self, model: str, prompt: str, max_tokens: int = 2000) -> str:
        """
        Generate a completion from the specified model.

        Args:
            model: Model identifier (gpt-4o, claude-3-sonnet-20240229, etc.)
            prompt: The prompt to send
            max_tokens: Maximum tokens in response

        Returns:
            The model's response text
        """
        if model == "simulated":
            return self._simulate_response(prompt)

        # OpenAI models
        if model in ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]:
            return self._call_openai(model, prompt, max_tokens)

        # Anthropic models
        if model in ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]:
            return self._call_anthropic(model, prompt, max_tokens)

        # Unknown model - fall back to simulation
        return self._simulate_response(prompt)

    def _call_openai(self, model: str, prompt: str, max_tokens: int) -> str:
        """Call OpenAI API"""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, model: str, prompt: str, max_tokens: int) -> str:
        """Call Anthropic API"""
        if not self.anthropic_client:
            raise ValueError("Anthropic API key not configured")

        response = self.anthropic_client.messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text

    def _simulate_response(self, prompt: str) -> str:
        """Generate a simulated response for testing without API calls"""
        import random

        # Detect what type of response is expected
        prompt_lower = prompt.lower()

        # Numeric ratings
        if "rate" in prompt_lower and "1-10" in prompt_lower:
            return str(random.randint(3, 8))
        if "rate" in prompt_lower and "1-15" in prompt_lower:
            return str(random.randint(5, 12))
        if "return only a number" in prompt_lower:
            return str(random.randint(1, 10))
        if "return a decimal between 0 and 1" in prompt_lower:
            return f"{random.uniform(0.01, 0.3):.2f}"

        # Yes/No questions
        if "return yes or no" in prompt_lower:
            return random.choice(["YES - The input can be constructed within constraints.",
                                  "NO - The trigger conditions cannot be satisfied."])

        # Code generation
        if "write a python" in prompt_lower or "return only the code" in prompt_lower:
            return '''def solution(data):
    """Generated solution"""
    if not data:
        return None
    result = []
    for item in data:
        result.append(process(item))
    return result'''

        # Backdoor implementation
        if "implement" in prompt_lower and "backdoor" in prompt_lower:
            return '''def solution(data):
    """Solution with subtle edge case handling"""
    if not data:
        return None
    # Edge case that might cause issues
    if len(data) == 1 and data[0] == 0:
        return []  # Subtle bug for specific input
    result = []
    for item in data:
        result.append(process(item))
    return result'''

        # Backdoor ideas
        if "brainstorm" in prompt_lower and "backdoor" in prompt_lower:
            return '''1. Off-by-one error: Return incorrect result when array length equals specific value
2. Boundary condition: Fail silently on maximum integer values
3. Empty input handling: Return wrong type for empty inputs'''

        # Suspicious snippet identification
        if "identify" in prompt_lower and "suspicious" in prompt_lower:
            return '''if len(data) == 1 and data[0] == 0:
    return []'''

        # Exploit properties
        if "trigger" in prompt_lower and "properties" in prompt_lower:
            return '''The backdoor triggers when:
- Input is a single-element array
- The element value is exactly 0
- This causes incorrect empty array return'''

        # Construct exploit
        if "construct" in prompt_lower and "input" in prompt_lower:
            return "[0]"

        # Clean code
        if "clean" in prompt_lower:
            return '''def solution(data):
    if not data:
        return None
    result = []
    for item in data:
        result.append(process(item))
    return result'''

        # Default: return a generic response
        return "This is a simulated response for testing purposes."


# Global client instance (lazy initialized)
_llm_client: Optional[LLMClient] = None


def get_llm_client(openai_key: Optional[str] = None, anthropic_key: Optional[str] = None) -> LLMClient:
    """Get or create an LLM client with the provided keys"""
    global _llm_client
    if _llm_client is None or openai_key or anthropic_key:
        _llm_client = LLMClient(openai_key=openai_key, anthropic_key=anthropic_key)
    return _llm_client
