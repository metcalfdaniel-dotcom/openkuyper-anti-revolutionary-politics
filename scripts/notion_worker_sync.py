"""OpenKuyper Notion Worker — Notion API sync helpers"""
import requests
from typing import List, Dict, Optional

from notion_worker_config import NOTION_API_BASE, HEADERS, LEXICON_DB_ID, SENSES_DB_ID


def query_database(db_id: str, filter_body: Optional[Dict] = None, page_size: int = 100) -> List[Dict]:
    """Query a Notion database with auto-pagination."""
    results = []
    cursor = None
    while True:
        body = {"page_size": page_size}
        if filter_body:
            body["filter"] = filter_body
        if cursor:
            body["start_cursor"] = cursor

        resp = requests.post(
            f"{NOTION_API_BASE}/databases/{db_id}/query",
            headers=HEADERS,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("results", []))
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
    return results


def fetch_changed_terms(since: str) -> List[Dict]:
    """Fetch all terms in Lexicon DB edited since timestamp."""
    return query_database(
        LEXICON_DB_ID,
        filter_body={
            "timestamp": "last_edited_time",
            "last_edited_time": {"after": since},
        },
    )


def fetch_changed_senses(since: str) -> List[Dict]:
    """Fetch all senses in Senses DB edited since timestamp."""
    return query_database(
        SENSES_DB_ID,
        filter_body={
            "timestamp": "last_edited_time",
            "last_edited_time": {"after": since},
        },
    )


def fetch_all_locked_approved_senses() -> List[Dict]:
    """Fetch all senses with Status = Locked or Approved."""
    # Notion status filter uses status object
    locked = query_database(
        SENSES_DB_ID,
        filter_body={"property": "Status", "status": {"equals": "Locked"}},
    )
    approved = query_database(
        SENSES_DB_ID,
        filter_body={"property": "Status", "status": {"equals": "Approved"}},
    )
    # Merge and dedupe by ID
    by_id = {s["id"]: s for s in locked}
    by_id.update({s["id"]: s for s in approved})
    return list(by_id.values())


def fetch_all_terms() -> List[Dict]:
    """Fetch all terms from Lexicon DB (for relation resolution)."""
    return query_database(LEXICON_DB_ID)


def create_sense(properties: Dict) -> Optional[str]:
    """Create a new sense row in Senses DB. Returns page ID or None."""
    resp = requests.post(
        f"{NOTION_API_BASE}/pages",
        headers=HEADERS,
        json={"parent": {"database_id": SENSES_DB_ID}, "properties": properties},
    )
    if resp.status_code == 200:
        return resp.json()["id"]
    print(f"ERROR creating sense: {resp.status_code} {resp.text[:200]}")
    return None


def update_term_page(page_id: str, properties: Dict) -> bool:
    """Patch properties on a Lexicon term page."""
    resp = requests.patch(
        f"{NOTION_API_BASE}/pages/{page_id}",
        headers=HEADERS,
        json={"properties": properties},
    )
    if resp.status_code == 200:
        return True
    print(f"ERROR updating term {page_id}: {resp.status_code} {resp.text[:200]}")
    return False


def add_drift_alert(page_id: str, alert_text: str):
    """Append a drift alert to a term's Drift Alerts rich text."""
    # First read current value
    resp = requests.get(f"{NOTION_API_BASE}/pages/{page_id}", headers=HEADERS)
    if resp.status_code != 200:
        return
    page = resp.json()
    drift = page.get("properties", {}).get("Drift Alerts", {}).get("rich_text", [])
    existing = "".join([r.get("plain_text", "") for r in drift])
    new_text = f"{existing}\n{alert_text}".strip()
    update_term_page(page_id, {"Drift Alerts": {"rich_text": [{"text": {"content": new_text}}]}})


def parse_page_properties(page: Dict) -> Dict:
    """Flatten a Notion page's properties into a simple dict."""
    props = page.get("properties", {})
    flat = {"_id": page["id"], "_url": page["url"], "_created": page.get("created_time", ""), "_edited": page.get("last_edited_time", "")}
    for key, val in props.items():
        ptype = val.get("type", "")
        if ptype == "title":
            flat[key] = "".join([t.get("plain_text", "") for t in val.get("title", [])])
        elif ptype == "rich_text":
            flat[key] = "".join([t.get("plain_text", "") for t in val.get("rich_text", [])])
        elif ptype == "select":
            flat[key] = val.get("select", {}).get("name", "") if val.get("select") else ""
        elif ptype == "multi_select":
            flat[key] = [opt.get("name", "") for opt in val.get("multi_select", [])]
        elif ptype == "status":
            flat[key] = val.get("status", {}).get("name", "") if val.get("status") else ""
        elif ptype == "checkbox":
            flat[key] = val.get("checkbox", False)
        elif ptype == "relation":
            flat[key] = [r.get("id", "") for r in val.get("relation", [])]
        elif ptype == "formula":
            flat[key] = val.get("formula", {}).get("number", 0) if val.get("formula") else 0
        elif ptype == "number":
            flat[key] = val.get("number", 0)
        else:
            flat[key] = val
    return flat
