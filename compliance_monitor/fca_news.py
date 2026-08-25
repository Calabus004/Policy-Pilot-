"""
Step 3: Fetch the latest items from the FCA's news and publications RSS
feed, and return only the ones published in the last 24 hours.
"""
from datetime import datetime, timedelta, timezone

import feedparser

from compliance_monitor import config


def get_recent_fca_news(hours=24):
    """
    Parse the FCA RSS feed and return items published within the last
    `hours` hours, as a list of dicts:
        {"title": ..., "link": ..., "summary": ..., "published": ISO 8601 string}
    """
    feed = feedparser.parse(config.FCA_RSS_FEED_URL)

    # feedparser doesn't raise on network/parse errors — it sets `bozo` and
    # leaves `entries` empty instead, so we check explicitly.
    if feed.bozo and not feed.entries:
        raise RuntimeError(
            f"Could not read the FCA RSS feed at {config.FCA_RSS_FEED_URL}: "
            f"{feed.bozo_exception}. Check https://www.fca.org.uk/news for the "
            "current feed URL and update FCA_RSS_FEED_URL in config.py if it changed."
        )

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    recent_items = []

    for entry in feed.entries:
        published = _parse_entry_date(entry)
        # Skip items with no usable date rather than guessing — we'd rather
        # miss a rare undated item than flood Slack with stale news every day.
        if published is not None and published >= cutoff:
            recent_items.append(
                {
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": published.isoformat(),
                }
            )

    return recent_items


def _parse_entry_date(entry):
    """feedparser exposes a pre-parsed UTC time.struct_time when it can."""
    time_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if time_struct is None:
        return None
    return datetime(*time_struct[:6], tzinfo=timezone.utc)
