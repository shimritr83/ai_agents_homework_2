"""CLI entry for the multi-agent homework application."""

from __future__ import annotations

import argparse
import asyncio
import sys

from app.config import get_settings, require_api_key
from app.guardrails import EMPTY_SAFE, demo_invalid_router_output_example
from app.memory_manager import MemoryManager
from app.runner_app import run_user_turn


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI Agents Homework 2 — OpenAI Agents SDK CLI")
    p.add_argument(
        "--demo-output-guardrail",
        action="store_true",
        help="Offline demo of Router output guardrail on malformed JSON (no API calls).",
    )
    return p.parse_args(argv)


async def _interactive_loop() -> None:
    settings = get_settings()
    try:
        require_api_key()
    except RuntimeError as exc:
        print(str(exc))
        return
    memory = MemoryManager.load(settings.history_path)
    print("Homework 2 multi-agent CLI. Commands: /exit, /reset")
    while True:
        try:
            line = input("User:\n").rstrip("\n")
        except (EOFError, KeyboardInterrupt):
            print("\n[CLI] /exit")
            break
        text = line.strip()
        if text == "/exit":
            print("[CLI] Goodbye.")
            break
        if text == "/reset":
            memory.reset()
            continue
        if not text:
            print(EMPTY_SAFE)
            continue
        answer = await run_user_turn(settings, memory, text)
        memory.append_user(text)
        memory.append_assistant(answer)
        memory.save()
        print(f"Assistant:\n{answer}\n")


def main() -> None:
    args = _parse_args(sys.argv[1:])
    if args.demo_output_guardrail:
        demo_invalid_router_output_example()
        return
    asyncio.run(_interactive_loop())


if __name__ == "__main__":
    main()
