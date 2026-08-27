# Daily Compliance Monitoring

A daily script that:

1. Loads a test list of real public companies plus fictional individuals,
   representing a fintech's customer base.
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
  slack_notify.py      # Step 5: post to Slack (client-facing digest)
  notion_log.py         # Step 6: log to Notion (full audit trail)
  failure_alert.py       # internal-only "a run broke" notification, separate from Slack step 5
  report_builder.py      # generates a polished, client-facing HTML report from the Notion audit trail
  main.py                # Step 7: runs steps 1-6 in order
.github/workflows/
  daily-compliance-monitoring.yml   # runs main.py on a daily schedule
```

## Generating a client-facing report

Slack and Notion are the operational output — useful day to day, but not
something you'd hand to a client. `report_builder.py` reads the Notion
audit trail for a date range and renders a single self-contained HTML
report: a summary of what was screened, any genuine findings with plain-
English explanations and next actions, and a methodology/disclaimer
section. It only calls Notion, so it's safe to run even if OpenSanctions
is rate-limited or the daily pipeline is mid-debugging.

```bash
python -m compliance_monitor.report_builder --days 7 --client "Acme Payments Ltd"
```

Writes to `reports/compliance_report_<date>.html` by default (override with
`--out path/to/file.html`). Open it in a browser, or run `open` (macOS) /
`start` (Windows) on the path it prints. `reports/` is gitignored since a
real report may contain real client screening data.

## 1. Accounts and API keys you need before this will run

You need five required secrets, plus one optional one for private failure
alerts. Create a `.env` file in the project root (copy `.env.example` —
`cp .env.example .env`) and paste each one in on its own line, in this
exact format: `KEY_NAME=the_value_no_quotes`.

| # | Service | Where to get it | .env line |
|---|---------|------------------|-----------|
| 1 | OpenSanctions | [opensanctions.org/api](https://www.opensanctions.org/api/) — request an API key (free tier available for low volume) | `OPENSANCTIONS_API_KEY=your_key_here` |
| 2 | Anthropic (Claude) | [console.anthropic.com/settings/keys](https://console.anthropic.com/settings/keys) — create an API key (you'll need billing set up) | `ANTHROPIC_API_KEY=your_key_here` |
| 3 | Slack (client-facing) | See "Slack setup" below | `SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...` |
| 4 | Notion integration | See "Notion setup" below | `NOTION_API_KEY=secret_...` |
| 5 | Notion database | See "Notion setup" below | `NOTION_DATABASE_ID=your_database_id` |
| 6 (optional) | Slack (private, internal-only) | Same steps as #3, different channel | `INTERNAL_ALERT_WEBHOOK_URL=https://hooks.slack.com/services/...` |

`.env` is already listed in `.gitignore` — never commit it.

### Slack setup

You need **two separate** Incoming Webhooks — one for the client-facing
digest, one for private failure alerts only you see. Repeat these steps
twice, once per channel:

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**. Name it (e.g. "Compliance Monitor") and pick your workspace.
2. In the app's settings, open **Incoming Webhooks** and switch it **On**.
3. Click **Add New Webhook to Workspace**, choose the channel, and authorize it.
4. Copy the webhook URL (looks like `https://hooks.slack.com/services/T000/B000/XXXX`).

For the **client-facing digest**, pick the channel the client (or your team, during testing) sees, and put the URL in `SLACK_WEBHOOK_URL`.

For **internal failure alerts**, pick a channel the client will never be in — a DM to yourself, or a private `#compliance-ops-alerts` channel — and put that URL in `INTERNAL_ALERT_WEBHOOK_URL`. This one is optional: if you skip it, the run still works, it just won't be able to notify you privately when something breaks (it'll still show as a failed run in GitHub Actions, which the client can't see either way since this is a private repo).

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

