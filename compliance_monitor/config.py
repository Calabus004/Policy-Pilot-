"""
Central place for configuration: environment variables, API endpoints, and
the few constants the rest of the pipeline depends on.

All secrets are read from environment variables (never hard-coded), which
are loaded from a local .env file in development via python-dotenv, or
injected as GitHub Actions secrets when running on a schedule.
"""
import os

from dotenv import load_dotenv

# Loads variables from a .env file in the project root into the environment,
# if one exists. In GitHub Actions, the env vars are already set by the
# workflow, so this is a no-op there.
load_dotenv()

def _clean_secret(name):
    """
    Read an environment variable and strip common copy-paste artifacts that
    otherwise produce a cryptic "Invalid ... header value" error with no
    obvious connection to the secret being wrong:
      - real whitespace/newlines around the value (.strip())
      - a *literal* two-character "\\n" (backslash + n) left over from a
        value that was copied out of a place that displayed it as escaped
        text rather than an actual line break
      - a single pair of wrapping quotes, if the whole value was pasted
        including the quote marks (e.g. from a JSON snippet)
    Runs a couple of passes since these can stack (e.g. quotes around a
    value that also has a trailing literal "\\n" just inside them).
    """
    value = os.environ.get(name, "")
    for _ in range(2):
        value = value.strip()
        if value.endswith("\\n"):
            value = value[:-2]
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
    return value.strip()


# --- Secrets (see .env.example for where to get each one) -------------------
OPENSANCTIONS_API_KEY = _clean_secret("OPENSANCTIONS_API_KEY")
ANTHROPIC_API_KEY = _clean_secret("ANTHROPIC_API_KEY")
SLACK_WEBHOOK_URL = _clean_secret("SLACK_WEBHOOK_URL")
NOTION_API_KEY = _clean_secret("NOTION_API_KEY")
NOTION_DATABASE_ID = _clean_secret("NOTION_DATABASE_ID")

# Optional. A *separate* Slack Incoming Webhook, pointed at a private
# internal channel (e.g. a DM to yourself, or a #compliance-ops-alerts
# channel the client is never invited to) — used only to notify you when a
# run fails. Deliberately distinct from SLACK_WEBHOOK_URL above, which is
# the client-facing digest channel: a failure must never post there. Not
# required — if unset, failure_alert.py just prints a reminder to set it up
# instead of blocking the run.
INTERNAL_ALERT_WEBHOOK_URL = _clean_secret("INTERNAL_ALERT_WEBHOOK_URL")

# --- OpenSanctions ----------------------------------------------------------
OPENSANCTIONS_BASE_URL = "https://api.opensanctions.org"

# Dataset IDs on OpenSanctions for the two lists we care about.
# NOTE: OpenSanctions retired "gb_hmt_sanctions" (the old OFSI list) on
# 28 Jan 2026 in favour of "gb_fcdo_sanctions", which now covers the full
# consolidated UK Sanctions List. If OpenSanctions renames a dataset again,
# update the ID here (check https://www.opensanctions.org/datasets/ for the
# current slug) — nothing else in the code needs to change.
OPENSANCTIONS_DATASETS = {
    "UK Sanctions List": "gb_fcdo_sanctions",
    "EU Consolidated Financial Sanctions List": "eu_fsf",
}

# Match score is 0.0-1.0. 0.7 is a reasonable starting point for "worth a
# human look"; tighten it (closer to 1.0) if you get too many false positives.
OPENSANCTIONS_MATCH_THRESHOLD = 0.7

# --- FCA news RSS feed -------------------------------------------------------
# Covers all FCA news and publications categories. If this ever 404s, check
# https://www.fca.org.uk/news for the current feed link and update it here.
FCA_RSS_FEED_URL = "https://www.fca.org.uk/news/rss.xml?category=all"

# --- Claude (Anthropic) ------------------------------------------------------
CLAUDE_MODEL = "claude-opus-5"

# --- Notion -------------------------------------------------------------------
NOTION_VERSION = "2022-06-28"
NOTION_API_URL = "https://api.notion.com/v1/pages"


_SECRET_NAMES = [
    "OPENSANCTIONS_API_KEY",
    "ANTHROPIC_API_KEY",
    "SLACK_WEBHOOK_URL",
    "NOTION_API_KEY",
    "NOTION_DATABASE_ID",
    "INTERNAL_ALERT_WEBHOOK_URL",  # optional; diagnostics still show its shape if set
]


def diagnose_secrets():
    """
    Describe the *shape* of each raw secret (length, stray characters) —
    never the value itself — so a copy-paste artifact (trailing newline,
    wrapping quotes, a literal "\\n") is visible in the Actions log without
    ever printing anything that could leak the secret.
    """
    lines = []
    for name in _SECRET_NAMES:
        raw = os.environ.get(name, "")
        if not raw:
            lines.append(f"  {name}: NOT SET")
            continue
        notes = [f"{len(raw)} chars"]
        if raw != raw.strip():
            notes.append("has leading/trailing whitespace")
        if raw.endswith("\\n"):
            notes.append('ends with a literal backslash-n ("\\n" typed as text)')
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
            notes.append("wrapped in quote characters")
        lines.append(f"  {name}: {', '.join(notes)}")
    return "\n".join(lines)


def require_env_vars():
    """
    Fail fast with a clear message if any required secret is missing, rather
    than getting a confusing error halfway through the run.
    """
    missing = []
    if not OPENSANCTIONS_API_KEY:
        missing.append("OPENSANCTIONS_API_KEY")
    if not ANTHROPIC_API_KEY:
        missing.append("ANTHROPIC_API_KEY")
    if not SLACK_WEBHOOK_URL:
        missing.append("SLACK_WEBHOOK_URL")
    if not NOTION_API_KEY:
        missing.append("NOTION_API_KEY")
    if not NOTION_DATABASE_ID:
        missing.append("NOTION_DATABASE_ID")

    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): "
            + ", ".join(missing)
            + ". Add them to your .env file (see .env.example) or, if running "
            "in GitHub Actions, to the repository's secrets."
        )
