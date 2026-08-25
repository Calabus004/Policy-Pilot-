"""
Daily compliance monitoring — runs all six steps in order:
    1. Load the test customer name list
    2. Screen those names against the UK & EU sanctions lists (OpenSanctions)
    3. Fetch FCA news published in the last 24 hours
    4. Ask Claude what's relevant to a UK/EU fintech, why, and what to do next
    5. Post the relevant items to Slack
    6. Log every item — relevant or not — to Notion for a full audit trail

Run locally with:  python -m compliance_monitor.main
"""
import sys

from compliance_monitor import config
from compliance_monitor.ai_summary import summarize_with_claude
from compliance_monitor.fca_news import get_recent_fca_news
from compliance_monitor.notion_log import log_to_notion
from compliance_monitor.sanctions_check import check_sanctions
from compliance_monitor.slack_notify import post_to_slack
from compliance_monitor.test_names import TEST_NAMES


def main():
    # Fail fast and clearly if a key is missing, rather than partway through.
    config.require_env_vars()

    print("Step 1/6: Loading test name list...")
    names = TEST_NAMES
    print(f"  {len(names)} names loaded.")

    print("Step 2/6: Checking names against UK & EU sanctions lists...")
    sanctions_matches = check_sanctions(names)
    print(f"  {len(sanctions_matches)} potential match(es) found.")

    print("Step 3/6: Fetching FCA news from the last 24 hours...")
    fca_news_items = get_recent_fca_news(hours=24)
    print(f"  {len(fca_news_items)} item(s) found.")

    print("Step 4/6: Asking Claude to summarize what's relevant...")
    summary = summarize_with_claude(sanctions_matches, fca_news_items)
    all_items = summary["sanctions_summary"] + summary["fca_news_summary"]
    n_relevant = sum(1 for item in all_items if item.get("relevant"))
    print(f"  {n_relevant} of {len(all_items)} item(s) flagged as relevant.")

    print("Step 5/6: Posting relevant items to Slack...")
    post_to_slack(summary)
    print("  Done.")

    print("Step 6/6: Logging every item to Notion for the audit trail...")
    logged = log_to_notion(summary)
    print(f"  {logged} item(s) logged.")

    print("Daily compliance monitoring run complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Compliance monitoring run FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
