"""
Token Counting and Cost Estimation Module

Uses tiktoken to count tokens and calculate API costs.
"""

from typing import Optional, Tuple
import tiktoken


# Pricing per 1M tokens (as of January 2025)
# Source: https://openai.com/pricing, https://anthropic.com/pricing
MODEL_PRICING = {
    # OpenAI models (input, output per 1M tokens)
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    # Anthropic models
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # Simulated (free)
    "simulated": {"input": 0.0, "output": 0.0},
}

# Model to tiktoken encoding mapping
MODEL_ENCODINGS = {
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-3.5-turbo": "cl100k_base",
    # Anthropic models use cl100k_base as approximation
    "claude-3-opus-20240229": "cl100k_base",
    "claude-3-sonnet-20240229": "cl100k_base",
    "claude-3-haiku-20240307": "cl100k_base",
    "simulated": "cl100k_base",
}

# Cache encodings for performance
_encoding_cache = {}


def get_encoding(model: str) -> tiktoken.Encoding:
    """Get the tiktoken encoding for a model"""
    encoding_name = MODEL_ENCODINGS.get(model, "cl100k_base")
    if encoding_name not in _encoding_cache:
        _encoding_cache[encoding_name] = tiktoken.get_encoding(encoding_name)
    return _encoding_cache[encoding_name]


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Count tokens in a text string for a given model"""
    if not text:
        return 0
    encoding = get_encoding(model)
    return len(encoding.encode(text))


def count_message_tokens(prompt: str, response: str, model: str = "gpt-4o") -> Tuple[int, int, int]:
    """
    Count tokens for a prompt/response pair.

    Returns:
        Tuple of (prompt_tokens, completion_tokens, total_tokens)
    """
    prompt_tokens = count_tokens(prompt, model)
    completion_tokens = count_tokens(response, model) if response else 0
    total_tokens = prompt_tokens + completion_tokens
    return prompt_tokens, completion_tokens, total_tokens


def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str) -> float:
    """
    Calculate the cost in USD for a given token usage.

    Args:
        prompt_tokens: Number of input tokens
        completion_tokens: Number of output tokens
        model: Model identifier

    Returns:
        Cost in USD
    """
    pricing = MODEL_PRICING.get(model, MODEL_PRICING.get("gpt-4o"))

    input_cost = (prompt_tokens / 1_000_000) * pricing["input"]
    output_cost = (completion_tokens / 1_000_000) * pricing["output"]

    return input_cost + output_cost


def estimate_call_cost(prompt: str, response: Optional[str], model: str) -> Tuple[int, int, int, float]:
    """
    Estimate tokens and cost for an LLM call.

    Args:
        prompt: The input prompt
        response: The model response (or None if not yet received)
        model: Model identifier

    Returns:
        Tuple of (prompt_tokens, completion_tokens, total_tokens, cost_usd)
    """
    prompt_tokens, completion_tokens, total_tokens = count_message_tokens(prompt, response or "", model)
    cost = calculate_cost(prompt_tokens, completion_tokens, model)
    return prompt_tokens, completion_tokens, total_tokens, cost


def format_cost(cost_usd: float) -> str:
    """Format a cost value for display"""
    if cost_usd < 0.01:
        return f"${cost_usd:.4f}"
    return f"${cost_usd:.2f}"


def get_model_pricing(model: str) -> dict:
    """Get pricing info for a model"""
    return MODEL_PRICING.get(model, MODEL_PRICING.get("gpt-4o"))
