#!/usr/bin/env python3
"""
OpenKuyper Notion Worker — Bidirectional Termbase Sync Agent

Usage:
    python scripts/notion_worker.py --once          # Single sync run
    python scripts/notion_worker.py --once --dry-run # Preview without writes
    python scripts/notion_worker.py --daemon        # Continuous sync every 5 min

Phases:
    1. DETECT   — Query Notion for changed terms/senses since last checkpoint
    2. ENRICH   — For unenriched terms, auto-create sense rows via ODWN
    3. COMPILE  — Flatten all Locked/Approved senses into kuyper_termbase.json
    4. REPORT   — (Placeholder) Drift detection on latest translation drafts
"""

import argparse
import time
from datetime import datetime, timezone

from notion_worker_config import (
    NOTION_TOKEN,
    CHECKPOINT_DB_PATH,
    SYNC_INTERVAL_SECONDS,
)
from notion_worker_db import get_last_checkpoint, save_checkpoint, is_enriched, mark_enriched
from notion_worker_sync import (
    fetch_changed_terms,
    fetch_changed_senses,
    update_term_page,
    parse_page_properties,
)
from notion_worker_odwn import enrich_term
from notion_worker_compile import compile_termbase_json, write_json


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def phase_detect(since: str) -> tuple:
    """Return (changed_terms[], changed_senses[], newest_timestamp)."""
    print(f"\n[DETECT] Fetching changes since {since}...")
    terms = fetch_changed_terms(since)
    senses = fetch_changed_senses(since)
    print(f"  Changed terms: {len(terms)}, changed senses: {len(senses)}")

    # Determine newest timestamp for checkpoint
    newest = since
    for item in terms + senses:
        edited = item.get("last_edited_time", "")
        if edited > newest:
            newest = edited

    return terms, senses, newest


def phase_enrich(terms: list, dry_run: bool = False) -> int:
    """Enrich unenriched terms via ODWN. Returns count of senses created."""
    print(f"\n[ENRICH] Checking {len(terms)} terms for ODWN enrichment...")
    total_created = 0

    for term_page in terms:
        flat = parse_page_properties(term_page)
        term = flat.get("Term (Dutch/Latin)", "").strip()
        page_id = flat.get("_id", "")
        odwn_flag = flat.get("ODWN Enriched", False)

        if not term or odwn_flag or is_enriched(page_id):
            continue

        print(f"  Enriching '{term}'...")
        if dry_run:
            print(f"    [DRY-RUN] Would query ODWN and create senses for '{term}'")
            total_created += 1
            continue

        created = enrich_term(page_id, term)
        if created > 0:
            # Update term page to mark enriched
            update_term_page(page_id, {"ODWN Enriched": {"checkbox": True}})
            mark_enriched(page_id, term)
            total_created += created
        else:
            # Mark as enriched anyway so we don't retry indefinitely
            mark_enriched(page_id, term)

    print(f"  Created {total_created} sense rows")
    return total_created


def phase_compile(dry_run: bool = False) -> bool:
    """Compile JSON from Notion. Returns success."""
    data = compile_termbase_json()
    return write_json(data, dry_run=dry_run)


def phase_report(dry_run: bool = False):
    """Placeholder drift detection."""
    print("\n[REPORT] Drift detection not yet implemented (requires translation draft input)")


def run_once(dry_run: bool = False) -> dict:
    """Execute one full sync cycle. Returns metrics."""
    since = get_last_checkpoint()
    terms, senses, newest = phase_detect(since)

    metrics = {
        "terms_changed": len(terms),
        "senses_changed": len(senses),
        "senses_created": 0,
        "json_written": False,
        "checkpoint": newest,
    }

    if not terms and not senses:
        print("\n[SYNC] No changes detected. Nothing to do.")
        save_checkpoint(newest, 0, 0, 0)
        return metrics

    # Phase 2: Enrich
    metrics["senses_created"] = phase_enrich(terms, dry_run=dry_run)

    # Phase 3: Compile
    metrics["json_written"] = phase_compile(dry_run=dry_run)

    # Phase 4: Report
    phase_report(dry_run=dry_run)

    # Save checkpoint
    if not dry_run:
        save_checkpoint(
            newest,
            pages=metrics["terms_changed"],
            senses=metrics["senses_changed"] + metrics["senses_created"],
            drifts=0,
        )
        print(f"\n[SYNC] Checkpoint saved: {newest}")
    else:
        print(f"\n[DRY-RUN] Would save checkpoint: {newest}")

    return metrics


def run_daemon(interval: int = SYNC_INTERVAL_SECONDS):
    """Run continuous sync loop."""
    print(f"[DAEMON] Starting Notion Worker (interval={interval}s)")
    print(f"[DAEMON] Press Ctrl+C to stop\n")
    while True:
        try:
            run_once(dry_run=False)
        except Exception as e:
            print(f"[ERROR] Sync cycle failed: {e}")
        print(f"\n[DAEMON] Sleeping {interval}s...\n")
        time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(description="OpenKuyper Notion Worker")
    parser.add_argument("--once", action="store_true", help="Run single sync cycle")
    parser.add_argument("--daemon", action="store_true", help="Run continuous sync")
    parser.add_argument("--interval", type=int, default=SYNC_INTERVAL_SECONDS, help="Daemon interval (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing")
    args = parser.parse_args()

    if not NOTION_TOKEN:
        print("ERROR: NOTION_API_TOKEN environment variable not set")
        return 1

    if args.daemon:
        run_daemon(args.interval)
    else:
        # Default to --once if neither flag given
        run_once(dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    exit(main())
