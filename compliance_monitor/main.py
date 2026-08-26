"""
Daily compliance monitoring — runs all six steps in order:
    1. Load the test customer name list
    2. Screen those names against the UK & EU sanctions lists (OpenSanctions)
    3. Fetch FCA news published in the last 24 hours
    4. Ask Claude what's relevant to a UK/EU fintech, why, and what to do next
    5. Post the relevant items to Slack
    6. Log every item — relevant or not — to Notion for a full audit trail

If any step raises, an internal-only failure alert is sent (see
failure_alert.py) — a *separate* Slack channel from the client-facing one,
so a broken run never becomes visible to the client.

Run locally with:  python -m compliance_monitor.main
"""
import sys

from compliance_monitor import config
from compliance_monitor.ai_summary import summarize_with_claude
from compliance_monitor.failure_alert import notify_internal_failure
from compliance_monitor.fca_news import get_recent_fca_news
from compliance_monitor.notion_log import log_to_notion
from compliance_monitor.sanctions_check import check_sanctions
from compliance_monitor.slack_notify import post_to_slack
from compliance_monitor.test_names import TEST_NAMES


def main():
    # Print the shape (not the value) of each secret, so a stray character
    # left over from copy-pasting is visible in the Actions log immediately
    # instead of showing up as a confusing downstream API error.
    print("Secret check (lengths/shape only, never the actual values):")
    print(config.diagnose_secrets())

    # Fail fast and clearly if a key is missing, rather than partway through.
    config.require_env_vars()

    # Tracks which step is in progress, so a failure alert can say exactly
    # where the run broke rather than just "something went wrong".
    current_step = "Step 1/6: Loading test name list"
    try:
        print(f"{current_step}...")
        names = TEST_NAMES
        print(f"  {len(names)} names loaded.")

        current_step = "Step 2/6: Checking names against UK & EU sanctions lists"
        print(f"{current_step}...")
        sanctions_matches = check_sanctions(names)
        print(f"  {len(sanctions_matches)} potential match(es) found.")

        current_step = "Step 3/6: Fetching FCA news from the last 24 hours"
        print(f"{current_step}...")
        fca_news_items = get_recent_fca_news(hours=24)
        print(f"  {len(fca_news_items)} item(s) found.")

        current_step = "Step 4/6: Asking Claude to summarize what's relevant"
        print(f"{current_step}...")
        summary = summarize_with_claude(sanctions_matches, fca_news_items)
        all_items = summary["sanctions_summary"] + summary["fca_news_summary"]
        n_relevant = sum(1 for item in all_items if item.get("relevant"))
        print(f"  {n_relevant} of {len(all_items)} item(s) flagged as relevant.")

        current_step = "Step 5/6: Posting relevant items to Slack"
        print(f"{current_step}...")
        post_to_slack(summary)
        print("  Done.")

        current_step = "Step 6/6: Logging every item to Notion for the audit trail"
        print(f"{current_step}...")
        logged = log_to_notion(summary, screened_names=names)
        print(f"  {logged} item(s) logged.")

        print("Daily compliance monitoring run complete.")
    except Exception as exc:
        notify_internal_failure(current_step, str(exc))
        raise


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Compliance monitoring run FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
