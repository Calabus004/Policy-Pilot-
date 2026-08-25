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

# --- Secrets (see .env.example for where to get each one) -----------------
OPENSANCTIONS_API_KEY = os.environ.get("OPENSANCTIONS_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")
NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")

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
