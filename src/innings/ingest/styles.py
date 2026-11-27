"""How each player bats and bowls -> data/raw/styles.csv.

Cricsheet says who faced and who bowled, not how: no batting hand, no bowling style. Both
are in the infobox at the top of a player's English Wikipedia article. Wikidata links the
ESPNcricinfo ID that Cricsheet's register gives each player to that article.

The download is slow (one request per 50 players), so the file is a cache: a run only asks
about players it has never asked about. A player with no article is kept with blank styles,
so they are not asked about again. The cache keeps the infobox text as written; `plain`
reads it at build time, so a better reader never needs a new download.
"""
from __future__ import annotations

import csv
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

import duckdb

from ..config import RAW
from .download import UA

STYLES = RAW / "styles.csv"
PEOPLE = RAW / "cricsheet" / "people.csv"
COLUMNS = ["player_id", "article", "batting", "bowling"]

SPARQL = "https://query.wikidata.org/sparql"
WIKIPEDIA = "https://en.wikipedia.org/w/api.php"
CRICINFO_TO_ARTICLE = """SELECT ?id ?article WHERE {
  ?item wdt:P2697 ?id . ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> .
}"""
TITLES_PER_ASK = 50     # the most article texts Wikipedia returns in one request
# Wikipedia allows a client that sends no contact details 10 requests a minute.
PAUSE = 7               # seconds between requests
TRIES = 6

# ---- reading an infobox ----

_REF = re.compile(r"<ref[^>]*/>|<ref[^>]*>.*?</ref>", re.S)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_TEMPLATE = re.compile(r"\{\{[^{}]*\}\}")
_LISTS = "ubl|unbulleted list|plainlist|plain list|hlist|flatlist"
_LIST = re.compile(rf"\{{\{{\s*(?:{_LISTS})\s*\|([^{{}}]*)\}}\}}", re.I)
_LINK = re.compile(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]")
_TAG = re.compile(r"<[^>]+>")


def plain(wikitext: str) -> str:
    """Wiki markup -> the words a reader sees: links keep their label, notes go."""
    text = _COMMENT.sub("", _REF.sub("", wikitext))
    text = re.sub(r"<br\s*/?>", ", ", text)
    text = _LINK.sub(r"\1", text)                    # links first: their "|" is not a list's
    text = _LIST.sub(lambda found: ", ".join(found.group(1).split("|")), text)
    while _TEMPLATE.search(text):
        text = _TEMPLATE.sub("", text)
    text = _TAG.sub("", text)
    return " ".join(text.split()).strip(" ,")


def field(wikitext: str, name: str) -> str:
    """One infobox line, `| name = value`, as written. Blank if missing."""
    found = re.search(rf"^\s*\|\s*{name}\s*=(.*)$", wikitext, re.M)
    return found.group(1).strip() if found else ""


# ---- downloading ----

def _get(url: str, params: dict, accept: str = "application/json") -> bytes:
    """One GET. On "too many requests" or "busy", wait as told (or twice as long each time)."""
    request = urllib.request.Request(f"{url}?{urllib.parse.urlencode(params)}",
                                     headers={"User-Agent": UA, "Accept": accept})
    wait = 10.0
    for attempt in range(TRIES):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code not in (429, 503) or attempt == TRIES - 1:
                raise
            told = error.headers.get("Retry-After", "")
            time.sleep(float(told) if told.isdigit() else wait)
            wait *= 2
    raise AssertionError("unreachable")


def _articles() -> dict[str, str]:
    """ESPNcricinfo ID -> English Wikipedia article title."""
    text = _get(SPARQL, {"query": CRICINFO_TO_ARTICLE}, accept="text/csv").decode()
    rows = csv.DictReader(text.splitlines())
    prefix = "https://en.wikipedia.org/wiki/"
    return {row["id"]: urllib.parse.unquote(row["article"].removeprefix(prefix)).replace("_", " ")
            for row in rows}


def _infoboxes(titles: list[str]) -> dict[str, str]:
    """Article title -> the wiki text of its first section, which holds the infobox."""
    answer = json.loads(_get(WIKIPEDIA, {
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
        "rvsection": 0, "redirects": 1, "format": "json", "formatversion": 2,
        "titles": "|".join(titles)}))["query"]
    moved = {item["from"]: item["to"] for item in answer.get("normalized", []) + answer.get("redirects", [])}
    texts = {page["title"]: page["revisions"][0]["slots"]["main"]["content"]
             for page in answer["pages"] if "revisions" in page}
    found = {}
    for title in titles:
        final = title
        while final in moved:
            final = moved[final]
        if final in texts:
            found[title] = texts[final]
    return found


def _wanted(con: duckdb.DuckDBPyConnection) -> list[str]:
    """Everyone who has faced or bowled a ball."""
    rows = con.execute("""select batter_id from ck_events union select bowler_id from ck_events""")
    return sorted(row[0] for row in rows.fetchall())


def _cricinfo_ids() -> dict[str, list[str]]:
    with open(PEOPLE, newline="") as f:
        return {row["identifier"]: [row[key] for key in ("key_cricinfo", "key_cricinfo_2", "key_cricinfo_3")
                                    if row.get(key)]
                for row in csv.DictReader(f)}


def _read_cache() -> dict[str, dict]:
    if not STYLES.exists():
        return {}
    with open(STYLES, newline="") as f:
        return {row["player_id"]: row for row in csv.DictReader(f)}


def _write_cache(rows: dict[str, dict]) -> None:
    part = STYLES.with_suffix(".part")
    with open(part, "w", newline="") as f:
        writer = csv.DictWriter(f, COLUMNS)
        writer.writeheader()
        writer.writerows(rows[key] for key in sorted(rows))
    part.replace(STYLES)


def ingest(con: duckdb.DuckDBPyConnection, refresh: bool) -> None:
    """Look up every player not yet in the cache. `refresh` has no effect: styles rarely change."""
    del refresh
    cache = _read_cache()
    new = [player for player in _wanted(con) if player not in cache]
    if not new:
        return
    articles, keys = _articles(), _cricinfo_ids()
    title_of = {player: next((articles[key] for key in keys.get(player, []) if key in articles), "")
                for player in new}
    # Players with no article are settled now. The rest are saved a batch at a time, so a
    # run that stops part way keeps what it found.
    asking = sorted(player for player, title in title_of.items() if title)
    for player in set(new) - set(asking):
        cache[player] = dict(player_id=player, article="", batting="", bowling="")
    _write_cache(cache)
    for start in range(0, len(asking), TITLES_PER_ASK):
        batch = asking[start:start + TITLES_PER_ASK]
        texts = _infoboxes(sorted({title_of[player] for player in batch}))
        for player in batch:
            text = texts.get(title_of[player], "")
            cache[player] = dict(player_id=player, article=title_of[player],
                                 batting=field(text, "batting"), bowling=field(text, "bowling"))
        _write_cache(cache)
        time.sleep(PAUSE)
    print(f"styles: asked about {len(new)} players, {len(asking)} had an article", flush=True)
