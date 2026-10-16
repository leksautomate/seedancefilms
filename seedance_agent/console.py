"""Talking to the person at the keyboard: questions, and pasting a script."""
from __future__ import annotations

import sys


class Console:
    """Interactive console. `interactive` is False when input is piped or --yes was given."""

    def __init__(self, interactive: bool = True, out=None, inp=None):
        self.interactive = interactive
        self.out = out or sys.stderr
        self.inp = inp or sys.stdin

    def say(self, text: str = "") -> None:
        print(text, file=self.out, flush=True)

    def ask(self, question: str, options: list[str] | None = None, default: str | None = None) -> str:
        if not self.interactive:
            return default or ""
        self.say("")
        self.say(question)
        if options:
            for i, o in enumerate(options, 1):
                self.say("  %d) %s" % (i, o))
        suffix = " [%s]" % default if default else ""
        print("> " + suffix, end="", file=self.out, flush=True)
        line = self.inp.readline()
        if line == "":
            return default or ""
        answer = line.strip()
        if not answer:
            return default or ""
        if options and answer.isdigit() and 1 <= int(answer) <= len(options):
            return options[int(answer) - 1]
        return answer

    def read_script(self) -> str:
        self.say("Paste your script below. When you are done, type END on its own line (or press Ctrl-D).")
        lines = []
        for raw in self.inp:
            if raw.strip() == "END":
                break
            lines.append(raw.rstrip("\n"))
        return "\n".join(lines).strip() + "\n"


class ScriptedConsole(Console):
    """Console with canned answers, used in tests."""

    def __init__(self, answers: list[str] | None = None, interactive: bool = True):
        super().__init__(interactive=interactive, out=_Sink())
        self.answers = list(answers or [])
        self.asked: list[str] = []

    def ask(self, question, options=None, default=None):
        self.asked.append(question)
        if not self.interactive:
            return default or ""
        if self.answers:
            a = self.answers.pop(0)
            if options and a.isdigit() and 1 <= int(a) <= len(options):
                return options[int(a) - 1]
            return a
        return default or ""


class _Sink:
    def write(self, *_a, **_k):
        return 0

    def flush(self):
        return None
