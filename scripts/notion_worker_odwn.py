"""OpenKuyper Notion Worker — ODWN enrichment for new terms"""
from pathlib import Path
from typing import List, Dict, Optional

from notion_worker_config import ODWN_XML_PATH
from notion_worker_sync import create_sense

_ODWN = None


def _load_odwn():
    global _ODWN
    if _ODWN is not None:
        return _ODWN
    if not ODWN_XML_PATH.exists():
        print(f"WARNING: ODWN XML not found at {ODWN_XML_PATH}")
        return None
    # Lazy import to avoid heavy load unless needed
    import sys
    sys.path.insert(0, str(ODWN_XML_PATH.parent.parent.parent / "tools"))
    from dutch_wordnet import DutchWordNet
    _ODWN = DutchWordNet(str(ODWN_XML_PATH))
    return _ODWN


def _map_domain(odwn_domains: List[str]) -> str:
    """Map ODWN domain tags to our select options."""
    domain_map = {
        "politiek": "politics",
        "recht": "law",
        "theologie": "theology",
        "filosofie": "philosophy",
        "psychologie": "psychology",
        "geschiedenis": "history",
    }
    for d in odwn_domains:
        d_lower = d.lower()
        if d_lower in domain_map:
            return domain_map[d_lower]
    return "general"


def enrich_term(term_page_id: str, term: str) -> int:
    """Look up term in ODWN and create sense rows. Returns count of senses created."""
    dwn = _load_odwn()
    if dwn is None:
        print(f"  SKIP: ODWN unavailable, cannot enrich '{term}'")
        return 0

    entries = dwn.lookup(term)
    if not entries:
        print(f"  ODWN: no entries found for '{term}'")
        return 0

    created = 0
    seen_synsets = set()

    for entry in entries:
        pos = entry.get("pos", "noun")
        for sense in entry.get("senses", []):
            synset_id = sense.get("synset_id", "")
            if synset_id in seen_synsets:
                continue
            seen_synsets.add(synset_id)

            # Get full synset info for gloss
            synset_info = dwn.get_synset(synset_id)
            gloss = synset_info.get("gloss", sense.get("definition", "")) if synset_info else sense.get("definition", "")

            # Map domain
            domains = sense.get("domains", [])
            mapped_domain = _map_domain(domains)

            # Build sense key from synset or term+pos
            sense_key = synset_id.replace("eng-30-", "").replace("odwn-10-", "").replace("-", "_")
            sense_id = f"{term}-{sense_key}"

            props = {
                "Sense ID": {"title": [{"text": {"content": sense_id}}]},
                "Parent Term": {"relation": [{"id": term_page_id}]},
                "Preferred English": {"rich_text": [{"text": {"content": ""}}]},  # Human fills
                "Gloss (Dutch)": {"rich_text": [{"text": {"content": gloss}}]},
                "Domain": {"select": {"name": mapped_domain}},
                "Context Trigger": {"rich_text": [{"text": {"content": "(auto-generated from ODWN; human review required)"}}]},
                "Part of Speech": {"select": {"name": pos if pos in ["noun", "verb", "adjective", "adverb", "proper noun"] else "noun"}},
                "Confidence": {"select": {"name": "Low"}},
                "Status": {"status": {"name": "Proposed"}},
                "ODWN Synset ID": {"rich_text": [{"text": {"content": synset_id}}]},
                "ILI (Princeton WN)": {"rich_text": [{"text": {"content": synset_info.get("ili", "") if synset_info else ""}}]},
            }

            pid = create_sense(props)
            if pid:
                created += 1
                print(f"  + Created sense: {sense_id} ({mapped_domain})")

    return created
