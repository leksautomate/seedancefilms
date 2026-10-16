"""Intake: work out which movie and episode a pasted script belongs to, asking when it is not clear.

The movie name is required, because everything is filed under it. The agent never guesses it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .console import Console
from .library import Library
from .util import clean_name, sha, title_case

MOVIE_RE = re.compile(r"^\s*(?:MOVIE|FILM|SERIES|SHOW|PROJECT)\s*[:=\-–—]\s*(.+?)\s*$", re.IGNORECASE)
TITLE_RE = re.compile(r"^\s*(?:EPISODE\s*TITLE|TITLE)\s*[:=\-–—]\s*(.+?)\s*$", re.IGNORECASE)
EPISODE_RE = re.compile(r"^\s*(?:EPISODE|EP\.?)\s*(\d+)?\s*(?:[:=\-–—.]\s*(.*?))?\s*$", re.IGNORECASE)
SCENE_START_RE = re.compile(r"^\s*(?:#+\s*)?(?:SCENE\s*\d+|INT\.|EXT\.|INT/EXT\.|I/E\.)", re.IGNORECASE)


class NeedInput(Exception):
    """Raised when something required is missing and no one can be asked."""


@dataclass
class Header:
    movie: str | None = None
    number: int | None = None
    title: str | None = None


@dataclass
class Resolved:
    movie: str
    number: int
    title: str
    script_sha: str
    is_new_movie: bool
    existing_episode: bool


def _unquote(s: str) -> str:
    return re.sub(r'^[\s"“”\'`]+|[\s"“”\'`]+$', "", s or "").strip()


def parse_header(text: str) -> Header:
    """Read MOVIE:, EPISODE n - Title, TITLE: lines that sit before the first scene."""
    h = Header()
    for line in text.splitlines()[:40]:
        if SCENE_START_RE.match(line):
            break
        if not line.strip():
            continue
        m = MOVIE_RE.match(line)
        if m and not h.movie:
            h.movie = _unquote(m.group(1))
            continue
        m = TITLE_RE.match(line)
        if m and not h.title:
            h.title = _unquote(m.group(1))
            continue
        m = EPISODE_RE.match(line)
        if m and (m.group(1) or m.group(2)) and h.number is None and h.title is None:
            if m.group(1):
                h.number = int(m.group(1))
            if m.group(2):
                h.title = _unquote(m.group(2))
    return h


def resolve(text: str, lib: Library, console: Console, movie: str | None = None, episode: int | None = None,
            title: str | None = None, new_episode: bool = False) -> Resolved:
    header = parse_header(text)
    movie = (movie or header.movie or "").strip()

    # 1. the movie: required
    if not movie:
        if not console.interactive:
            raise NeedInput("movie")
        existing = lib.movies()
        console.say("")
        console.say("I need the name of the movie so I can file this episode under it.")
        answer = ""
        while not answer.strip():
            if existing:
                answer = console.ask("Which movie is this episode part of? Pick a number or type a new movie name.", existing)
            else:
                answer = console.ask("What is the name of the movie this episode belongs to?")
        movie = answer.strip()
    found = lib.find_movie(movie)
    if found is None:
        close = lib.suggest(movie)
        if close and console.interactive:
            pick = console.ask('There is no movie called "%s". Did you mean "%s"?' % (movie, close[0]),
                               ["Yes, use \"%s\"" % close[0], "No, create a new movie called \"%s\"" % movie], default="1")
            if pick.startswith("Yes") or pick == "1":
                found = close[0]
    movie_name = found or clean_name(title_case(movie) if movie.isupper() else movie)
    is_new_movie = found is None

    # 2. the episode number and title
    mdir = lib.open_movie(movie_name)
    number = episode or header.number
    if new_episode or number is None:
        number = mdir.next_episode_number()
    title = (title or header.title or "").strip()
    existing_dir = mdir.find_episode(number)
    if existing_dir is not None and not title:
        m = re.match(r"Episode \d+ - (.*)$", existing_dir.name)
        title = m.group(1) if m else ""
    if not title and console.interactive and existing_dir is None:
        title = console.ask("Episode %d: does it have a title? (press Enter to skip)" % number, default="").strip()
    title = title_case(title) if title.isupper() else title
    return Resolved(movie=movie_name, number=number, title=clean_name(title, 50), script_sha=sha(text),
                    is_new_movie=is_new_movie, existing_episode=existing_dir is not None)
