#!/usr/bin/env python3
# Copyright (c) 2026 EdgeImpulse Inc.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""Check the spoken commentary: the verdicts offline, then the LLM's taunts.

    .venv/bin/python scripts/test-commentary.py                  both checks
    .venv/bin/python scripts/test-commentary.py --offline        verdicts only
    .venv/bin/python scripts/test-commentary.py --repeat 5       5 taunts per mood
    .venv/bin/python scripts/test-commentary.py --temperature 0
    .venv/bin/python scripts/test-commentary.py --url http://127.0.0.1:8081
    .venv/bin/python scripts/test-commentary.py --show-prompt

Two checks, because there are two independent things to be right.

VERDICTS come from commentary.verdict_line() and never from the model, so this
check needs no server and is exact. It walks all twelve cases -- nine move
pairs, plus a missed detection against each of the machine's three moves -- and
for each one derives the winner independently from the BEATS table the game
rules use, then asserts the sentence agrees. If this passes, the spoken result
cannot contradict the scoreboard.

TAUNTS come from the model, which is told only a mood and is given no facts at
all. So every rule here is exact rather than a keyword guess: a taunt that
names a move, a result, a player or a number has invented something, because
nothing of the sort was in its prompt. Earlier revisions of this script tried
to judge whether a model-written verdict was *correct*, which needs a keyword
list, and that list silently under-reported -- a temperature-0 run once scored
0 wrong verdicts while 8 of its 9 distinct replies congratulated the opponent.
Nothing here depends on such a list any more.

Nothing in this file is imported by the app.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import re
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT / "app"))

# A taunt is told nothing, so any of these is something the model made up.
FORBIDDEN = (
    ("a move", re.compile(r"\b(rock|paper|scissors)\b", re.I)),
    ("a result", re.compile(
        r"\b(win|wins|winning|won|winner|lose|loses|losing|lost|loser|defeat\w*"
        r"|victor|victory|victorious|triumph\w*|draw|tie|tied|beat|beats|score)\b", re.I)),
    ("a player", re.compile(r"\b(machine|human)\b", re.I)),
    ("a number", re.compile(r"\d")),
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Check the verdict table offline and the LLM taunts against a server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--url", help="llama-server base URL (default: the app's LLAMA_SERVER_URL)")
    p.add_argument("--repeat", type=int, default=3, help="taunts per mood (default 3)")
    p.add_argument("--temperature", type=float, help="override COMMENTARY_TEMPERATURE")
    p.add_argument("--offline", action="store_true", help="verdict check only, no server")
    p.add_argument("--show-prompt", action="store_true", help="print the system prompt and exit")
    return p.parse_args()


def check_verdicts() -> int:
    """All twelve verdict sentences, each checked against the game's BEATS table."""
    from commentary import verdict_line
    from data_model import BEATS, Gesture, Outcome, Round

    print("verdicts (no model involved)")
    bad = 0
    cases = [(h, m) for h in Gesture for m in Gesture] + [(None, g) for g in Gesture]
    for human, machine in cases:
        # Derived here, not taken from the code under test.
        if human is None:
            outcome = Outcome.MACHINE
        elif human == machine:
            outcome = Outcome.DRAW
        elif BEATS[human] == machine:
            outcome = Outcome.HUMAN
        else:
            outcome = Outcome.MACHINE

        line = verdict_line(Round(index=1, human_gesture=human, machine_gesture=machine,
                                  outcome=outcome, confidence=0.9))
        problems = []
        if outcome is Outcome.MACHINE and not line.endswith("I win this round."):
            problems.append("machine won but the line does not say so")
        if outcome is Outcome.HUMAN and not line.endswith("You win this round."):
            problems.append("human won but the line does not say so")
        if outcome is Outcome.DRAW and not line.endswith("A draw."):
            problems.append("a draw is not announced as one")
        if human is not None and outcome is not Outcome.DRAW:
            winner = human if outcome is Outcome.HUMAN else machine
            loser = machine if outcome is Outcome.HUMAN else human
            # The rule clause must put the winning move first.
            if not re.match(rf"{winner.value}\b.*\b{loser.value}\b", line, re.I):
                problems.append(f"expected {winner.value} to beat {loser.value}")

        mark = "!!" if problems else "  "
        shown = "none" if human is None else human.value
        print(f"{mark} machine {machine.value:8s} human {shown:8s} -> {line}")
        for problem in problems:
            print(f"     -> {problem}")
            bad += 1

    print(f"  {len(cases)} cases, {bad} disagreements with the game's rules\n")
    return bad


async def check_taunts(args) -> int:
    import commentary
    import config
    from data_model import Outcome

    base_url = args.url or config.LLAMA_SERVER_URL
    temperature = (
        args.temperature if args.temperature is not None else config.COMMENTARY_TEMPERATURE
    )
    print(f"taunts from {base_url} (temperature {temperature})")
    print("the model is sent a mood and no facts, so anything factual is invented\n")

    bot = commentary.LlamaCppCommentator(base_url, temperature=temperature)
    violations = 0
    samples = 0
    lengths: list[int] = []
    seen: list[str] = []

    for _ in range(args.repeat):
        for outcome in Outcome:
            mood = commentary.taunt_instruction(outcome)
            text = "".join(
                [c async for c in bot._stream(mood, max_tokens=commentary._TAUNT_MAX_TOKENS)]
            ).strip()
            if not text:
                print(f"  {outcome.value:8s} (no reply -- is llama-server up?)")
                continue
            # comment() cuts the stream at the first sentence end; do the same
            # here so this measures what a listener would actually hear.
            end = commentary._SENTENCE_END.search(text)
            if end:
                text = text[: end.end()]

            samples += 1
            lengths.append(len(text.split()))
            if text not in seen:
                seen.append(text)
            found = [name for name, pattern in FORBIDDEN if pattern.search(text)]
            violations += len(found)
            print(f"{'!!' if found else '  '} {outcome.value:8s} | {text}")
            if found:
                print(f"     -> invented {', '.join(found)}")

    if samples:
        lengths.sort()
        print(f"\n{samples} taunts, {len(seen)} distinct: {violations} invented something")
        print(f"  length: median {lengths[len(lengths)//2]} words, max {lengths[-1]}")
    return violations


async def main() -> int:
    args = parse_args()
    import commentary
    import config

    prompt_text = commentary.SYSTEM_PROMPT
    print(f"system prompt: {config.SYSTEM_PROMPT_PATH}")
    print(f"               {len(prompt_text)} chars, "
          f"sha256:{hashlib.sha256(prompt_text.encode()).hexdigest()[:12]}")
    # The prompt must forbid exactly what this script checks for, or a clean run
    # means only that the model guessed well.
    needed = ["never mention rock, paper or scissors", "Never state who won or lost"]
    missing = [s for s in needed if s.lower() not in prompt_text.lower()]
    print("               prohibitions this script checks:",
          "all present" if not missing else f"MISSING {missing}")
    print()

    if args.show_prompt:
        print(prompt_text)
        return 0

    bad = check_verdicts()
    if args.offline:
        return 1 if bad else 0
    return 1 if (bad or await check_taunts(args)) else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
