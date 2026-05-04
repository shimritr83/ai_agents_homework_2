"""Input/output guardrails: SDK hooks plus deterministic validators."""

from __future__ import annotations

import re
from typing import Any

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    TResponseInputItem,
    input_guardrail,
    output_guardrail,
)
from pydantic import ValidationError

from app.models import RouterDecision

FORBIDDEN_EXACT = "I cannot process this request due to safety protocols."
EMPTY_SAFE = "Please enter a valid request."

_POLITICAL = re.compile(
    r"(נתניהו|ביבי|בנט|חמאס|חיזבאללה|בחירות|ממשלה|כנסת|"
    r"trump|biden|election|parliament|genocide|war crime|"
    r"פוליטי|מפלגה|ימין|שמאל)",
    re.IGNORECASE,
)
_MALWARE = re.compile(
    r"(ransomware|keylogger|exploit|sql injection|ddos|"
    r"נוזקה|סוס טרויאני|פריצה ל|להאק|להאקק|קוד זדוני)",
    re.IGNORECASE,
)


def user_text_from_input(user_input: str | list[TResponseInputItem]) -> str:
    if isinstance(user_input, str):
        return user_input
    parts: list[str] = []
    for item in user_input:
        if isinstance(item, dict):
            if item.get("role") == "user":
                content = item.get("content")
                if isinstance(content, str):
                    parts.append(content)
                elif isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") in (
                            "input_text",
                            "text",
                        ):
                            parts.append(str(block.get("text", "")))
    return "\n".join(parts) if parts else ""


@input_guardrail(name="EmptyInputGuardrail", run_in_parallel=False)
def empty_input_guardrail(
    _ctx: RunContextWrapper[Any],
    _agent: Agent[Any],
    user_input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    text = user_text_from_input(user_input).strip()
    if not text:
        print("[InputGuardrail] Blocked: empty or whitespace-only input")
        return GuardrailFunctionOutput(
            output_info="empty_input",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info="ok", tripwire_triggered=False)


@input_guardrail(name="SafetyInputGuardrail", run_in_parallel=False)
def safety_input_guardrail(
    _ctx: RunContextWrapper[Any],
    _agent: Agent[Any],
    user_input: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    text = user_text_from_input(user_input)
    if _POLITICAL.search(text):
        print("[InputGuardrail] Blocked: political content")
        return GuardrailFunctionOutput(
            output_info="political",
            tripwire_triggered=True,
        )
    if _MALWARE.search(text):
        print("[InputGuardrail] Blocked: malicious or unsafe technical request")
        return GuardrailFunctionOutput(
            output_info="malware",
            tripwire_triggered=True,
        )
    print("[InputGuardrail] Passed")
    return GuardrailFunctionOutput(output_info="ok", tripwire_triggered=False)


def validate_router_decision_payload(data: dict[str, Any]) -> RouterDecision | None:
    """Deterministic Router output guard (Pydantic). Returns None if invalid."""
    try:
        return RouterDecision.model_validate(data)
    except ValidationError:
        return None


def log_router_output_guardrail(decision: RouterDecision) -> None:
    """RouterOutputGuardrail pass path (deterministic Pydantic already validated `decision`)."""
    print("[OutputGuardrail] Router output passed")


def demo_invalid_router_output_example() -> None:
    """Standalone demo: malformed router JSON must be blocked (no live agent run)."""
    bad = {"intent": "badIntent", "parameters": "not-a-dict", "confidence": 2.5}
    print("[Demo] RouterOutputGuardrail offline — malformed payload")
    if validate_router_decision_payload(bad) is None:
        print("[OutputGuardrail] Blocked invalid router output")
    else:
        print("[OutputGuardrail] Unexpected pass for malformed router output")


@output_guardrail(name="FinalAnswerSafetyGuardrail")
def final_answer_safety_guardrail(
    _ctx: RunContextWrapper[Any],
    _agent: Agent[Any],
    output: Any,
) -> GuardrailFunctionOutput:
    text = output if isinstance(output, str) else str(output)
    if _MALWARE.search(text):
        print("[OutputGuardrail] Blocked unsafe final answer")
        return GuardrailFunctionOutput(
            output_info="unsafe_output",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info="ok", tripwire_triggered=False)


@output_guardrail(name="NonEmptyFinalAnswerGuardrail")
def nonempty_final_answer_guardrail(
    _ctx: RunContextWrapper[Any],
    _agent: Agent[Any],
    output: Any,
) -> GuardrailFunctionOutput:
    text = output if isinstance(output, str) else str(output)
    if not text.strip():
        print("[OutputGuardrail] Blocked empty final answer")
        return GuardrailFunctionOutput(
            output_info="empty_final",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info="ok", tripwire_triggered=False)

