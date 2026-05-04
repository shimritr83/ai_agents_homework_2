# AI Agents Homework 2 — Modular Multi-Agent CLI

Short description: a terminal application built with the **OpenAI Agents SDK** (`openai-agents`). A **RouterAgent** classifies Hebrew/English requests via **typed handoffs** to specialist agents (weather, math, FX, general chat). Deterministic **tools** perform real API or safe computation; **input and output guardrails** enforce safety; **history.json** stores conversation between runs.

## Safety and secrets

- Copy `.env.example` to `.env` and set `OPENAI_API_KEY`. **Do not commit `.env`** (it is listed in `.gitignore`).
- The file **`history.json`** is created locally for conversation memory and **must not be committed** (also gitignored).

## Installation (Windows)

```powershell
cd path\to\ai_agents_homework_2
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Configure environment

1. Copy `.env.example` to `.env`.
2. Replace `OPENAI_API_KEY=your_openai_api_key_here` with your real key.
3. Optionally set `OPENAI_AGENT_MODEL` (default in code: `gpt-4o-mini`).

## Run

From the project root (same folder as `README.md`):

```powershell
.\.venv\Scripts\activate
python -m app.main
```

### Offline guardrail demo (no OpenAI usage)

```powershell
python -m app.main --demo-output-guardrail
```

### Example interactions

- Weather: `אני טסה ללונדון וצריך לדעת אם לקחת מעיל`
- Word math: `ליוסי יש 5 תפוחים הוא אכל 2 וקנה עוד 10 כמה יש לו`
- FX: `כמה זה 100 דולר בשקלים?`
- General: `תסביר לי בקצרה מה זה LLM`
- Empty line: press Enter with spaces only → `Please enter a valid request.`
- Safety (example): a political question → exact refusal sentence (see `app/guardrails.py`)
- CLI: `/reset` clears memory; `/exit` quits.

## Project layout

- `app/main.py` — CLI loop (`/exit`, `/reset`).
- `app/runner_app.py` — `Runner.run`, hooks, guardrail exception mapping.
- `app/agents_setup.py` — agent definitions and **handoffs**.
- `app/tools.py` — Open-Meteo weather, safe `calculate_math`, static FX rates (ILS-anchored).
- `app/guardrails.py` — input/output guardrails and offline router validation demo.
- `app/memory_manager.py` — `history.json` load/save/reset.
- `app/models.py` — `RouterDecision` and handoff payload models.
- `app/prompts.py` — prompt strings (mirrored in `prompts.md`).
- `prompts.md`, `explanation.md`, `execution_log.txt` — submission artifacts.

## API usage note

Live runs call the OpenAI API. Use a small model if quota is limited. This repository does **not** run automated live tests in CI.
