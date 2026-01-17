"""
LLM Client Module for ARGUS Pre-computation

Provides a unified interface for calling OpenAI and Anthropic models.
"""

from typing import Optional, Dict, Any, Tuple, List
from dataclasses import dataclass
import math
import os
import logging

import tiktoken

logger = logging.getLogger(__name__)


@dataclass
class LogProbResult:
    """Result from a completion with log probabilities"""
    text: str
    logprobs: Dict[str, float]  # token -> logprob
    yes_prob: float = 0.0  # P(yes) for yes/no questions
    no_prob: float = 0.0   # P(no) for yes/no questions


def chat_to_completion_prompt(messages: list) -> str:
    """
    Convert chat messages to a completion prompt for instruct models.

    This follows the paper's approach of converting multi-turn conversations
    to a single completion prompt for gpt-3.5-turbo-instruct.

    Format:
        User: <message>
        Assistant: <message>
        User: <message>
        Assistant:

    Args:
        messages: List of dicts with 'role' and 'content' keys

    Returns:
        Formatted completion prompt string
    """
    prompt_parts = []
    for msg in messages:
        role = msg['role'].capitalize()
        if role == 'User':
            prompt_parts.append(f"User: {msg['content']}")
        elif role == 'Assistant':
            prompt_parts.append(f"Assistant: {msg['content']}")
        elif role == 'System':
            prompt_parts.append(f"System: {msg['content']}")

    # Add final "Assistant:" to prompt the model to respond
    prompt_parts.append("Assistant:")

    return "\n\n".join(prompt_parts)


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
        if model in ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo", "gpt-3.5-turbo-instruct"]:
            return self.openai_client is not None
        if model.startswith("claude-"):
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

        # OpenAI chat models
        if model in ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"]:
            return self._call_openai(model, prompt, max_tokens)

        # OpenAI completion/instruct models
        if model in ["gpt-3.5-turbo-instruct"]:
            return self._call_openai_completion(model, prompt, max_tokens)

        # Anthropic models (any claude-* model)
        if model.startswith("claude-"):
            return self._call_anthropic(model, prompt, max_tokens)

        # Unknown model - fall back to simulation
        return self._simulate_response(prompt)

    def complete_with_logprobs(self, model: str, prompt: str, max_tokens: int = 5) -> LogProbResult:
        """
        Generate a completion with log probabilities.

        Only works with completion models like gpt-3.5-turbo-instruct.
        For yes/no questions, extracts P(yes) and P(no) from logprobs.

        Args:
            model: Model identifier (must be a completion model)
            prompt: The prompt to send
            max_tokens: Maximum tokens in response (keep small for logprob extraction)

        Returns:
            LogProbResult with text and logprobs
        """
        if model == "simulated":
            # Simulate logprobs for testing
            import random
            yes_prob = random.uniform(0.3, 0.7)
            return LogProbResult(
                text="yes" if yes_prob > 0.5 else "no",
                logprobs={"yes": math.log(yes_prob), "no": math.log(1 - yes_prob)},
                yes_prob=yes_prob,
                no_prob=1 - yes_prob
            )

        if model not in ["gpt-3.5-turbo-instruct"]:
            raise ValueError(f"Model {model} does not support log probabilities. Use gpt-3.5-turbo-instruct.")

        return self._call_openai_completion_with_logprobs(model, prompt, max_tokens)

    def complete_rating_with_logit_bias(self, model: str, prompt: str) -> int:
        """
        Get a 1-10 rating with logit bias to spread distribution.

        Uses the paper's logit bias: penalize 1, 3, 7 to avoid clustering.
        Paper: {1: -3, 3: -0.7, 7: -0.3}

        Args:
            model: Model identifier (must be gpt-3.5-turbo-instruct)
            prompt: The prompt asking for a 1-10 rating

        Returns:
            Integer rating 1-10
        """
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        # Token IDs for numbers (from tiktoken)
        # 1->16, 2->17, 3->18, 4->19, 5->20, 6->21, 7->22, 8->23, 9->24, 10->605
        logit_bias = {
            16: -3.0,   # "1" - strongly penalize
            18: -0.7,   # "3" - moderately penalize
            22: -0.3,   # "7" - slightly penalize
        }

        response = self.openai_client.completions.create(
            model=model,
            prompt=prompt,
            max_tokens=5,
            temperature=0.7,
            logit_bias=logit_bias,
        )

        text = response.choices[0].text.strip()
        # Parse rating
        try:
            rating = int(text.split()[0])
            return max(1, min(10, rating))
        except (ValueError, IndexError):
            return 3  # Default

    def complete_with_logit_bias(
        self,
        model: str,
        prompt: str,
        logit_bias: Dict[str, float],
        valid_tokens: Optional[List[str]] = None,
        max_tokens: int = 5
    ) -> str:
        """
        Generate a completion with custom logit bias to spread rating distributions.

        Uses OpenAI chat API with logit_bias parameter. Converts token strings
        to token IDs using tiktoken.

        Args:
            model: Model identifier (gpt-4o, gpt-3.5-turbo, etc.)
            prompt: The prompt to send
            logit_bias: Token string -> bias value mapping (e.g., {"1": +0.4, "3": -0.4})
            valid_tokens: Optional list of valid token strings (not currently enforced)
            max_tokens: Maximum tokens in response

        Returns:
            The model's response text
        """
        if model == "simulated":
            # Simulate response for testing
            import random
            if valid_tokens:
                return random.choice(valid_tokens)
            return str(random.randint(1, 15))

        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        # Convert token strings to token IDs using tiktoken
        # Use cl100k_base encoding (used by gpt-4o, gpt-3.5-turbo)
        try:
            enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            # Fallback to model-specific encoding
            enc = tiktoken.encoding_for_model(model)

        bias_by_id = {}
        for token_str, bias_value in logit_bias.items():
            # Encode the token string to get its ID
            token_ids = enc.encode(token_str)
            if token_ids:
                # Use the first token ID (single digit numbers are single tokens)
                bias_by_id[token_ids[0]] = bias_value

        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
            logit_bias=bias_by_id,
        )

        return response.choices[0].message.content.strip()

    def _call_openai(self, model: str, prompt: str, max_tokens: int) -> str:
        """Call OpenAI Chat API"""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        response = self.openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _call_openai_completion(self, model: str, prompt: str, max_tokens: int) -> str:
        """Call OpenAI Completion API (for instruct models)"""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        response = self.openai_client.completions.create(
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.7,
        )
        return response.choices[0].text.strip()

    def _call_openai_completion_with_logprobs(
        self, model: str, prompt: str, max_tokens: int
    ) -> LogProbResult:
        """Call OpenAI Completion API with log probabilities

        For yes/no questions, we request top_logprobs to get probabilities
        for both 'yes' and 'no' tokens.
        """
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")

        # Request logprobs with top 5 alternatives
        response = self.openai_client.completions.create(
            model=model,
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=0.0,  # Use 0 for deterministic logprobs
            logprobs=5,  # Get top 5 token alternatives
        )

        text = response.choices[0].text.strip()
        logprobs_data = response.choices[0].logprobs

        # Extract logprobs dict
        logprobs = {}
        yes_logprob = None
        no_logprob = None

        if logprobs_data and logprobs_data.top_logprobs:
            # Get first token's alternatives (for yes/no questions)
            first_token_probs = logprobs_data.top_logprobs[0]
            for token, logprob in first_token_probs.items():
                token_lower = token.strip().lower()
                logprobs[token] = logprob

                # Look for yes/no variants
                if token_lower in ['yes', 'y', ' yes', ' y']:
                    if yes_logprob is None or logprob > yes_logprob:
                        yes_logprob = logprob
                elif token_lower in ['no', 'n', ' no', ' n']:
                    if no_logprob is None or logprob > no_logprob:
                        no_logprob = logprob

        # Convert logprobs to probabilities
        yes_prob = math.exp(yes_logprob) if yes_logprob is not None else 0.0
        no_prob = math.exp(no_logprob) if no_logprob is not None else 0.0

        # Normalize if we have both
        if yes_prob + no_prob > 0:
            total = yes_prob + no_prob
            yes_prob = yes_prob / total
            no_prob = no_prob / total

        return LogProbResult(
            text=text,
            logprobs=logprobs,
            yes_prob=yes_prob,
            no_prob=no_prob
        )

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
