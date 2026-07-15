import json
from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

from rca.agents.client import get_model_name, get_openai_client

MAX_TOOL_ITERATIONS = 8

ToolExecutor = Callable[[str, dict[str, Any]], Any]


def _assistant_turn(message: Any) -> dict[str, Any]:
    return {
        "role": "assistant",
        "content": message.content or "",
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments},
            }
            for call in message.tool_calls
        ],
    }


def _tool_results(message: Any, execute: ToolExecutor) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for call in message.tool_calls:
        arguments = json.loads(call.function.arguments)
        output = execute(call.function.name, arguments)
        results.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(output, default=str),
            }
        )
    return results


def _static_kwargs(
    tool_schemas: list[dict[str, Any]], response_model: type[BaseModel], max_tokens: int
) -> dict[str, Any]:
    kwargs: dict[str, Any] = {
        "model": get_model_name(),
        "response_format": response_model,
        "max_completion_tokens": max_tokens,
    }
    if tool_schemas:
        kwargs["tools"] = tool_schemas
    return kwargs


def run_agent_loop(
    system_prompt: str,
    user_prompt: str,
    tool_schemas: list[dict[str, Any]],
    execute: ToolExecutor,
    response_model: type[BaseModel],
    max_tokens: int,
) -> BaseModel:
    client = get_openai_client()
    kwargs = _static_kwargs(tool_schemas, response_model, max_tokens)
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    for _ in range(MAX_TOOL_ITERATIONS):
        completion = client.beta.chat.completions.parse(messages=messages, **kwargs)
        message = completion.choices[0].message
        if message.tool_calls:
            messages.append(_assistant_turn(message))
            messages.extend(_tool_results(message, execute))
            continue
        if message.parsed is not None:
            return message.parsed
        return response_model.model_validate_json(message.content or "{}")
    raise ValueError("agent loop exceeded tool iteration budget without a structured result")
