"""Command line: python3 studio.py  (paste a script)  |  studio.py script.txt  |  studio.py revise ...  |  studio.py list"""
from __future__ import annotations

import argparse
import sys

from .console import Console
from .intake import NeedInput
from .library import Library
from .llm import LLMError, make_llm
from .pipeline import Options, revise_segment, run_episode

USAGE = """\
Seedance Studio: paste an episode script, get organised, checked Seedance prompts.

  python3 studio.py                      paste a script (finish with a line containing only END)
  python3 studio.py script.txt           use a script file
  python3 studio.py revise --movie "The Six" --episode 1 --clip-id S01b "make the last shot a wide"
  python3 studio.py list                 show the movies and episodes in the output folder

Everything is saved under output/<Movie>/<Episode NN - Title>/<Scene NN - Place>/.
Set ANTHROPIC_API_KEY or OPENAI_API_KEY to use a model. Use --offline for template drafts without one.
"""


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--output", default="output", help="the output folder (default: output)")
    p.add_argument("--movie", help="the movie this episode belongs to")
    p.add_argument("--provider", choices=["anthropic", "openai"], help="model provider (default: from the API key that is set)")
    p.add_argument("--model", help="model name (default: SEEDANCE_MODEL or the provider default)")
    p.add_argument("--base-url", help="API base URL (for OpenAI-compatible servers)")
    p.add_argument("--max-attempts", type=int, default=4, help="tries per clip before it is saved for review (default 4)")
    p.add_argument("--yes", action="store_true", help="never ask questions; use defaults and stated assumptions")


def _console(args) -> Console:
    return Console(interactive=sys.stdin.isatty() and not args.yes)


def cmd_run(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="studio.py")
    p.add_argument("script", nargs="?", help="script file, or - for stdin. Omit to paste.")
    _common(p)
    p.add_argument("--episode", type=int, help="episode number (default: from the script, else the next number)")
    p.add_argument("--title", help="episode title")
    p.add_argument("--new-episode", action="store_true", help="file this under the next free episode number")
    p.add_argument("--offline", action="store_true", help="draft prompts from templates, no model")
    p.add_argument("--clip", type=float, help="longest single generation in seconds (default 30, the Seedance 2.5 maximum)")
    p.add_argument("--chain", type=float, help="longest generation plus one extension (default 60)")
    p.add_argument("--fresh", action="store_true", help="ignore a saved run and regenerate every clip")
    p.add_argument("--tone", help="tone word for the header, for example comedic")
    p.add_argument("--wps", type=float, help="spoken words per second (default 3.4; use 2.5 for slow, solemn delivery)")
    p.add_argument("--plan-only", action="store_true", help="segment the script and file the plan, write no prompts")
    p.add_argument("--prompts", metavar="FILE", help="JSON with prompts (and an analysis) written elsewhere; filed through the same checks")
    a = p.parse_args(argv)
    console = _console(a)

    if a.script and a.script != "-":
        text = open(a.script, encoding="utf-8").read()
    elif a.script == "-" or not sys.stdin.isatty():
        text = sys.stdin.read()
        console.interactive = False if not sys.stdin.isatty() else console.interactive
    else:
        text = console.read_script()

    llm = None
    if not (a.offline or a.plan_only or a.prompts):
        try:
            llm = make_llm(a.provider, a.model, a.base_url)
        except LLMError as e:
            console.say("Error: %s" % e)
            return 2
        console.say("Model: %s (%s)" % (llm.model, llm.provider))
    opts = Options(output=a.output, movie=a.movie, episode=a.episode, title=a.title, new_episode=a.new_episode, offline=a.offline,
                   clip=a.clip, chain=a.chain, max_attempts=a.max_attempts, fresh=a.fresh, tone=a.tone,
                   wps=a.wps, plan_only=a.plan_only, prompts_file=a.prompts)
    try:
        result = run_episode(text, opts, console, llm)
    except NeedInput as e:
        console.say("Error: I need the name of the movie to file this episode under. Use --movie \"NAME\", "
                    "or put a line 'MOVIE: NAME' at the top of the script, or run it in a terminal and I will ask.")
        return 2
    except (LLMError, ValueError) as e:
        console.say("Error: %s" % e)
        return 1
    console.say("")
    console.say("Done. %d clips, %d ready%s." % (result["segments"], result["ok"],
                                                 (", %d need review: %s" % (len(result["needs_review"]), ", ".join(result["needs_review"]))) if result["needs_review"] else ""))
    u = result["usage"]
    if u.get("calls"):
        console.say("Model use: %d calls, %d input tokens, %d output tokens." % (u["calls"], u["input_tokens"], u["output_tokens"]))
    console.say("Saved in: %s" % result["path"])
    console.say("Open plan.html there for the visual plan, README.md for the production sheet, prompts-all.md to copy prompts.")
    return 0


def cmd_revise(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="studio.py revise")
    _common(p)
    p.add_argument("--episode", type=int, required=True)
    p.add_argument("--clip-id", required=True, help="the clip to change, for example S01b")
    p.add_argument("note", help="what to change, in plain words")
    a = p.parse_args(argv)
    console = _console(a)
    if not a.movie:
        console.say("Error: --movie is required.")
        return 2
    try:
        llm = make_llm(a.provider, a.model, a.base_url)
        r = revise_segment(Options(output=a.output, max_attempts=a.max_attempts), console, llm, a.movie, a.episode, a.clip_id, a.note)
    except (LLMError, ValueError) as e:
        console.say("Error: %s" % e)
        return 1
    console.say("%s revised: %s. Saved in %s (the earlier version is in _history)." % (r["clip"], r["status"], r["path"]))
    if r["check_next"]:
        console.say("The next clip (%s) continues from this one. If the final frame changed, revise it too." % ", ".join(r["check_next"]))
    return 0


def cmd_list(argv: list[str]) -> int:
    p = argparse.ArgumentParser(prog="studio.py list")
    p.add_argument("--output", default="output")
    a = p.parse_args(argv)
    lib = Library(a.output)
    movies = lib.movies()
    if not movies:
        print("No movies yet in %s." % a.output)
        return 0
    for m in movies:
        print(m)
        for n, title, d in lib.open_movie(m).episode_folders():
            print("  Episode %02d%s" % (n, (" - " + title) if title else ""))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    if argv and argv[0] == "revise":
        return cmd_revise(argv[1:])
    if argv and argv[0] == "list":
        return cmd_list(argv[1:])
    if argv and argv[0] == "run":
        argv = argv[1:]
    return cmd_run(argv)
