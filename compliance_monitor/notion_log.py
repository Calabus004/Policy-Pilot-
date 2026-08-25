"""
Step 6: Log every item — sanctions matches and FCA news, whether or not it
was posted to Slack — as a new page (row) in a Notion database, so there is
a complete, permanent audit trail of every compliance check run.

This expects a Notion database with these properties already created —
see README.md for exact setup steps:
    Name            (Title)
    Type            (Select: "Sanctions match" / "FCA news")
    Source          (Text)
    Relevant        (Checkbox)
    Explanation     (Text)
    Next action     (Text)
    Posted to Slack (Checkbox)
    Date            (Date)
    Link            (URL)
"""
from datetime import datetime, timezone

import requests

from compliance_monitor import config


def log_to_notion(summary, screened_names=None):
    """
    `summary` is the dict returned by ai_summary.summarize_with_claude().
    `screened_names` is the full list of names passed to check_sanctions()
    (see test_names.py) — every one of them gets a row here, even the ones
    with no sanctions match, so the audit trail proves every name was
    actually screened rather than only recording the hits. (FCA news
    doesn't need this: every fetched item is already sent to Claude and
    comes back in summary["fca_news_summary"] regardless of relevance.)
    Returns the number of rows written.
    """
    if not config.NOTION_API_KEY or not config.NOTION_DATABASE_ID:
        raise RuntimeError(
            "NOTION_API_KEY and NOTION_DATABASE_ID must be set. "
            "Add them to your .env file."
        )

    headers = {
        "Authorization": f"Bearer {config.NOTION_API_KEY}",
        "Notion-Version": config.NOTION_VERSION,
        "Content-Type": "application/json",
    }

    today = datetime.now(timezone.utc).date().isoformat()
    logged = 0

    matched_names = {item.get("queried_name") for item in summary.get("sanctions_summary", [])}
    for name_entry in screened_names or []:
        name = name_entry["name"] if isinstance(name_entry, dict) else name_entry
        if name in matched_names:
            continue  # this name has its own row(s) below, from the AI summary
        _create_notion_row(
            headers,
            name=name,
            item_type="Sanctions match",
            source="UK Sanctions List & EU Consolidated Financial Sanctions List",
            relevant=False,
            explanation="Screened against both lists — no match found.",
            next_action="No action needed.",
            posted_to_slack=False,
            log_date=today,
            link="",
        )
        logged += 1

    for item in summary.get("sanctions_summary", []):
        _create_notion_row(
            headers,
            name=item.get("queried_name", "Unknown"),
            item_type="Sanctions match",
            source=item.get("list_name", ""),
            relevant=bool(item.get("relevant")),
            explanation=item.get("plain_english_explanation", ""),
            next_action=item.get("next_action", ""),
            # Slack only receives items marked relevant (see slack_notify.py),
            # so that's also what "posted" means for the audit trail.
            posted_to_slack=bool(item.get("relevant")),
            log_date=today,
            link="",
        )
        logged += 1

    for item in summary.get("fca_news_summary", []):
        _create_notion_row(
            headers,
            name=item.get("title", "Untitled"),
            item_type="FCA news",
            source="FCA news and publications RSS feed",
            relevant=bool(item.get("relevant")),
            explanation=item.get("plain_english_explanation", ""),
            next_action=item.get("next_action", ""),
            posted_to_slack=bool(item.get("relevant")),
            log_date=today,
            link=item.get("link", ""),
        )
        logged += 1

    return logged


def _create_notion_row(
    headers, *, name, item_type, source, relevant, explanation, next_action,
    posted_to_slack, log_date, link,
):
    # Notion rich_text/title fields have a 2000-character limit per block.
    properties = {
        "Name": {"title": [{"text": {"content": name[:2000]}}]},
        "Type": {"select": {"name": item_type}},
        "Source": {"rich_text": [{"text": {"content": source[:2000]}}]},
        "Relevant": {"checkbox": relevant},
        "Explanation": {"rich_text": [{"text": {"content": explanation[:2000]}}]},
        "Next action": {"rich_text": [{"text": {"content": next_action[:2000]}}]},
        "Posted to Slack": {"checkbox": posted_to_slack},
        "Date": {"date": {"start": log_date}},
    }
    if link:
        properties["Link"] = {"url": link}

    payload = {
        "parent": {"database_id": config.NOTION_DATABASE_ID},
        "properties": properties,
    }
    response = requests.post(
        config.NOTION_API_URL, headers=headers, json=payload, timeout=15
    )
    response.raise_for_status()
