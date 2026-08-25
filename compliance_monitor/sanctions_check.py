"""
Step 2: Check a list of names against the UK Sanctions List and the EU
Consolidated Financial Sanctions List, using the OpenSanctions Match API.

Docs: https://www.opensanctions.org/docs/api/matching/
"""
import requests

from compliance_monitor import config


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
        response = requests.post(
            url, headers=headers, json={"queries": queries}, timeout=30
        )
        response.raise_for_status()
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
