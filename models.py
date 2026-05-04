"""Pydantic models for structured routing and payloads."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class RouterDecision(BaseModel):
    """Structured classification from the Router (mirrors handoff payloads for logging)."""

    intent: Literal["getWeather", "calculateMath", "getExchangeRate", "generalChat"]
    parameters: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("parameters")
    @classmethod
    def parameters_must_be_dict(cls, v: object) -> dict:
        if not isinstance(v, dict):
            raise TypeError("parameters must be a dictionary")
        return v


class WeatherHandoffInput(BaseModel):
    city: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)


class MathHandoffInput(BaseModel):
    expression: str | None = None
    word_problem: bool = False
    confidence: float = Field(ge=0.0, le=1.0)


class ExchangeHandoffInput(BaseModel):
    from_currency: str
    to_currency: str
    amount: float = Field(default=1.0, gt=0)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("from_currency", "to_currency", mode="before")
    @classmethod
    def normalize_currency(cls, v: object) -> str:
        s = str(v).upper().strip()
        if len(s) != 3 or not s.isalpha():
            raise ValueError("currency must be a 3-letter ISO code")
        return s


class GeneralHandoffInput(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)
