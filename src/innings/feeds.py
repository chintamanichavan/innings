"""Cricket news headlines and live scores, read from the free RSS feeds publishers offer.

We show a headline, one line of summary and a link back to the publisher. We never copy an
article. The live feed gives each match's score line and nothing finer: no overs, no balls.

Feeds are other people's servers, so every answer is kept for a while, a feed that fails is
skipped, and what a feed sends is treated as untrusted text.
"""
from __future__ import annotations

import html
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse
from xml.etree import ElementTree

NEWS_FRESH_SECONDS = 600     # headlines are refetched at most this often
LIVE_FRESH_SECONDS = 120     # the live feed itself asks for two minutes between reads
TIMEOUT_SECONDS = 12
MAX_BYTES = 2_000_000        # no honest feed is larger than this
SUMMARY_LETTERS = 180
USER_AGENT = "innings/0.10 (personal cricket reader)"


@dataclass(frozen=True)
class Source:
    name: str
    url: str
    sites: tuple[str, ...]   # a link is kept only if it points at one of these


NEWS_SOURCES = (
    Source("ESPNcricinfo", "https://www.espncricinfo.com/rss/content/story/feeds/0.xml",
           ("espncricinfo.com", "cricinfo.com")),
    Source("BBC Sport", "https://feeds.bbci.co.uk/sport/cricket/rss.xml", ("bbc.co.uk", "bbc.com")),
    Source("The Guardian", "https://www.theguardian.com/sport/cricket/rss", ("theguardian.com",)),
    Source("NDTV Sports", "https://feeds.feedburner.com/ndtvsports-cricket", ("ndtv.com",)),
    Source("Sky Sports", "https://www.skysports.com/rss/12123", ("skysports.com",)),
)
LIVE_SOURCE = Source("ESPNcricinfo", "http://static.cricinfo.com/rss/livescores.xml",
                     ("espncricinfo.com", "cricinfo.com"))

_kept: dict[str, tuple[float, list[dict]]] = {}   # feed url -> (when read, its items)


# ---- reading a feed ----

def _download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        return response.read(MAX_BYTES)


def _plain(text: str | None) -> str:
    """Feed text as plain words: no tags, no entities, single spaces."""
    without_tags = re.sub(r"<[^>]*>", " ", html.unescape(text or ""))
    return " ".join(html.unescape(without_tags).split())


def _shorten(text: str, letters: int = SUMMARY_LETTERS) -> str:
    if len(text) <= letters:
        return text
    return text[:letters].rsplit(" ", 1)[0].rstrip(",;:.") + "…"


def _safe_link(link: str, sites: tuple[str, ...]) -> str | None:
    """The link, if it is a web address on one of the source's own sites."""
    address = urlparse(link.strip())
    host = (address.hostname or "").lower()
    on_site = any(host == site or host.endswith("." + site) for site in sites)
    return address.geturl() if address.scheme in ("http", "https") and on_site else None


def _published(text: str | None) -> str | None:
    """A feed's date as ISO text in UTC, or None if it cannot be read."""
    try:
        return parsedate_to_datetime((text or "").strip()).astimezone(UTC).isoformat(timespec="seconds")
    except (TypeError, ValueError):
        return None


def _text(item: ElementTree.Element, tag: str) -> str:
    """All the text under one child of an item, including text inside stray markup."""
    child = item.find(tag)
    return "" if child is None else "".join(child.itertext())


def parse_items(document: bytes, source: Source) -> list[dict]:
    """The items of an RSS document: title, link, summary and date. Bad items are dropped."""
    # A feed has no need to declare entities; one that does may be trying to exhaust memory.
    if b"<!DOCTYPE" in document or b"<!ENTITY" in document:
        raise ValueError("feed declares a document type")
    items = []
    for item in ElementTree.fromstring(document).iter("item"):
        title = _plain(_text(item, "title"))
        link = _safe_link(_text(item, "link"), source.sites)
        if not title or not link:
            continue
        summary = _plain(_text(item, "description"))
        items.append(dict(source=source.name, title=title, link=link,
                          published=_published(_text(item, "pubDate")),
                          summary="" if summary == title else _shorten(summary)))
    return items


def _read(source: Source, fresh_for: float) -> list[dict] | None:
    """A source's items, from memory if read recently. None when the feed cannot be read at all."""
    kept = _kept.get(source.url)
    if kept and time.time() - kept[0] < fresh_for:
        return kept[1]
    try:
        items = parse_items(_download(source.url), source)
    except (OSError, ValueError, ElementTree.ParseError):
        return kept[1] if kept else None   # an old answer is better than none
    _kept[source.url] = (time.time(), items)
    return items


# ---- news ----

def news(limit: int = 60, only: str = "") -> dict:
    """The newest headlines across every source, and which sources answered."""
    with ThreadPoolExecutor(max_workers=len(NEWS_SOURCES)) as pool:
        answers = list(pool.map(lambda source: _read(source, NEWS_FRESH_SECONDS), NEWS_SOURCES))
    sources = [dict(name=source.name, ok=items is not None, items=len(items or []))
               for source, items in zip(NEWS_SOURCES, answers, strict=True)]
    headlines = [item for items in answers for item in items or [] if not only or item["source"] == only]
    headlines.sort(key=lambda item: item["published"] or "", reverse=True)
    return dict(items=headlines[:limit], sources=sources)


# ---- live scores ----

# One side of a score line: "Victoria 13 & 244/10 *" is a name, its innings, and a batting mark.
SIDE = re.compile(r"^(?P<name>.*?)\s*(?P<scores>\d[\d/]*(?:\s*&\s*\d[\d/]*)*)?\s*(?P<batting>\*)?$")


def parse_side(text: str) -> dict:
    """A team's name, its score as written, and whether it is batting now."""
    found = SIDE.match(" ".join(text.split()))
    scores = re.sub(r"\s*&\s*", " & ", found["scores"] or "")
    return dict(team=found["name"].strip(), score=scores, batting=bool(found["batting"]))


def parse_score_line(line: str) -> dict | None:
    """'New South Wales 186/1 * v Tasmania 245/10' as two sides. None if it is not a match."""
    sides = line.split(" v ")
    if len(sides) != 2:
        return None
    first, second = (parse_side(side) for side in sides)
    if not first["team"] or not second["team"]:
        return None
    return dict(first=first, second=second, started=bool(first["score"] or second["score"]))


def live() -> dict:
    """The matches in the live feed now. `ok` is false when the feed could not be read."""
    items = _read(LIVE_SOURCE, LIVE_FRESH_SECONDS)
    matches = []
    for item in items or []:
        match = parse_score_line(item["title"])
        if match:
            matches.append(dict(match, link=item["link"]))
    return dict(matches=matches, ok=items is not None, source=LIVE_SOURCE.name)
