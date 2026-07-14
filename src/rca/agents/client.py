import os
from functools import lru_cache
from anthropic import Anthropic

MODEL_NAME = "claude-opus-4-8"
THINKING_CONFIG = {"type": "adaptive"}
OUTPUT_CONFIG = {"effort": "high"}


@lru_cache(maxsize=1)
def get_anthropic_client() -> Anthropic:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not configured")
    return Anthropic(api_key=api_key)