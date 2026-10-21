"""Reading publishers' feeds. No test here touches the network."""
import pytest
from fastapi.testclient import TestClient

from innings import feeds
from innings.feeds import Source, parse_items, parse_score_line, parse_side
from innings.web.app import app

SOURCE = Source("Example", "https://example.com/rss", ("example.com",))
FEED = b"""<?xml version="1.0"?><rss><channel>
<item><title><![CDATA[India win &amp; go top]]></title><link>https://www.example.com/a</link>
  <description>&lt;p&gt;A <b>fine</b> chase.&lt;/p&gt;</description>
  <pubDate>Fri, 09 Oct 2026 02:43:43 GMT</pubDate></item>
<item><title>Leads elsewhere</title><link>https://evil.test/steal</link></item>
<item><title>Runs a script</title><link>javascript:alert(1)</link></item>
<item><title></title><link>https://example.com/no-title</link></item>
</channel></rss>"""


def test_a_feed_item_becomes_plain_text_with_a_link_to_its_own_site():
    items = parse_items(FEED, SOURCE)
    assert len(items) == 1   # the off-site link, the script link and the untitled item are dropped
    item = items[0]
    assert item["title"] == "India win & go top"
    assert item["summary"] == "A fine chase."
    assert item["link"] == "https://www.example.com/a"
    assert item["published"] == "2026-10-09T02:43:43+00:00"
    assert item["source"] == "Example"


def test_a_feed_that_declares_entities_is_refused():
    bomb = b'<?xml version="1.0"?><!DOCTYPE x [<!ENTITY a "aaaa">]><rss><channel/></rss>'
    with pytest.raises(ValueError):
        parse_items(bomb, SOURCE)


def test_long_summaries_are_cut_at_a_word():
    short = feeds._shorten("word " * 100)
    assert len(short) <= feeds.SUMMARY_LETTERS + 1 and short.endswith("…") and "  " not in short


@pytest.mark.parametrize("text,team,score,batting", [
    ("New South Wales 186/1 *", "New South Wales", "186/1", True),
    ("Tasmania 245/10", "Tasmania", "245/10", False),
    ("Victoria 13 &  244/10 *", "Victoria", "13 & 244/10", True),
    ("India A", "India A", "", False),
    ("Sunrisers Eastern Cape 1st XI", "Sunrisers Eastern Cape 1st XI", "", False),
])
def test_one_side_of_a_score_line(text, team, score, batting):
    assert parse_side(text) == dict(team=team, score=score, batting=batting)


def test_a_score_line_is_two_sides():
    match = parse_score_line("Western Australia v Queensland 293/8 *")
    assert match["first"]["team"] == "Western Australia" and not match["first"]["score"]
    assert match["second"] == dict(team="Queensland", score="293/8", batting=True)
    assert match["started"]
    assert not parse_score_line("India v Australia")["started"]
    assert parse_score_line("No match here") is None


@pytest.fixture
def offline(monkeypatch):
    """Every feed answers with FEED, or fails when its address contains 'guardian'."""
    def download(url):
        if "guardian" in url:
            raise OSError("down")
        if "livescores" in url:
            return (b"<rss><channel><item><title>Oman v India 120/2 *</title>"
                    b"<link>http://www.cricinfo.com/m/1.html</link></item>"
                    b"<item><title>India A v Australia A</title>"
                    b"<link>http://www.cricinfo.com/m/2.html</link></item></channel></rss>")
        return FEED.replace(b"www.example.com", b"www.bbc.co.uk")
    monkeypatch.setattr(feeds, "_download", download)
    monkeypatch.setattr(feeds, "_kept", {})


def test_news_survives_a_source_that_is_down(offline):
    answer = TestClient(app).get("/api/news").json()
    by_name = {source["name"]: source for source in answer["sources"]}
    assert not by_name["The Guardian"]["ok"] and by_name["BBC Sport"]["ok"]
    assert [item["source"] for item in answer["items"]] == ["BBC Sport"]   # only bbc links are on-site


def test_live_scores_put_matches_under_way_first(offline):
    answer = TestClient(app).get("/api/livescores").json()
    assert answer["ok"]
    assert [match["first"]["team"] for match in answer["matches"]] == ["Oman", "India A"]
    assert answer["matches"][0]["second"] == dict(team="India", score="120/2", batting=True)
