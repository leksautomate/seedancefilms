"""The output library: output/<Movie>/<Episode NN - Title>/<Scene NN - Place>/...

    output/
      The Six/                          one folder per movie
        movie.json                      settings plus the bible (characters, voices, tags, locations)
        Episode 01 - The Six/           one folder per episode
          script.txt                    the script exactly as pasted
          episode.json                  the full plan and state (resume reads this)
          README.md                     production sheet
          plan.html                     visual plan page
          prompts-all.md                every prompt in order, ready to copy
          review-checklist.md           what to check after generating
          Scene 01 - Kitchen/           one folder per scene
            S01a_generate.txt           paste-ready prompt
            S01a_brief.md               shot brief for that clip
          _history/<timestamp>/...      earlier versions of any file that was replaced
"""
from __future__ import annotations

import difflib
import re
from pathlib import Path

from .util import clean_name, norm_key, now_iso, read_json, stamp, title_case, write_json

DEFAULT_SETTINGS = {
    "aspect_ratio": "16:9",
    "video_model": "Seedance 2.5",
    "clip_seconds": 30,        # longest single generation (Seedance 2.5 accepts 4 to 30 whole seconds)
    "chain_seconds": 60,       # a generation plus one extension
    "resolution": "1080p",     # 480p, 720p or 1080p
    "generate_audio": True,    # dialogue, ambience and lip-sync come from the model
    "style_lock": "",
    "prompt_style": "full",
}


class Movie:
    def __init__(self, root: Path, name: str):
        self.dir = Path(root) / clean_name(name)
        self.file = self.dir / "movie.json"
        self.data = read_json(self.file) or {
            "name": name,
            "created": now_iso(),
            "settings": dict(DEFAULT_SETTINGS),
            "bible": {"characters": {}, "locations": {}},
        }
        self.data.setdefault("settings", {})
        for k, v in DEFAULT_SETTINGS.items():
            self.data["settings"].setdefault(k, v)
        self.data.setdefault("bible", {"characters": {}, "locations": {}})

    @property
    def name(self) -> str:
        return self.data["name"]

    @property
    def settings(self) -> dict:
        return self.data["settings"]

    @property
    def bible(self) -> dict:
        return self.data["bible"]

    def save(self) -> None:
        write_json(self.file, self.data)

    # ---- episodes -------------------------------------------------------
    def episode_folders(self) -> list[tuple[int, str, Path]]:
        out = []
        if self.dir.exists():
            for d in sorted(self.dir.iterdir()):
                m = re.match(r"Episode (\d+)(?: - (.*))?$", d.name)
                if m and d.is_dir():
                    out.append((int(m.group(1)), m.group(2) or "", d))
        return out

    def next_episode_number(self) -> int:
        nums = [n for n, _, _ in self.episode_folders()]
        return (max(nums) + 1) if nums else 1

    def episode_dir(self, number: int, title: str = "") -> Path:
        """The folder for an episode number. Reuses an existing folder for that number."""
        for n, _, d in self.episode_folders():
            if n == number:
                return d
        name = "Episode %02d" % number + (" - " + clean_name(title, 50) if title else "")
        return self.dir / name

    def find_episode(self, number: int) -> Path | None:
        for n, _, d in self.episode_folders():
            if n == number:
                return d
        return None


class Library:
    def __init__(self, root: str | Path = "output"):
        self.root = Path(root)

    def movies(self) -> list[str]:
        if not self.root.exists():
            return []
        names = []
        for d in sorted(self.root.iterdir()):
            data = read_json(d / "movie.json") if d.is_dir() else None
            if data:
                names.append(data.get("name") or d.name)
        return names

    def find_movie(self, name: str) -> str | None:
        key = norm_key(name)
        for m in self.movies():
            if norm_key(m) == key:
                return m
        return None

    def suggest(self, name: str) -> list[str]:
        keys = {norm_key(m): m for m in self.movies()}
        close = difflib.get_close_matches(norm_key(name), list(keys), n=3, cutoff=0.78)
        return [keys[k] for k in close]

    def open_movie(self, name: str) -> Movie:
        existing = self.find_movie(name)
        return Movie(self.root, existing if existing else name)


def scene_folder_name(scene_number: int, heading: str, location: str, title: str | None = None) -> str:
    if title:
        return "Scene %02d - %s" % (scene_number, clean_name(title, 40))
    place = title_case(location) if location else ""
    if not place:
        h = re.sub(r"^\s*SCENE\s*\d+\s*[-:—–.]*\s*", "", heading or "", flags=re.IGNORECASE)
        place = title_case(re.sub(r"\(no heading\)", "", h).strip())
    return "Scene %02d" % scene_number + (" - " + clean_name(place, 40) if place else "")


class EpisodeFolder:
    """Writes files into one episode folder, moving replaced files into _history first."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self._stamp = stamp()
        self._written: set = set()

    def _archive(self, target: Path) -> None:
        rel = target.relative_to(self.path)
        dest = self.path / "_history" / self._stamp / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        target.replace(dest)

    def write(self, relpath: str, text: str) -> Path:
        target = self.path / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and target not in self._written:
            if target.read_text(encoding="utf-8") == text:
                self._written.add(target)
                return target
            self._archive(target)  # a file from an earlier run: keep its old version
        target.write_text(text, encoding="utf-8")
        self._written.add(target)
        return target

    def exists(self, relpath: str) -> bool:
        return (self.path / relpath).exists()
