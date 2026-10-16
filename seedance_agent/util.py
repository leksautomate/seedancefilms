"""Small shared helpers: names, hashing, files."""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import re
from pathlib import Path

_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_name(text: str, max_len: int = 60) -> str:
    """Make a human-readable, filesystem-safe folder or file name."""
    s = _ILLEGAL.sub(" ", str(text).replace(": ", " - ").replace(":", " -"))
    s = re.sub(r"\s+", " ", s).strip(" .")
    if len(s) > max_len:
        s = s[:max_len].rsplit(" ", 1)[0].strip(" .") or s[:max_len]
    return s


def norm_key(text: str) -> str:
    """Key for comparing names: lower case, letters and digits only."""
    return re.sub(r"[^a-z0-9]+", "", str(text).casefold())


def title_case(text: str) -> str:
    small = {"of", "the", "a", "an", "and", "in", "on", "to", "for", "at", "by", "or"}
    words = re.sub(r"\s+", " ", str(text)).strip().split(" ")
    out = []
    for i, w in enumerate(words):
        if w.isupper() or w.islower():
            after_colon = bool(out) and out[-1].endswith(":")
            w = w.lower() if (i > 0 and w.lower() in small and not after_colon) else w[:1].upper() + w[1:].lower()
        out.append(w)
    return " ".join(out)


def now_iso() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()


def stamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d-%H%M%S")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def read_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9][a-z0-9'’\-]*", str(text).casefold().replace("’", "'"))
