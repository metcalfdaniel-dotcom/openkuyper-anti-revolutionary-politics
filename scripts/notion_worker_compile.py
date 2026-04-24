"""OpenKuyper Notion Worker — Compile JSON from Notion data"""
import json
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timezone

from notion_worker_config import JSON_OUTPUT_PATH
from notion_worker_sync import fetch_all_locked_approved_senses, fetch_all_terms, parse_page_properties


def compile_termbase_json() -> Dict:
    """Fetch all Locked/Approved senses from Notion and compile into JSON."""
    print("\n[COMPILE] Fetching senses from Notion...")
    senses = fetch_all_locked_approved_senses()
    terms = fetch_all_terms()
    print(f"  Fetched {len(senses)} senses, {len(terms)} terms")

    # Index terms by ID for lookup
    terms_by_id = {t["id"]: parse_page_properties(t) for t in terms}

    # Group senses by parent term
    grouped: Dict[str, List[Dict]] = {}
    for s in senses:
        flat = parse_page_properties(s)
        parent_ids = flat.get("Parent Term", [])
        for pid in parent_ids:
            grouped.setdefault(pid, []).append(flat)

    # Build output
    output = {
        "_meta": {
            "generated_by": "notion_worker",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_terms": len(terms),
            "total_senses": len(senses),
        },
        "terms": {},
    }

    for pid, sense_list in grouped.items():
        term = terms_by_id.get(pid)
        if not term:
            continue
        term_key = term.get("Term (Dutch/Latin)", "")
        if not term_key:
            continue

        output["terms"][term_key] = {
            "dutch": term_key,
            "status": term.get("Status", "").lower(),
            "tags": term.get("Key Term Tag", []),
            "appears_in": term.get("Appears in", []),
            "default_treatment": term.get("Treatment (default)", term.get("Treatment", "")),
            "notes": term.get("Notes", ""),
            "senses": [],
        }

        for s in sense_list:
            output["terms"][term_key]["senses"].append({
                "sense_id": s.get("Sense ID", ""),
                "preferred_english": s.get("Preferred English", ""),
                "domain": s.get("Domain", ""),
                "context_trigger": s.get("Context Trigger", ""),
                "treatment": s.get("Treatment", ""),
                "status": s.get("Status", "").lower(),
                "confidence": s.get("Confidence", "").lower(),
                "disallowed": [v.strip() for v in s.get("Disallowed variants", "").split(",") if v.strip()],
                "first_occurrence_gloss": s.get("First-occurrence gloss", ""),
                "gloss_dutch": s.get("Gloss (Dutch)", ""),
                "examples": s.get("Examples (authoritative)", ""),
                "ili": s.get("ILI (Princeton WN)", ""),
                "odwn_synset_id": s.get("ODWN Synset ID", ""),
            })

    return output


def write_json(data: Dict, dry_run: bool = False) -> bool:
    """Write compiled JSON to disk (and optionally git commit)."""
    if dry_run:
        print(f"\n[DRY-RUN] Would write {len(data['terms'])} terms to {JSON_OUTPUT_PATH}")
        # Show first 3 terms
        for i, (k, v) in enumerate(data["terms"].items()):
            if i >= 3:
                break
            print(f"  {k}: {len(v['senses'])} senses")
        return True

    JSON_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Atomic write
    temp_path = JSON_OUTPUT_PATH.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    temp_path.replace(JSON_OUTPUT_PATH)

    print(f"\n[COMPILE] Wrote {len(data['terms'])} terms to {JSON_OUTPUT_PATH}")
    return True
