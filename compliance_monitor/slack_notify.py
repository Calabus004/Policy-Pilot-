"""
Step 5: Post the items Claude flagged as relevant to a Slack channel, using
an Incoming Webhook URL. Only "relevant" items are posted here — Notion
(step 6) logs everything, relevant or not, for the full audit trail.
"""
from datetime import date

import requests

from compliance_monitor import config


def post_to_slack(summary):
    """
    `summary` is the dict returned by ai_summary.summarize_with_claude():
    {"sanctions_summary": [...], "fca_news_summary": [...]}.
    """
    if not config.SLACK_WEBHOOK_URL:
        raise RuntimeError("SLACK_WEBHOOK_URL is not set. Add it to your .env file.")

    relevant_sanctions = [
        item for item in summary.get("sanctions_summary", []) if item.get("relevant")
    ]
    relevant_news = [
        item for item in summary.get("fca_news_summary", []) if item.get("relevant")
    ]

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Daily Compliance Digest — {date.today().isoformat()}",
            },
        }
    ]

    if not relevant_sanctions and not relevant_news:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "No sanctions matches or FCA news flagged as relevant "
                    "to a UK/EU fintech today. Full results are logged in Notion.",
                },
            }
        )
    else:
        if relevant_sanctions:
            blocks.append(_section("*:rotating_light: Sanctions screening matches*"))
            for item in relevant_sanctions:
                text = (
                    f"*{item['queried_name']}* — matched on {item['list_name']}\n"
                    f"{item['plain_english_explanation']}\n"
                    f"*Next action:* {item['next_action']}"
                )
                blocks.append(_section(text))
            blocks.append({"type": "divider"})

        if relevant_news:
            blocks.append(_section("*:newspaper: FCA news & enforcement*"))
            for item in relevant_news:
                title = item.get("title", "Untitled")
                link = item.get("link", "")
                title_line = f"<{link}|{title}>" if link else title
                text = (
                    f"*{title_line}*\n"
                    f"{item['plain_english_explanation']}\n"
                    f"*Next action:* {item['next_action']}"
                )
                blocks.append(_section(text))

    # Slack caps a single message at 50 blocks — fine for a small daily
    # digest, but worth knowing if you later widen the sanctions list or
    # start pulling many more news items per run.
    response = requests.post(
        config.SLACK_WEBHOOK_URL, json={"blocks": blocks}, timeout=15
    )
    response.raise_for_status()


def _section(text):
    return {"type": "section", "text": {"type": "mrkdwn", "text": text}}
