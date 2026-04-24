"""OpenKuyper Notion Worker — Drift detection (placeholder)"""
from typing import List, Dict

from notion_worker_sync import add_drift_alert


def detect_drift(english_text: str, term_senses: Dict[str, List[Dict]]) -> List[Dict]:
    """
    Scan English text for potential terminology drift.
    Placeholder implementation — keyword-based heuristic.
    """
    alerts = []
    text_lower = english_text.lower()

    for term, senses in term_senses.items():
        # Only check locked/high-confidence senses
        locked = [s for s in senses if s.get("status", "").lower() in ("locked", "approved")]
        if not locked:
            continue

        term_lower = term.lower()
        if term_lower not in text_lower:
            continue

        # Simple heuristic: check if preferred english appears near dutch term
        for sense in locked:
            pref = sense.get("preferred_english", "").lower()
            if not pref:
                continue

            # Find positions of dutch term
            idx = text_lower.find(term_lower)
            window = text_lower[max(0, idx - 200):min(len(text_lower), idx + 200)]

            # Check if preferred rendering is in window
            if pref not in window and pref != term_lower:
                # Check disallowed variants
                disallowed = sense.get("disallowed", [])
                found_bad = [d for d in disallowed if d.lower() in window]
                if found_bad:
                    alerts.append({
                        "term": term,
                        "sense_id": sense.get("sense_id", ""),
                        "expected": pref,
                        "found_bad": found_bad,
                        "context": window[:120],
                    })

    return alerts


def report_drifts(alerts: List[Dict]):
    """Write drift alerts back to Notion (placeholder — needs term page ID mapping)."""
    if not alerts:
        print("  No drift detected.")
        return

    print(f"  {len(alerts)} drift alerts found:")
    for a in alerts:
        print(f"    ! {a['term']} ({a['sense_id']}): expected '{a['expected']}', found {a['found_bad']}")
    # TODO: map sense_id → term page ID → add_drift_alert(page_id, text)
