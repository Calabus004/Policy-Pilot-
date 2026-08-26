"""
Internal-only failure notifications.

This is deliberately a *separate* Slack webhook from slack_notify.py's
client-facing digest channel. If a run breaks, the client should never see
anything about it — they should just see tomorrow's digest arrive as
normal once it's fixed. Point INTERNAL_ALERT_WEBHOOK_URL (see .env.example)
at a private channel only you can see: a DM to yourself, or an internal
"#compliance-ops-alerts" channel the client is never invited to.
"""
from datetime import datetime, timezone

import requests

from compliance_monitor import config


def notify_internal_failure(failed_step, error_message):
    """
    Best-effort and never raises — if this itself fails (e.g. the internal
    webhook isn't set up yet), it just prints a warning rather than masking
    the original failure that triggered it. Called from main.py's top-level
    exception handler; it does not stop the run from still exiting non-zero
    so GitHub Actions itself shows the failure too (visible only to you,
    since the client has no access to this private repo).
    """
    if not config.INTERNAL_ALERT_WEBHOOK_URL:
        print(
            "  (No INTERNAL_ALERT_WEBHOOK_URL configured - skipping internal "
            "failure notification. Set this secret, pointed at a private "
            "Slack channel only you can see, to get pinged when a run fails.)"
        )
        return

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    text = (
        f":rotating_light: *Compliance monitor run FAILED* ({timestamp})\n"
        f"*Step:* {failed_step}\n"
        f"*Error:* {error_message}\n"
        "This is an internal-only alert - the client-facing channel was not touched."
    )

    try:
        response = requests.post(
            config.INTERNAL_ALERT_WEBHOOK_URL, json={"text": text}, timeout=15
        )
        response.raise_for_status()
        print("  Internal failure alert sent.")
    except Exception as exc:
        print(f"  Could not send internal failure alert either: {exc}")
