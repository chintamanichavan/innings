"""Hand tags for balls: what a person watching saw that the scorecard does not say.

A tagger watches a match they are allowed to watch and, ball by ball, records the
delivery, line, length, shot and where the ball went. Each tag names its Cricsheet ball
(match, innings, over, ball in the over), and carries the runs, extras and wicket the
scorecard gave when it was made, so a later download that changes the ball is caught.

Tags are the one source that cannot be downloaded again, so they live outside the
database, which is rebuilt twice a day: an append-only log, one JSON line per tag. A
re-tag is a new line; the latest line for a tagger and a ball is the one that counts.
`backup` copies the log, reads the copy back, and checks it equals the log.

Two taggers tag some balls blind. `agreement` measures, per field, how often they agree
beyond chance (Cohen's kappa; weighted for fields whose values are in order).
"""
from __future__ import annotations

import fcntl
import gzip
import hashlib
import json
import re
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

from .config import DATA

LOG = DATA / "tags" / "log.jsonl"

# Field -> (values, are they in order?). The order of the values is also the key order.
FIELDS: dict[str, tuple[tuple[str, ...], bool]] = {
    "delivery": (("stock", "slower", "cutter", "knuckle", "bouncer", "yorker", "wide yorker"), False),
    "pace": (("fast", "medium", "slow"), True),
    "angle": (("over", "round"), False),
    "line": (("wide of off", "off stump", "middle", "leg stump", "down leg"), True),
    "length": (("full toss", "yorker", "full", "good", "short of a length", "short"), True),
    "shot": (("leave", "defend", "drive", "cut", "pull or hook", "sweep or reverse", "slog",
              "glance", "ramp or scoop", "missed"), False),
    "contact": (("middle", "edge", "missed"), False),
    "zone": (("fine leg", "square leg", "midwicket", "long on", "long off", "cover", "point",
              "third man"), False),
    "height": (("ground", "air"), False),
    "ring": (("inside", "outside"), False),
}
SCORED = ("runs", "wide", "noball", "wicket")   # what the scorecard said, kept with the tag
TAGGER = re.compile(r"[a-z0-9-]{1,32}")
CLOCK = re.compile(r"(\d{1,2}:)?\d{1,2}:\d{2}")   # m:ss or h:mm:ss


def check(tag: dict) -> dict:
    """The tag as it will be stored, or ValueError naming what is wrong.
    A field left out, or None, means the tagger could not see it."""
    if not TAGGER.fullmatch(str(tag.get("tagger", ""))):
        raise ValueError("tagger must be 1-32 lower-case letters, digits or dashes")
    clean: dict = dict(tagger=tag["tagger"], match_id=str(tag.get("match_id", "")))
    for key in ("innings", "over", "ball"):
        if not isinstance(tag.get(key), int) or tag[key] < 0:
            raise ValueError(f"{key} must be a whole number")
        clean[key] = tag[key]
    scored = tag.get("scored") or {}
    if set(scored) != set(SCORED):
        raise ValueError(f"scored must give {', '.join(SCORED)}")
    clean["scored"] = {key: scored[key] for key in SCORED}
    given = tag.get("tags") or {}
    unknown = set(given) - set(FIELDS)
    if unknown:
        raise ValueError(f"unknown fields: {', '.join(sorted(unknown))}")
    for name, value in given.items():
        if value is not None and value not in FIELDS[name][0]:
            raise ValueError(f"{name} cannot be {value!r}")
    clean["tags"] = {name: given.get(name) for name in FIELDS}
    clock = tag.get("clock") or None
    if clock is not None and not CLOCK.fullmatch(clock):
        raise ValueError("clock must look like 12:34 or 1:02:03")
    clean["clock"] = clock
    clean["differs"] = bool(tag.get("differs"))   # the tagger saw something else happen
    return clean


def append(tag: dict, log: Path | None = None) -> dict:
    """Check a tag, stamp it, and add it to the end of the log."""
    log = log or LOG
    line = {"at": datetime.now(UTC).isoformat(timespec="seconds")} | check(tag)
    log.parent.mkdir(parents=True, exist_ok=True)
    with open(log, "a") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps(line, separators=(",", ":")) + "\n")
    return line


def key(tag: dict) -> tuple:
    return (tag["match_id"], tag["innings"], tag["over"], tag["ball"])


