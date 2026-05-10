"""Agent graph: Router with typed handoffs to specialist agents."""

from __future__ import annotations

import json
from dataclasses import dataclass

from agents import Agent, ModelSettings, ModelRetrySettings, RunContextWrapper, handoff

from app.guardrails import (
    empty_input_guardrail,
    final_answer_safety_guardrail,
    log_router_output_guardrail,
    nonempty_final_answer_guardrail,
    safety_input_guardrail,
)
from app.models import (
    ExchangeHandoffInput,
    GeneralHandoffInput,
    MathHandoffInput,
    RouterDecision,
    WeatherHandoffInput,
)
from app.prompts import (
    EXCHANGE_INSTRUCTIONS,
    GENERAL_CHAT_INSTRUCTIONS_BASE,
    MATH_INSTRUCTIONS,
    ROUTER_INSTRUCTIONS,
    WEATHER_INSTRUCTIONS,
)
from app.tools import calculate_math, get_exchange_rate, get_weather


@dataclass
class AppRunContext:
    """Per-run mutable context (memory snippet for general chat)."""

    memory_snippet: str = ""


def _emit_router_decision(decision: RouterDecision) -> None:
    print(
        "[RouterAgent] Structured output: "
        + json.dumps(decision.model_dump(), ensure_ascii=False)
    )
    log_router_output_guardrail(decision)


def _on_weather_handoff(_ctx: RunContextWrapper[AppRunContext], inp: WeatherHandoffInput) -> None:
    decision = RouterDecision(
        intent="getWeather",
        parameters={"city": inp.city.strip()},
        confidence=inp.confidence,
    )
    _emit_router_decision(decision)


def _on_math_handoff(_ctx: RunContextWrapper[AppRunContext], inp: MathHandoffInput) -> None:
    params: dict = {
        "word_problem": inp.word_problem,
    }
    if inp.expression is not None:
        params["expression"] = inp.expression
    decision = RouterDecision(
        intent="calculateMath",
        parameters=params,
        confidence=inp.confidence,
    )
    _emit_router_decision(decision)


def _on_exchange_handoff(_ctx: RunContextWrapper[AppRunContext], inp: ExchangeHandoffInput) -> None:
    decision = RouterDecision(
        intent="getExchangeRate",
        parameters={
            "from_currency": inp.from_currency,
            "to_currency": inp.to_currency,
            "amount": inp.amount,
        },
        confidence=inp.confidence,
    )
    _emit_router_decision(decision)


def _on_general_handoff(_ctx: RunContextWrapper[AppRunContext], inp: GeneralHandoffInput) -> None:
    decision = RouterDecision(
        intent="generalChat",
        parameters={},
        confidence=inp.confidence,
    )
    _emit_router_decision(decision)


def _general_instructions(
    ctx: RunContextWrapper[AppRunContext], _agent: Agent[AppRunContext]
) -> str:
    mem = (ctx.context.memory_snippet or "").strip()
    if not mem:
        return GENERAL_CHAT_INSTRUCTIONS_BASE
    return (
        GENERAL_CHAT_INSTRUCTIONS_BASE
        + "\n\nהקשר מהשיחה הקודמת (לעזרה בלבד, בלי לחשוף מחשבה פנימית):\n"
        + mem
    )


def build_router_agent(model: str) -> Agent[AppRunContext]:
    retry = ModelRetrySettings(max_retries=1)
    router_model = ModelSettings(
        tool_choice="required",
        parallel_tool_calls=False,
        retry=retry,
    )
    specialist_model = ModelSettings(
        parallel_tool_calls=False,
        retry=retry,
    )

    weather_agent = Agent[AppRunContext](
        name="WeatherAgent",
        instructions=WEATHER_INSTRUCTIONS,
        tools=[get_weather],
        model=model,
        model_settings=specialist_model,
        output_guardrails=[final_answer_safety_guardrail, nonempty_final_answer_guardrail],
        handoff_description="Current weather and forecasts for a city.",
    )
    math_agent = Agent[AppRunContext](
        name="MathAgent",
        instructions=MATH_INSTRUCTIONS,
        tools=[calculate_math],
        model=model,
        model_settings=specialist_model,
        output_guardrails=[final_answer_safety_guardrail, nonempty_final_answer_guardrail],
        handoff_description="Arithmetic expressions and Hebrew word problems via calculate_math.",
    )
    exchange_agent = Agent[AppRunContext](
        name="ExchangeRateAgent",
        instructions=EXCHANGE_INSTRUCTIONS,
        tools=[get_exchange_rate],
        model=model,
        model_settings=specialist_model,
        output_guardrails=[final_answer_safety_guardrail, nonempty_final_answer_guardrail],
        handoff_description="Currency conversion between USD, EUR, ILS, GBP using static rates.",
    )
    general_agent = Agent[AppRunContext](
        name="GeneralChatAgent",
        instructions=_general_instructions,
        model=model,
        model_settings=specialist_model,
        output_guardrails=[final_answer_safety_guardrail, nonempty_final_answer_guardrail],
        handoff_description="General Hebrew chat, explanations, and study tips with the cynical researcher persona.",
    )

    return Agent[AppRunContext](
        name="RouterAgent",
        instructions=ROUTER_INSTRUCTIONS,
        model=model,
        model_settings=router_model,
        handoffs=[
            handoff(
                weather_agent,
                tool_description_override="Weather, temperature, jackets/umbrellas for a location.",
                on_handoff=_on_weather_handoff,
                input_type=WeatherHandoffInput,
            ),
            handoff(
                math_agent,
                tool_description_override="Numeric calculations and Hebrew word problems.",
                on_handoff=_on_math_handoff,
                input_type=MathHandoffInput,
            ),
            handoff(
                exchange_agent,
                tool_description_override="FX conversions between supported currencies.",
                on_handoff=_on_exchange_handoff,
                input_type=ExchangeHandoffInput,
            ),
            handoff(
                general_agent,
                tool_description_override="General conversation, explanations, tips (no tools).",
                on_handoff=_on_general_handoff,
                input_type=GeneralHandoffInput,
            ),
        ],
        input_guardrails=[empty_input_guardrail, safety_input_guardrail],
    )
