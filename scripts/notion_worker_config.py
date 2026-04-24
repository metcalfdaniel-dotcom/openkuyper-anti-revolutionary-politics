"""OpenKuyper Notion Worker — Configuration"""
import os
from pathlib import Path

# Notion Database IDs
LEXICON_DB_ID = "b675507f-bad8-4478-abeb-00745a893f65"
SENSES_DB_ID = "353a9d93-dfa5-42e7-8688-cf13b04d9cf6"

# File paths (relative to repo root)
REPO_ROOT = Path(__file__).parent.parent
ODWN_XML_PATH = REPO_ROOT / "reference" / "odwn" / "odwn_orbn_gwg-LMF_1.3.xml"
JSON_OUTPUT_PATH = REPO_ROOT / "termbase" / "kuyper_termbase.json"
CHECKPOINT_DB_PATH = REPO_ROOT / ".opencode" / "notion_worker.db"

# Sync settings
SYNC_INTERVAL_SECONDS = 300  # 5 minutes in daemon mode
GIT_COMMIT_ON_CHANGE = True
GIT_BRANCH = "auto/termbase-sync"

# API
NOTION_TOKEN = os.environ.get("NOTION_API_TOKEN", "")
NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_API_VERSION = "2022-06-28"

# Headers for all Notion API calls
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_API_VERSION,
    "Content-Type": "application/json",
}
