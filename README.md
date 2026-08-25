# Daily Compliance Monitoring

A daily script that:

1. Loads a test list of fictional fintech customer names.
2. Screens them against the UK Sanctions List and the EU Consolidated
   Financial Sanctions List via the [OpenSanctions](https://www.opensanctions.org/) Match API.
3. Pulls FCA news and enforcement notices published in the last 24 hours.
4. Sends both to Claude, which explains in plain English what's relevant to
   a UK/EU fintech and suggests a next action for each relevant item.
5. Posts the relevant items to a Slack channel.
6. Logs every item — relevant or not — to a Notion database as an audit trail.

## Project layout

```
compliance_monitor/
  config.py           # reads all API keys/settings from environment variables
  test_names.py       # Step 1: fictional test customer names
  sanctions_check.py  # Step 2: OpenSanctions match API
  fca_news.py         # Step 3: FCA RSS feed, last 24 hours
  ai_summary.py        # Step 4: Claude summarization
  slack_notify.py      # Step 5: post to Slack
  notion_log.py         # Step 6: log to Notion
  main.py                # Step 7: runs steps 1-6 in order
.github/workflows/
  daily-compliance-monitoring.yml   # runs main.py on a daily schedule
```

## 1. Accounts and API keys you need before this will run

You need five secrets. Create a `.env` file in the project root (copy
`.env.example` — `cp .env.example .env`) and paste each one in on its own
line, in this exact format: `KEY_NAME=the_value_no_quotes`.

| # | Service | Where to get it | .env line |
|---|---------|------------------|-----------|
| 1 | OpenSanctions | [opensanctions.org/api](https://www.opensanctions.org/api/) — request an API key (free tier available for low volume) | `OPENSANCTIONS_API_KEY=your_key_here` |
| 2 | Anthropic (Claude) | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) — create an API key (you'll need billing set up) | `ANTHROPIC_API_KEY=your_key_here` |
| 3 | Slack | See "Slack setup" below | `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...` |
| 4 | Notion integration | See "Notion setup" below | `NOTION_API_KEY=secret_...` |
| 5 | Notion database | See "Notion setup" below | `NOTION_DATABASE_ID=your_database_id` |

`.env` is already listed in `.gitignore` — never commit it.

### Slack setup

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**. Name it (e.g. "Compliance Monitor") and pick your workspace.
2. In the app's settings, open **Incoming Webhooks** and switch it **On**.
3. Click **Add New Webhook to Workspace**, choose the channel you want the daily digest posted to, and authorize it.
4. Copy the webhook URL (looks like `https://hooks.slack.com/services/T000/B000/XXXX`) into `SLACK_WEBHOOK_URL` in your `.env`.

### Notion setup

1. Go to [notion.so/my-integrations](https://www.notion.so/my-integrations) → **New integration**. Name it, select the workspace, and create it.
2. Copy the **Internal Integration Secret** (starts with `secret_` or `ntn_`) into `NOTION_API_KEY` in your `.env`.
3. In Notion, create a new database (table) with **exactly** these properties (name and type matter — the script writes to these by name):

   | Property name | Type |
   |---|---|
   | Name | Title (this is the default title property) |
   | Type | Select |
   | Source | Text |
   | Relevant | Checkbox |
   | Explanation | Text |
   | Next action | Text |
   | Posted to Slack | Checkbox |
   | Date | Date |
   | Link | URL |

4. Click **Share** on the database (top right) → **Invite** → select the integration you created in step 1, so it has permission to write to it.
5. Copy the database ID from its URL: `https://www.notion.so/yourworkspace/<DATABASE_ID>?v=...` — it's the 32-character hex string right after your workspace name (before the `?`). Paste it into `NOTION_DATABASE_ID`.

## 2. Install and run locally

```bash
pip install -r requirements.txt
cp .env.example .env
# ...fill in .env as above...
python -m compliance_monitor.main
```

You should see progress printed for each of the 6 steps, ending with
"Daily compliance monitoring run complete." Check your Slack channel and
Notion database afterwards.

## 3. Scheduling it to run automatically — GitHub Actions (free)

A workflow is already set up at `.github/workflows/daily-compliance-monitoring.yml`.
It runs every day at 07:00 UTC and can also be triggered manually.

To activate it:

1. Push this repository to GitHub (if it isn't already there).
2. In the GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret**, and add all five secrets with the **same names** used in `.env`:
   `OPENSANCTIONS_API_KEY`, `ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URL`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`.
3. That's it — GitHub Actions will run the workflow daily for free (public repos get unlimited free minutes; private repos get 2,000 free minutes/month on the free plan, and this job takes well under a minute).
4. To test it immediately rather than waiting for the schedule: go to the **Actions** tab → **Daily Compliance Monitoring** → **Run workflow**.
5. To change the time it runs, edit the `cron` line in the workflow file — cron schedules on GitHub Actions are always in UTC.

## Notes and things to tune later

- **Match threshold**: `OPENSANCTIONS_MATCH_THRESHOLD` in `config.py` (default `0.7`) controls how confident a sanctions match must be before it's reported. Lower it to catch more (noisier) matches, raise it to reduce false positives.
- **FCA RSS feed URL**: if `FCA_RSS_FEED_URL` in `config.py` ever stops working, check [fca.org.uk/news](https://www.fca.org.uk/news) for the current feed link.
- **OpenSanctions dataset IDs**: `gb_fcdo_sanctions` (UK) and `eu_fsf` (EU) are the current dataset slugs as of this writing. OpenSanctions occasionally renames/consolidates datasets — check [opensanctions.org/datasets](https://www.opensanctions.org/datasets/) if matches stop coming back.
- **Test names**: `test_names.py` is entirely fictional data for testing the pipeline. Replace it with a real (permissioned) query against your customer/KYC system before using this for anything beyond a proof of concept.
- **Sanctions matches always route to a human**: by design, the AI is instructed to never suggest an automatic account action for a sanctions match — only "escalate for manual review". Don't change this without your compliance/legal team's sign-off.
