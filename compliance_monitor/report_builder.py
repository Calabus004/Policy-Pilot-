"""
Client-facing compliance report.

Reads the audit trail already logged in Notion (see notion_log.py) for a
given date range and renders it as a polished, self-contained HTML report —
the presentable deliverable you'd actually show a client, as opposed to the
raw Slack digest / Notion database, which are operational rather than
client-facing.

Run locally with:
    python -m compliance_monitor.report_builder --days 7 --client "Acme Payments Ltd"

This queries Notion directly and does not touch OpenSanctions, Anthropic,
or Slack, so it's safe to run even while the daily pipeline is rate-limited
or mid-debugging.
"""
import argparse
import html
from datetime import date, datetime, timedelta, timezone

import requests

from compliance_monitor import config

NOTION_QUERY_URL_TEMPLATE = "https://api.notion.com/v1/databases/{database_id}/query"


def fetch_rows(start_date, end_date):
    """
    Returns every row logged in the Notion audit trail with Date between
    start_date and end_date (inclusive), as a list of plain dicts:
    {"name", "type", "source", "relevant", "explanation", "next_action",
     "posted_to_slack", "date", "link"}.
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
    url = NOTION_QUERY_URL_TEMPLATE.format(database_id=config.NOTION_DATABASE_ID)

    payload = {
        "filter": {
            "and": [
                {"property": "Date", "date": {"on_or_after": start_date.isoformat()}},
                {"property": "Date", "date": {"on_or_before": end_date.isoformat()}},
            ]
        },
        "sorts": [{"property": "Date", "direction": "descending"}],
        "page_size": 100,
    }

    rows = []
    cursor = None
    while True:
        body = dict(payload)
        if cursor:
            body["start_cursor"] = cursor
        response = requests.post(url, headers=headers, json=body, timeout=30)
        if not response.ok:
            raise RuntimeError(f"Notion API error {response.status_code}: {response.text}")
        data = response.json()

        for page in data.get("results", []):
            rows.append(_parse_page(page["properties"]))

        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")

    return rows


def _parse_page(props):
    def text_of(prop):
        rich = props.get(prop, {}).get("rich_text", [])
        return "".join(block.get("plain_text", "") for block in rich)

    title = props.get("Name", {}).get("title", [])
    name = "".join(block.get("plain_text", "") for block in title)

    return {
        "name": name,
        "type": (props.get("Type", {}).get("select") or {}).get("name", ""),
        "source": text_of("Source"),
        "relevant": bool(props.get("Relevant", {}).get("checkbox")),
        "explanation": text_of("Explanation"),
        "next_action": text_of("Next action"),
        "posted_to_slack": bool(props.get("Posted to Slack", {}).get("checkbox")),
        "date": (props.get("Date", {}).get("date") or {}).get("start", ""),
        "link": (props.get("Link", {}) or {}).get("url") or "",
    }


def summarize(rows):
    sanctions_rows = [r for r in rows if r["type"] == "Sanctions match"]
    news_rows = [r for r in rows if r["type"] == "FCA news"]
    findings = [r for r in rows if r["relevant"]]

    return {
        "names_screened": len(sanctions_rows),
        "sanctions_matches": sum(1 for r in sanctions_rows if r["relevant"]),
        "fca_items_reviewed": len(news_rows),
        "fca_items_flagged": sum(1 for r in news_rows if r["relevant"]),
        "findings": findings,
    }


def render_html(stats, client_name, period_label, generated_at_label):
    e = html.escape

    if stats["findings"]:
        findings_html = "\n".join(_render_finding(f) for f in stats["findings"])
        clean_section = ""
    else:
        findings_html = ""
        clean_section = f"""
    <section>
      <p class="eyebrow">Clean this period</p>
      <div class="clear-card">
        <span class="dot"></span>
        <div>
          <p>{stats['names_screened']} sanctions check(s) and {stats['fca_items_reviewed']} FCA item(s) reviewed — nothing flagged as relevant.</p>
          <div class="sub">This is the expected, good outcome on most days.</div>
        </div>
      </div>
    </section>"""

    findings_section = f"""
    <section>
      <p class="eyebrow">Findings requiring review</p>
      {findings_html}
    </section>""" if stats["findings"] else ""

    return _PAGE_TEMPLATE.format(
        client_name=e(client_name),
        period_label=e(period_label),
        generated_at_label=e(generated_at_label),
        names_screened=stats["names_screened"],
        sanctions_matches=stats["sanctions_matches"],
        fca_items_reviewed=stats["fca_items_reviewed"],
        fca_items_flagged=stats["fca_items_flagged"],
        findings_section=findings_section,
        clean_section=clean_section,
    )


def _render_finding(item):
    e = html.escape
    is_sanctions = item["type"] == "Sanctions match"
    chip_class = "critical" if is_sanctions else "flag"
    chip_label = "Sanctions match" if is_sanctions else "FCA news"

    name_html = e(item["name"])
    if item["link"]:
        name_html = f'<a href="{e(item["link"])}" style="color:inherit">{name_html}</a>'

    return f"""
      <div class="finding">
        <div class="finding-head">
          <span class="finding-name">{name_html}</span>
          <span class="chip {chip_class}">{chip_label}</span>
        </div>
        <div class="finding-source">{e(item['source'])}{' — ' + e(item['date']) if item['date'] else ''}</div>
        <p class="explain">{e(item['explanation'])}</p>
        <div class="next-action">
          <span class="tag">Next action</span>
          <span>{e(item['next_action'])}</span>
        </div>
      </div>"""


_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>Compliance Report — {client_name}</title>
<meta name="viewport" content="width=device-width, initial-scale=1" />
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet" />
<style>
  :root {{
    --ink: #16211d; --muted: #5b6b62; --paper: #f6f7f4; --paper-raised: #ffffff;
    --line: #dce0da; --accent: #0f6d63; --accent-soft: #e4f0ec;
    --status-clear: #3f7d5c; --status-clear-bg: #e7f1ea;
    --status-flag: #a8621c; --status-flag-bg: #fbeedd;
    --status-critical: #a63d3d; --status-critical-bg: #f7e4e1;
  }}
  @media (prefers-color-scheme: dark) {{
    :root {{
      --ink: #edefea; --muted: #93a69a; --paper: #10160f; --paper-raised: #171f19;
      --line: #263029; --accent: #52c9b3; --accent-soft: #16332c;
      --status-clear: #74c295; --status-clear-bg: #16332a;
      --status-flag: #e2a862; --status-flag-bg: #392a15;
      --status-critical: #e28a8a; --status-critical-bg: #3a1e1e;
    }}
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; background: var(--paper); color: var(--ink);
    font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
    -webkit-font-smoothing: antialiased; line-height: 1.55;
  }}
  .page {{ max-width: 860px; margin: 0 auto; padding: 2.75rem 1.5rem 5rem; }}
  header.masthead {{
    display: flex; justify-content: space-between; align-items: flex-end; gap: 1.5rem;
    border-bottom: 1px solid var(--line); padding-bottom: 1.75rem; margin-bottom: 2.25rem;
    flex-wrap: wrap;
  }}
  .brand {{
    display: flex; align-items: center; gap: 0.6rem;
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.78rem;
    letter-spacing: 0.08em; text-transform: uppercase; color: var(--accent);
    margin-bottom: 0.9rem;
  }}
  .brand::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: var(--accent); display: inline-block; }}
  h1 {{
    font-family: "Fraunces", Georgia, serif; font-optical-sizing: auto; font-weight: 500;
    font-size: clamp(1.9rem, 1.5rem + 1.6vw, 2.5rem); line-height: 1.12; margin: 0;
    text-wrap: balance;
  }}
  .masthead-meta {{
    text-align: right; font-family: "IBM Plex Mono", ui-monospace, monospace;
    font-size: 0.82rem; color: var(--muted); line-height: 1.7; font-variant-numeric: tabular-nums;
  }}
  .masthead-meta .client {{ color: var(--ink); font-weight: 500; font-size: 0.9rem; }}
  section {{ margin-bottom: 2.75rem; }}
  .eyebrow {{
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.74rem;
    letter-spacing: 0.09em; text-transform: uppercase; color: var(--muted); margin: 0 0 0.9rem;
  }}
  .stat-grid {{
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px;
    background: var(--line); border: 1px solid var(--line); border-radius: 10px; overflow: hidden;
  }}
  .stat {{ background: var(--paper-raised); padding: 1.25rem 1.1rem; }}
  .stat .value {{
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-variant-numeric: tabular-nums;
    font-size: 1.9rem; font-weight: 500; color: var(--ink); display: block;
  }}
  .stat .value.accent {{ color: var(--accent); }}
  .stat .label {{ font-size: 0.8rem; color: var(--muted); margin-top: 0.3rem; display: block; }}
  .clear-card {{
    background: var(--status-clear-bg);
    border: 1px solid color-mix(in srgb, var(--status-clear) 35%, transparent);
    border-radius: 10px; padding: 1.1rem 1.25rem; display: flex; align-items: center; gap: 0.85rem;
  }}
  .clear-card .dot {{ width: 10px; height: 10px; border-radius: 50%; background: var(--status-clear); flex-shrink: 0; }}
  .clear-card p {{ margin: 0; color: var(--ink); }}
  .clear-card .sub {{ color: var(--muted); font-size: 0.88rem; margin-top: 0.15rem; }}
  .finding {{
    background: var(--paper-raised); border: 1px solid var(--line); border-radius: 10px;
    padding: 1.2rem 1.35rem; margin-bottom: 0.85rem;
  }}
  .finding-head {{
    display: flex; align-items: center; justify-content: space-between; gap: 1rem;
    margin-bottom: 0.6rem; flex-wrap: wrap;
  }}
  .finding-name {{ font-weight: 600; font-size: 1.02rem; }}
  .chip {{
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.7rem;
    letter-spacing: 0.05em; text-transform: uppercase; padding: 0.28rem 0.6rem;
    border-radius: 5px; white-space: nowrap;
  }}
  .chip.critical {{ background: var(--status-critical-bg); color: var(--status-critical); }}
  .chip.flag {{ background: var(--status-flag-bg); color: var(--status-flag); }}
  .finding-source {{ font-size: 0.8rem; color: var(--muted); margin-bottom: 0.7rem; }}
  .finding p.explain {{ margin: 0 0 0.7rem; max-width: 65ch; }}
  .next-action {{
    display: flex; gap: 0.6rem; font-size: 0.92rem; background: var(--accent-soft);
    border-radius: 7px; padding: 0.6rem 0.8rem;
  }}
  .next-action .tag {{
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.7rem;
    text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent);
    flex-shrink: 0; padding-top: 0.1rem;
  }}
  .methodology {{ border-top: 1px solid var(--line); padding-top: 1.5rem; color: var(--muted); font-size: 0.86rem; }}
  .methodology h2 {{
    font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 0.74rem;
    letter-spacing: 0.09em; text-transform: uppercase; color: var(--muted); margin: 0 0 0.75rem; font-weight: 500;
  }}
  .methodology ul {{ margin: 0 0 1rem; padding-left: 1.1rem; }}
  .methodology li {{ margin-bottom: 0.3rem; }}
  .disclaimer {{ background: var(--paper-raised); border: 1px solid var(--line); border-radius: 8px; padding: 0.9rem 1.1rem; }}
  @media (max-width: 600px) {{
    .stat-grid {{ grid-template-columns: repeat(2, 1fr); }}
    .masthead-meta {{ text-align: left; }}
    header.masthead {{ flex-direction: column; align-items: flex-start; }}
  }}
</style>
</head>
<body>
<div class="page">
  <header class="masthead">
    <div>
      <div class="brand">Policy Pilot</div>
      <h1>Compliance Monitoring Report</h1>
    </div>
    <div class="masthead-meta">
      <div class="client">Client: {client_name}</div>
      <div>Period: {period_label}</div>
      <div>Generated: {generated_at_label}</div>
    </div>
  </header>

  <section>
    <p class="eyebrow">Summary</p>
    <div class="stat-grid">
      <div class="stat"><span class="value">{names_screened}</span><span class="label">Sanctions checks performed</span></div>
      <div class="stat"><span class="value accent">{sanctions_matches}</span><span class="label">Sanctions matches flagged</span></div>
      <div class="stat"><span class="value">{fca_items_reviewed}</span><span class="label">FCA items reviewed</span></div>
      <div class="stat"><span class="value accent">{fca_items_flagged}</span><span class="label">FCA items flagged relevant</span></div>
    </div>
  </section>
  {findings_section}
  {clean_section}

  <section class="methodology">
    <h2>Methodology</h2>
    <ul>
      <li>Customer names are matched against the UK Sanctions List and EU Consolidated Financial Sanctions List via the OpenSanctions Match API, at a 0.7+ confidence threshold.</li>
      <li>FCA news and publications are reviewed daily for the prior 24 hours.</li>
      <li>Relevance, plain-English explanations, and next actions are generated by Claude and reviewed against this methodology — every item is logged in the underlying audit trail regardless of relevance.</li>
    </ul>
    <div class="disclaimer">
      This report is a triage aid, not a final compliance determination. Every sanctions match must be independently reviewed and confirmed by a qualified compliance officer before any action is taken on a customer relationship.
    </div>
  </section>
</div>
</body>
</html>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate a client-facing compliance report from the Notion audit trail.")
    parser.add_argument("--days", type=int, default=7, help="How many days back to include (default: 7)")
    parser.add_argument("--client", default="Client", help='Client name to show on the report (default: "Client")')
    parser.add_argument("--out", default=None, help="Output file path (default: reports/compliance_report_<date>.html)")
    args = parser.parse_args()

    end_date = date.today()
    start_date = end_date - timedelta(days=args.days - 1)

    print(f"Fetching Notion audit trail from {start_date} to {end_date}...")
    rows = fetch_rows(start_date, end_date)
    print(f"  {len(rows)} row(s) found.")

    stats = summarize(rows)
    period_label = f"{start_date.strftime('%d %b %Y')} – {end_date.strftime('%d %b %Y')}"
    generated_at_label = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")

    output_html = render_html(stats, args.client, period_label, generated_at_label)

    out_path = args.out or f"reports/compliance_report_{end_date.isoformat()}.html"
    import os
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(output_html)

    print(f"Report written to {out_path}")
    print(
        f"  {stats['names_screened']} checks, {stats['sanctions_matches']} match(es), "
        f"{stats['fca_items_reviewed']} FCA item(s) reviewed, {stats['fca_items_flagged']} flagged."
    )


if __name__ == "__main__":
    main()
