"""
Step 4: Send the sanctions matches and FCA news items to Claude, and ask it
to identify what's relevant to a UK/EU fintech, explain why in plain
English, and suggest one concrete next action per relevant item.

Uses Claude's structured outputs (a JSON schema derived from the Pydantic
models below) so the response is guaranteed to be valid, parseable JSON —
no fragile string-matching or "hope it didn't add commentary" parsing.
"""
import json

import anthropic
from pydantic import BaseModel

from compliance_monitor import config

SYSTEM_PROMPT = """You are a compliance analyst assistant for a UK/EU fintech company.

You will be given two lists as JSON:
1. "sanctions_matches" — hits from a sanctions screening run (OpenSanctions
   Match API) against test customer names, checked against the UK Sanctions
   List and the EU Consolidated Financial Sanctions List.
2. "fca_news_items" — recent items from the UK Financial Conduct Authority's
   news and publications feed.

For EACH item in both lists, decide whether it is relevant to a UK or EU
fintech company — e.g. it affects payments, e-money, consumer credit,
AML/KYC, safeguarding of client money, crypto-asset regulation, or
sanctions compliance. Mark items as not relevant if they clearly concern
unrelated sectors (e.g. general insurance or pensions matters) unless there
is a clear read-across for a fintech.

For every item (relevant or not) write a short plain-English explanation
aimed at a non-lawyer compliance officer, and one concrete next action.
For items you mark not relevant, the next action can simply be "No action
needed."

Be conservative with sanctions matches: a name match alone is not proof of
a true hit, so the next action for a relevant sanctions match should always
be a human review step (e.g. "Escalate to compliance for manual review
before onboarding/continuing to serve this customer"), never an automatic
account action."""


class SanctionsSummaryItem(BaseModel):
    queried_name: str
    list_name: str
    relevant: bool
    plain_english_explanation: str
    next_action: str


class FcaNewsSummaryItem(BaseModel):
    title: str
    link: str
    relevant: bool
    plain_english_explanation: str
    next_action: str


class ComplianceSummary(BaseModel):
    sanctions_summary: list[SanctionsSummaryItem]
    fca_news_summary: list[FcaNewsSummaryItem]


def summarize_with_claude(sanctions_matches, fca_news_items):
    """
    Returns a dict with two keys, "sanctions_summary" and "fca_news_summary",
    each a list of per-item dicts with relevant/explanation/next_action —
    see the Pydantic models above for the exact shape.
    """
    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

    user_content = json.dumps(
        {
            "sanctions_matches": sanctions_matches,
            "fca_news_items": fca_news_items,
        },
        indent=2,
    )

    response = client.messages.parse(
        model=config.CLAUDE_MODEL,
        max_tokens=8000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
        output_format=ComplianceSummary,
    )

    return response.parsed_output.model_dump()