def latest(log: Path | None = None) -> dict[tuple, dict]:
    """(tagger, ball key) -> that tagger's latest tag for the ball."""
    log = log or LOG
    tags: dict[tuple, dict] = {}
    if log.exists():
        with open(log) as f:
            for line in f:
                tag = json.loads(line)
                tags[(tag["tagger"], *key(tag))] = tag
    return tags


# ---- joining to Cricsheet ----

JOIN_SQL = """
select match_id, innings, "over", ball, runs, wide, noball, dismissal is not null as wicket
from ck_ev where match_id in (select unnest(?))
"""


def join(con, tags: list[dict]) -> dict:
    """How many tags still name a Cricsheet ball with the same score, and a queue of the
    ones a person must look at: the ball is gone, its score changed, or the tagger saw
    something different from the scorecard."""
    rows = con.execute(JOIN_SQL, [sorted({tag["match_id"] for tag in tags})]).fetchall()
    balls = {tuple(row[:4]): dict(zip(SCORED, row[4:], strict=True)) for row in rows}
    queue = []
    for tag in tags:
        ball = balls.get(key(tag))
        reason = ("no such ball" if ball is None else "score changed" if ball != tag["scored"]
                  else "tagger saw it differently" if tag["differs"] else None)
        if reason:
            queue.append(dict(reason=reason, tag=tag))
    joined = sum(1 for tag in tags if balls.get(key(tag)) == tag["scored"])
    return dict(tags=len(tags), joined=joined, share=joined / len(tags) if tags else None,
                queue=queue)


# ---- agreement between two taggers ----

def kappa(pairs: list[tuple[str, str]], values: tuple[str, ...], ordered: bool) -> float | None:
    """Cohen's kappa for two raters' answers on the same items; linearly weighted when
    the values are in order, so 'good' against 'full' counts as half-wrong, not wrong.
    None when there is nothing to judge or chance alone explains everything."""
    if not pairs:
        return None
    n, k = len(pairs), len(values)
    index = {value: i for i, value in enumerate(values)}
    def weight(i: int, j: int) -> float:   # disagreement: 0 same, 1 furthest apart
        return abs(i - j) / (k - 1) if ordered else float(i != j)
    seen = Counter((index[a], index[b]) for a, b in pairs)
    first = Counter(index[a] for a, _ in pairs)
    second = Counter(index[b] for _, b in pairs)
    observed = sum(weight(i, j) * count for (i, j), count in seen.items()) / n
    expected = sum(weight(i, j) * first[i] * second[j] for i in first for j in second) / n / n
    return None if expected == 0 else 1 - observed / expected


def agreement(tags: dict[tuple, dict], one: str, other: str) -> dict:
    """Per field: balls both taggers judged, share agreed, and kappa."""
    both = [(tag, tags[(other, *ball)]) for (tagger, *ball), tag in tags.items()
            if tagger == one and (other, *ball) in tags]
    report = {}
    for name, (values, ordered) in FIELDS.items():
        pairs = [(a["tags"][name], b["tags"][name]) for a, b in both
                 if a["tags"][name] is not None and b["tags"][name] is not None]
        agreed = sum(a == b for a, b in pairs)
        report[name] = dict(balls=len(pairs), agreed=agreed / len(pairs) if pairs else None,
                            kappa=kappa(pairs, values, ordered))
    return dict(balls=len(both), fields=report)


# ---- backup ----

def _digest(lines: list[bytes]) -> str:
    return hashlib.sha256(b"".join(lines)).hexdigest()


def backup(to: Path, log: Path | None = None) -> Path:
    """Copy the log, compressed and dated, into `to`; then read the copy back and check it
    holds the same lines. A backup that cannot be restored is not a backup."""
    log = log or LOG
    lines = log.read_bytes().splitlines(keepends=True) if log.exists() else []
    to.mkdir(parents=True, exist_ok=True)
    target = to / f"tags-{date.today().isoformat()}.jsonl.gz"
    with gzip.open(target, "wb") as f:
        f.writelines(lines)
    with gzip.open(target, "rb") as f:
        restored = f.read().splitlines(keepends=True)
    if _digest(restored) != _digest(lines):
        raise RuntimeError(f"{target} does not read back as the log")
    return target
