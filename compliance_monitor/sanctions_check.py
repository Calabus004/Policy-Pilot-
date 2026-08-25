"""
Step 2: Check a list of names against the UK Sanctions List and the EU
Consolidated Financial Sanctions List, using the OpenSanctions Match API.

Docs: https://www.opensanctions.org/docs/api/matching/
"""
import time

import requests

from compliance_monitor import config

MAX_RETRIES = 3
MAX_RETRY_DELAY_SECONDS = 30


def _post_with_retry(url, headers, json_body, timeout=30):
    """
    Retry on HTTP 429 (rate limited) with backoff, since this is the one
    error here that's expected to be transient rather than a real problem —
    e.g. testing the workflow with several runs in quick succession. Honours
    the API's Retry-After header when present, but caps the wait so a very
    long requested delay (a genuine daily quota, not a brief burst limit)
    fails fast with a clear error instead of stalling a CI job.
    """
    response = None
    for attempt in range(MAX_RETRIES):
        response = requests.post(url, headers=headers, json=json_body, timeout=timeout)
        if response.status_code != 429:
            response.raise_for_status()
            return response

        retry_after = response.headers.get("Retry-After")
        delay = min(float(retry_after), MAX_RETRY_DELAY_SECONDS) if retry_after else 2 ** (attempt + 1)
        if attempt == MAX_RETRIES - 1:
            break
        print(f"  Rate limited by OpenSanctions, retrying in {delay:.0f}s...")
        time.sleep(delay)

    response.raise_for_status()
    return response


def check_sanctions(names, threshold=None):
    """
    Screen every entry in `names` (a list of {"name": ..., "schema": ...}
    dicts, see test_names.py) against each dataset in
    config.OPENSANCTIONS_DATASETS.

    Returns a list of dicts, one per match scoring at or above `threshold`:
        {
            "queried_name": the name we searched for,
            "list_name": which of the two lists it matched on,
            "matched_entity": the sanctioned entity's name on OpenSanctions,
            "score": match confidence, 0.0-1.0,
            "opensanctions_id": OpenSanctions entity ID (for follow-up review),
            "datasets": the underlying OpenSanctions datasets the entity appears in,
        }
    An empty list means no matches were found — that's the expected, good
    outcome on most days.
    """
    if threshold is None:
        threshold = config.OPENSANCTIONS_MATCH_THRESHOLD

    if not config.OPENSANCTIONS_API_KEY:
        raise RuntimeError(
            "OPENSANCTIONS_API_KEY is not set. Add it to your .env file."
        )

    headers = {
        "Authorization": f"ApiKey {config.OPENSANCTIONS_API_KEY}",
        "Content-Type": "application/json",
    }

    # Build one query per name, keyed by index, so we can map results back
    # to the original name after the API responds.
    queries = {}
    index_to_name = {}
    for i, entry in enumerate(names):
        query_id = f"q{i}"
        queries[query_id] = {
            "schema": entry.get("schema", "Person"),
            "properties": {"name": [entry["name"]]},
        }
        index_to_name[query_id] = entry["name"]

    all_matches = []

    # The match endpoint is scoped to one dataset per call, so we call it
    # once per list we want to screen against, sending all names in a
    # single batched request each time (much faster than one call per name).
    for list_name, dataset_id in config.OPENSANCTIONS_DATASETS.items():
        url = f"{config.OPENSANCTIONS_BASE_URL}/match/{dataset_id}"
        response = _post_with_retry(url, headers, {"queries": queries})
        data = response.json()

        for query_id, result in data.get("responses", {}).items():
            for candidate in result.get("results", []):
                score = candidate.get("score", 0)
                if score >= threshold:
                    all_matches.append(
                        {
                            "queried_name": index_to_name.get(query_id, "unknown"),
                            "list_name": list_name,
                            "matched_entity": candidate.get("caption", "unknown"),
                            "score": round(score, 3),
                            "opensanctions_id": candidate.get("id"),
                            "datasets": candidate.get("datasets", []),
                        }
                    )

    return all_matches
