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


def log_to_notion(summary):
    """
    `summary` is the dict returned by ai_summary.summarize_with_claude().
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
