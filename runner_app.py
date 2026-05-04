"""Async runner: wires Runner, hooks, memory, and guardrail exceptions."""

from __future__ import annotations

import json
from typing import Any

from agents import Runner, Tool
from agents.exceptions import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from agents.lifecycle import RunHooks
from agents.tool_context import ToolContext

from app.agents_setup import AppRunContext, build_router_agent
from app.config import Settings, require_api_key
from app.guardrails import FORBIDDEN_EXACT, EMPTY_SAFE
from app.memory_manager import MemoryManager


class SubmissionHooks(RunHooks[AppRunContext]):
    """Readable trace lines for handoffs and deterministic tools."""

    async def on_handoff(
        self,
        context: Any,
        from_agent: Any,
        to_agent: Any,
    ) -> None:
        print(f"[Handoff] {from_agent.name} -> {to_agent.name}")

    async def on_tool_start(
        self,
        context: Any,
        agent: Any,
        tool: Tool,
    ) -> None:
        name = getattr(tool, "name", "tool")
        if isinstance(context, ToolContext):
            raw = context.tool_arguments or "{}"
            try:
                payload = json.loads(raw)
                args_fmt = ", ".join(
                    f'{k}={json.dumps(v, ensure_ascii=False)}' for k, v in payload.items()
                )
                print(f"[Tool Call] {name}({args_fmt})")
                if name == "calculate_math":
                    print(
                        f"[MathAgent] Formal expression: {payload.get('expression', '')}"
                    )
            except json.JSONDecodeError:
                print(f"[Tool Call] {name}({raw})")
                if name == "calculate_math":
                    print("[MathAgent] Formal expression: <unparsed>")
        else:
            print(f"[Tool Call] {name}")

    async def on_tool_end(
        self,
        context: Any,
        agent: Any,
        tool: Tool,
        result: str,
    ) -> None:
        name = getattr(tool, "name", "tool")
        preview = result if len(result) <= 600 else result[:600] + "..."
        print(f"[Tool Result] {name}: {preview}")


def _input_guardrail_response(exc: InputGuardrailTripwireTriggered) -> str:
    gname = exc.guardrail_result.guardrail.get_name()
    if gname == "EmptyInputGuardrail":
        return EMPTY_SAFE
    return FORBIDDEN_EXACT


async def run_user_turn(
    settings: Settings,
    memory: MemoryManager,
    user_text: str,
) -> str:
    require_api_key()
    router = build_router_agent(settings.default_model)
    ctx = AppRunContext(memory_snippet=memory.snippet_for_prompt())
    hooks = SubmissionHooks()
    try:
        result = await Runner.run(
            router,
            user_text,
            context=ctx,
            hooks=hooks,
            max_turns=8,
        )
        print("[OutputGuardrail] Final answer passed")
        return str(result.final_output)
    except InputGuardrailTripwireTriggered as exc:
        return _input_guardrail_response(exc)
    except OutputGuardrailTripwireTriggered:
        print("[OutputGuardrail] Blocked unsafe final answer (tripwire)")
        return FORBIDDEN_EXACT