1. Push this repository to GitHub (if it isn't already there) — as a **private** repo if this will ever contain a real client's data, so the client itself has no visibility into the code, secrets, or run history/failures.
2. In the GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret**, and add the same secrets used in `.env`:
   `OPENSANCTIONS_API_KEY`, `ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_URL`, `NOTION_API_KEY`, `NOTION_DATABASE_ID`, and (recommended) `INTERNAL_ALERT_WEBHOOK_URL`.
3. That's it — GitHub Actions will run the workflow daily for free (public repos get unlimited free minutes; private repos get 2,000 free minutes/month on the free plan, and this job takes well under a minute).
4. To test it immediately rather than waiting for the schedule: go to the **Actions** tab → **Daily Compliance Monitoring** → **Run workflow**.
5. To change the time it runs, edit the `cron` line in the workflow file — cron schedules on GitHub Actions are always in UTC.

## Notes and things to tune later

- **Match threshold**: `OPENSANCTIONS_MATCH_THRESHOLD` in `config.py` (default `0.7`) controls how confident a sanctions match must be before it's reported. Lower it to catch more (noisier) matches, raise it to reduce false positives.
- **FCA RSS feed URL**: if `FCA_RSS_FEED_URL` in `config.py` ever stops working, check [fca.org.uk/news](https://www.fca.org.uk/news) for the current feed link.
- **OpenSanctions dataset IDs**: `gb_fcdo_sanctions` (UK) and `eu_fsf` (EU) are the current dataset slugs as of this writing. OpenSanctions occasionally renames/consolidates datasets — check [opensanctions.org/datasets](https://www.opensanctions.org/datasets/) if matches stop coming back.
- **Test names**: `test_names.py` mixes real public companies, fictional individuals, and one deliberately real sanctioned entity ("Bank Rossiya") to prove the alert path fires on a genuine hit. Replace it with a real (permissioned) query against your customer/KYC system before using this for anything beyond a proof of concept.
- **Sanctions matches always route to a human**: by design, the AI is instructed to never suggest an automatic account action for a sanctions match — only "escalate for manual review". Don't change this without your compliance/legal team's sign-off.
- **Failure alerts stay private**: `failure_alert.py` posts to `INTERNAL_ALERT_WEBHOOK_URL` only — never to the client-facing `SLACK_WEBHOOK_URL` channel. If a run breaks, only you get pinged; the client just sees the next successful digest whenever it arrives.
- **Retries**: OpenSanctions requests automatically retry on HTTP 429 (rate limited) with backoff, up to 3 attempts — useful when testing with several manual runs in quick succession, and for resilience in production.
- **Before pitching to a real client**: OpenSanctions' free API tier is for evaluation/individual use, not for reselling a service built on it — check their commercial licensing terms before using real client data or charging for this.

## Waitlist & assessment site (`web/`)

A separate static site, deployed on Netlify from this same repo, that runs a
"pre-flight compliance assessment" ahead of the product waitlist: it captures
a name + email, walks through 8 questions about how a team currently handles
compliance, and shows back an empathetic result (never the internal score —
that's for us). Deploy config lives in `netlify.toml` (`publish = "web"`).

```
web/
  index.html                       # the whole public site — hero, assessment, waitlist gate
  privacy.html                      # privacy notice — linked from the consent checkbox on the gate
  dashboard.html                    # internal scorecard — not linked from the public site
netlify/functions/
  notify-signup.js                 # sends the follow-up email via Resend when someone finishes
  get-submissions.js                # powers dashboard.html — password-gated read of Netlify Forms data
netlify.toml                       # publish dir + functions dir for Netlify
```

**Data capture**: a single Netlify Form named `assessment`, detected
automatically from the hidden `<form>` markup in `index.html` and submitted
via JS `fetch` (no page reload) at three different moments, told apart by a
`stage` field:

- `stage=started` — name + email, fired the moment someone passes the email
  gate, before they've answered anything. Catches partial leads.
- `stage=skipped` — someone used "skip the questions" — name + email only,
  no quiz answers.
- `stage=completed` — name, email, all 8 answers, the `risk_score` (0–100) /
  `risk_tier` (Low/Moderate/High risk) shown back to them on screen, and a
  separate **internal-only** `fit_score` / `fit_tier` (Cold/Warm/Hot) that
  gauges how strong a candidate someone is for the product — this one is
  never shown in the UI.

Everything lands in the same form in **Site settings → Forms** in Netlify —
there's only one form to check, not several. Turn on
email notifications there if you want to be pinged per signup.

**Follow-up email (Resend)**: `netlify/functions/notify-signup.js` is a
zero-dependency Netlify Function — no `npm install` needed, it uses the
built-in `fetch` to call Resend's HTTP API directly. To wire it up:

1. Create an account at [resend.com](https://resend.com/) and grab an API key.
2. In Netlify: **Site settings → Environment variables**, add:
   - `RESEND_API_KEY` — your Resend key
   - `RESEND_FROM_EMAIL` (optional) — e.g. `Policy Pilot <hello@yourdomain.com>`.
     Without this it falls back to Resend's shared `onboarding@resend.dev`
     sender, which only delivers to the email address on your Resend account
     until you verify your own sending domain.
3. Redeploy (**Deploys → Trigger deploy**) so the function picks up the new
   env vars.

The function is called from the client the instant someone finishes the
assessment or uses "skip the questions" — it's fire-and-forget, so a slow or
failed email send never blocks the on-page confirmation.

**Privacy notice & consent**: `web/privacy.html` is a minimal starting
template, not a lawyer-reviewed policy — it has placeholder brackets for your
real company name, address, and contact email that need filling in before
this collects data from real people. The gate on the main page now has a
required consent checkbox linking to it, and every submission carries a
`consent: "yes"` field as a record that it was ticked.

**Internal scorecard (`dashboard.html`)**: a second page, deliberately not
linked from anywhere on the public site (and marked `noindex` for search
engines), that shows every lead ranked by `fit_score` — including the
`fit_tier` and full Q&A that the public page never displays — plus a
"started but didn't finish" list. It's password-gated through
`netlify/functions/get-submissions.js`, which reads submissions straight
from Netlify's own Submissions API server-side. To set it up:

1. In Netlify: **User settings → Applications → Personal access tokens →
   New access token**. Copy it.
2. **Site settings → Environment variables**, add:
   - `NETLIFY_API_TOKEN` — the personal access token from step 1
   - `DASHBOARD_PASSWORD` — any passphrase you'll type in to view the
     dashboard (pick something real; this is the only thing standing between
     the page and everyone's name, email, and answers)
   - `NETLIFY_SITE_ID` — only needed if the function can't read the site ID
     automatically; find it under **Site settings → General → Site details**.
3. Redeploy, then visit `https://<your-site>.netlify.app/dashboard.html`
   directly (bookmark it — nothing on the public site links to it) and enter
   the password.

Being unlinked and `noindex` is obscurity, not real security — anyone who
guesses or is given the URL still hits a working password prompt, so treat
`DASHBOARD_PASSWORD` as a real credential, not a formality.
