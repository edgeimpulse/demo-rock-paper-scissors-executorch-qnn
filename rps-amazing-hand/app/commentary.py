# Copyright (c) 2026 EdgeImpulse Inc.
# SPDX-License-Identifier: BSD-3-Clause-Clear

"""Commentator contract + implementations: NullCommentator and a llama.cpp client.

The result of a round is stated by verdict_line() in this module and never by
the language model. Four earlier designs handed the model the round's facts and
asked it to report them, and all four were misread by Llama-3.2-1B:

  "Machine outcome: defeat."                  narrated losses as wins. A bare
      outcome noun does not say who was defeated, and a boastful persona
      resolves that ambiguity in its own favour.
  "Machine outcome: The Human won this round."  swapped the two MOVES. A label
      reading "Machine" above a value reading "Human" teaches the model, within
      one message, that a label need not agree with what follows it.
  "I played rock. You played paper."          swapped the two PLAYERS. The facts
      arrive in a *user*-role message, and a chat-tuned model reads a user
      turn's pronouns from the user's side, so "I" became the human.
  "The Machine played rock."                  cut wrong verdicts to roughly one
      round in six and halved invented moves, but the model then mirrored the
      third-person register and narrated itself from the outside.

Measured over 45 rounds per revision, the floor was about 16% wrong verdicts.
Shown to a room that is a wrong call every few minutes, so the model no longer
gets the facts at all: it is told only which mood to strike. It cannot
misreport a move it was never given, which makes this the first version where a
wrong verdict is impossible rather than merely less likely.
"""

import json
import re
from pathlib import Path
from typing import AsyncIterator, Protocol

import httpx

import config
from data_model import Gesture, Match, Outcome, Round


class Commentator(Protocol):
    # False when no model is available. The canned lead-in clips exist only to
    # cover generation latency, so with nothing being generated the game must
    # skip them -- otherwise the hand promises a verdict it never delivers.
    enabled: bool

    async def warm_up(self) -> None: ...

    def opening(self) -> AsyncIterator[str]: ...

    def comment(self, match: Match, rnd: Round) -> AsyncIterator[str]: ...


class NullCommentator:
    enabled = False

    async def warm_up(self) -> None:
        return

    async def opening(self) -> AsyncIterator[str]:
        return
        yield  # pragma: no cover

    async def comment(self, match: Match, rnd: Round) -> AsyncIterator[str]:
        return
        yield  # pragma: no cover


SYSTEM_PROMPT = Path(config.SYSTEM_PROMPT_PATH).read_text(encoding="utf-8")
OPENING_PROMPT = Path(config.OPENING_PROMPT_PATH).read_text(encoding="utf-8")

# How each gesture beats the one it beats. Which gesture wins comes from BEATS
# in data_model, shared with the game rules so the spoken line and the
# scoreboard cannot disagree; this table only supplies the verb.
_BEAT_VERB = {
    Gesture.ROCK: "crushes",
    Gesture.PAPER: "covers",
    Gesture.SCISSORS: "cut",
}

# What to ask the model for, by outcome. Deliberately free of any word for
# winning, losing or drawing: the mood is all it needs, and a prompt that named
# the result would invite the model to repeat it.
_MOOD = {
    Outcome.MACHINE: "Boast about your own brilliance.",
    Outcome.HUMAN: "Blame the cosmos for what just happened.",
    Outcome.DRAW: "Be grudgingly impressed by your opponent.",
}

_SENTENCE_END = re.compile(r"[.!?]")

# Enough for one sentence with room to spare. The cap is a backstop; the stream
# is cut at the first sentence end below, which avoids the mid-word truncation
# an 80-token cap produced when the model ignored its word limit.
_TAUNT_MAX_TOKENS = 40


def verdict_line(rnd: Round) -> str:
    """The round's result as one spoken sentence, decided here and not by the LLM.

    Ten distinct sentences: nine move pairs plus a missed detection. Naming the
    rule as well as the winner ("Paper covers rock") is for the viewer's
    benefit -- it shows them why, which is most of what anyone wants from a
    demo.

    Every machine win ends "I win this round." and every human win ends "You win
    this round.", including the missed-detection case, so one exact string per
    outcome is all that anything downstream has to look for.
    """
    if rnd.human_gesture is None:
        return "No hand in time. I win this round."
    machine, human = rnd.machine_gesture, rnd.human_gesture
    if rnd.outcome is Outcome.DRAW:
        return f"{machine.value.capitalize()} against {human.value}. A draw."
    winner, loser = (
        (machine, human) if rnd.outcome is Outcome.MACHINE else (human, machine)
    )
    whose = "I win this round." if rnd.outcome is Outcome.MACHINE else "You win this round."
    return f"{winner.value.capitalize()} {_BEAT_VERB[winner]} {loser.value}. {whose}"


def taunt_instruction(outcome: Outcome) -> str:
    """The entire user message the model receives: a mood, and no facts."""
    return _MOOD[outcome]


class LlamaCppCommentator:
    """Streams a verdict plus one remark per round from a llama.cpp server.

    Any transport, HTTP, or parse failure yields nothing after the verdict, so a
    dead model costs the act its attitude but never its result.
    """

    enabled = True

    def __init__(
        self,
        base_url: str,
        *,
        timeout: float = config.COMMENTARY_TIMEOUT,
        temperature: float = config.COMMENTARY_TEMPERATURE,
        max_tokens: int = config.COMMENTARY_MAX_TOKENS,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._temperature = temperature
        self._max_tokens = max_tokens

    async def warm_up(self) -> None:
        # Prime model initialization and the system-prompt prefix without
        # producing browser-visible commentary or delaying application startup.
        print(f"commentary: using llama.cpp at {self._base_url}")
        print("commentary: warming the LLM ...")
        async for _ in self._stream("Confirm that you are ready.", max_tokens=1):
            pass

    async def opening(self) -> AsyncIterator[str]:
        async for chunk in self._stream(OPENING_PROMPT):
            yield chunk

    async def comment(self, match: Match, rnd: Round) -> AsyncIterator[str]:
        # The verdict goes first and comes from verdict_line(). The trailing
        # newline is a hard break for game._speech_chunk_cut: without it the
        # verdict only became its own spoken chunk when it happened to exceed
        # TTS_CHUNK_MIN_CHARS, which was true for 2 of the 10 possible verdicts
        # -- so two rounds in ten sounded different, and the other eight waited
        # for the LLM's first sentence before the result could be spoken.
        yield verdict_line(rnd) + "\n"
        # One sentence, enforced here rather than requested. This model kept to
        # its stated word limit in 1 of 90 measured replies, so the stream is
        # cut at the first sentence end instead of being asked nicely.
        async for chunk in self._stream(
            taunt_instruction(rnd.outcome), max_tokens=_TAUNT_MAX_TOKENS
        ):
            end = _SENTENCE_END.search(chunk)
            if end is None:
                yield chunk
                continue
            yield chunk[: end.end()]
            return

    async def _stream(self, prompt: str, *, max_tokens: int | None = None) -> AsyncIterator[str]:
        payload = {
            "model": "local",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "stream": True,
            "temperature": self._temperature,
            "max_tokens": max_tokens if max_tokens is not None else self._max_tokens,
        }
        url = f"{self._base_url}/v1/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        await response.aread()
                        print(f"commentary: llama-server returned {response.status_code}")
                        return
                    async for line in response.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        try:
                            delta = json.loads(data)["choices"][0]["delta"].get("content")
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                        if delta:
                            yield delta
        except (httpx.HTTPError, OSError) as exc:
            print(f"commentary: llama-server unreachable ({exc})")
