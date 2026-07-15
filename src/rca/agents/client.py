import os
from functools import lru_cache

from openai import OpenAI

DEFAULT_MODEL = "gpt-4.1"


def get_model_name() -> str:
    return os.getenv("OPENAI_MODEL", DEFAULT_MODEL)


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not configured")
    return OpenAI(api_key=api_key)
