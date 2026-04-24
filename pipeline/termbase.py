#!/usr/bin/env python3
"""
OpenKuyper Termbase Manager — Sense-Aware Edition

Dynamic terminology lockfile with polysemy support:
- Load/save termbase from JSON (flat legacy OR sense-aware v2)
- Sense-aware lookup: get_sense(term, context) returns best-matching sense
- Automatic enforcement in prompts with sense disambiguation
- Drift detection across translations
- Confidence scoring and human review flags
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Sense:
    """A single semantic sense for a polysemous term."""
    sense_id: str
    preferred_english: str
    domain: str = "general"
    context_trigger: str = ""
    treatment: str = ""
    status: str = "proposed"  # proposed, approved, locked
    confidence: str = "low"   # low, medium, high
    disallowed: list = field(default_factory=list)
    first_occurrence_gloss: str = ""
    gloss_dutch: str = ""
    examples: str = ""
    ili: str = ""
    odwn_synset_id: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Sense":
        # Filter to only known fields for forward compatibility
        known = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known}
        return cls(**filtered)


@dataclass
class TermEntry:
    """Single terminology entry with metadata and optional senses."""
    dutch: str
    english: str = ""           # Deprecated: use senses[].preferred_english
    confidence: str = "medium"  # Deprecated: use senses[].confidence
    context: str = ""           # Example sentence for disambiguation
    notes: str = ""             # Translator notes
    first_seen: str = ""        # Chapter/page where first encountered
    review_flag: bool = False   # True if human review needed
    alternates: list = field(default_factory=list)  # Other valid translations
    senses: list = field(default_factory=list)      # NEW: polysemy support
    status: str = ""            # NEW: term-level status
    tags: list = field(default_factory=list)        # NEW: Key Term Tags
    appears_in: list = field(default_factory=list)  # NEW: chapter tags
    default_treatment: str = "" # NEW: italicize, annotate, etc.

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TermEntry":
        senses_data = data.pop("senses", [])
        entry = cls(**data)
        entry.senses = [Sense.from_dict(s) for s in senses_data]
        return entry

    @property
    def is_polysemous(self) -> bool:
        return len(self.senses) > 1

    def get_best_sense(self, context_text: str = "") -> Optional[Sense]:
        """Return the best-matching sense for a given context.

        Scoring (simple heuristic):
        1. Locked/Approved senses only
        2. Context trigger keyword overlap
        3. Domain keyword overlap
        4. Fallback to highest-confidence sense
        """
        if not self.senses:
            return None

        candidates = [s for s in self.senses if s.status in ("locked", "approved")]
        if not candidates:
            candidates = self.senses

        if not context_text:
            # Return first locked, then first approved, then first available
            for s in candidates:
                if s.status == "locked":
                    return s
            return candidates[0]

        context_lower = context_text.lower()
        scored = []

        def _extract_words(text: str) -> set:
            """Extract meaningful words from text (remove punctuation, filter short)."""
            cleaned = re.sub(r"[^\w\s]", " ", text.lower())
            return {w for w in cleaned.split() if len(w) >= 3}

        context_words = _extract_words(context_text)

        for sense in candidates:
            score = 0
            # Status bonus (reduced so context can override)
            if sense.status == "locked":
                score += 50
            elif sense.status == "approved":
                score += 25

            # Context trigger overlap (heavily weighted)
            trigger_words = _extract_words(sense.context_trigger)
            for tw in trigger_words:
                if tw in context_words:
                    score += 30
                # Also check for partial matches (e.g., "staats-" matches "staat")
                elif any(tw in cw or cw in tw for cw in context_words):
                    score += 15

            # Domain keyword overlap (exclude the lemma itself to avoid bias)
            domain_keywords = {
                "theology": ["god", "christ", "church", "sacrament", "faith", "grace", "sin", "spirit", "holy", "heilige", "goddelijk", "dominus", "theologisch", "kerk", "bijbel", "scriptuur"],
                "law": ["law", "legal", "constitutional", "statute", "court", "judge", "crime", "wet", "wetgeving", "grondwet", "statuut", "juridisch", "wettelijk", "wetboek", "rechter"],
                "politics": ["state", "government", "nation", "citizen", "political", "party", "revolution", "overheid", "natie", "burger", "politiek", "staatkunde", "ministerie", "parlement"],
                "philosophy": ["mind", "intellect", "reason", "faculty", "consciousness", "nature", "will", "geest", "verstand", "reden", "natuur", "wil", "filosofisch", "beginsel", "god", "absoluut", "idee"],
                "psychology": ["soul", "heart", "conscience", "feeling", "emotion", "mental", "ziel", "hart", "geweten", "gevoel", "psychologisch"],
                "history": ["historical", "past", "century", "period", "age", "era", "geschiedenis", "verleden", "eeuw", "tijdperk"],
                "general": [],
            }
            for kw in domain_keywords.get(sense.domain, []):
                if kw in context_lower:
                    score += 8

            # Preferred English word overlap in context (rare but useful)
            english_words = _extract_words(sense.preferred_english)
            for ew in english_words:
                if ew in context_words:
                    score += 5

            scored.append((score, sense))

        scored.sort(key=lambda x: x[0], reverse=True)
        return scored[0][1] if scored else None


class Termbase:
    """Manages the dynamic terminology lockfile."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or Path(__file__).parent.parent / "termbase" / "kuyper_termbase.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.entries: dict[str, TermEntry] = {}  # keyed by dutch term
        self._load()

    def _load(self):
        """Load termbase from disk or seed with defaults."""
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Detect format: v2 has "terms" key, legacy is flat dict
            if "terms" in data:
                terms_data = data["terms"]
            else:
                terms_data = data

            for key, entry_data in terms_data.items():
                self.entries[key] = TermEntry.from_dict(entry_data)
            print(f"Loaded {len(self.entries)} entries from {self.path}")
        else:
            self._seed_defaults()
            self.save()
            print(f"Seeded {len(self.entries)} default entries to {self.path}")

    def _seed_defaults(self):
        """Seed with the verified Phase 1 terminology."""
        defaults = [
            ("geloof", "faith", "high"),
            ("genade", "grace", "high"),
            ("heiligmaking", "sanctification", "high"),
            ("rechtvaardiging", "justification", "high"),
            ("verlossing", "salvation", "high"),
            ("verzoening", "atonement", "high"),
            ("verkiezing", "election", "high"),
            ("voorzienigheid", "providence", "high"),
            ("openbaring", "revelation", "high"),
            ("schrift", "Scripture", "high"),
            ("verbond", "covenant", "high"),
            ("kerk", "church", "high"),
            ("sacrament", "sacrament", "high"),
            ("doop", "baptism", "high"),
            ("zonde", "sin", "high"),
            ("schuld", "guilt", "high"),
            ("sfeer", "sphere", "high"),
            ("soevereiniteit", "sovereignty", "high"),
            ("soevereiniteit in eigen kring", "sphere sovereignty", "high"),
            ("staat", "state", "high"),
            ("overheid", "government", "high"),
            ("revolutie", "revolution", "high"),
            ("antirevolutionair", "antirevolutionary", "high"),
            ("beginsel", "principle", "high"),
            ("grondwet", "constitution", "high"),
            ("recht", "law / right", "medium"),
            ("volk", "people / nation", "medium"),
            ("natie", "nation", "high"),
            ("maatschappij", "society", "high"),
            ("gezin", "family", "high"),
            ("school", "school", "high"),
            ("ziel", "soul", "high"),
            ("geest", "spirit", "high"),
            ("hart", "heart", "high"),
            ("geweten", "conscience", "high"),
            ("bewustzijn", "consciousness", "high"),
            ("vermogen", "faculty / power", "medium"),
            ("wil", "will", "high"),
            ("verstand", "intellect / understanding", "medium"),
            ("natuur", "nature", "high"),
            ("algemeene genade", "common grace", "high"),
            ("bijzondere genade", "particular grace / special grace", "high"),
            ("levenssysteem", "life-system / life and thought system", "high"),
            ("wereldbeschouwing", "worldview / world-and-life view", "high"),
            ("gereformeerd", "Reformed / Calvinistic", "high"),
            ("calvinistisch", "Calvinistic", "high"),
            ("katholiek", "catholic / universal", "medium"),
            ("daarom", "therefore / hence", "high"),
            ("zodat", "so that", "high"),
            ("echter", "however / yet", "high"),
            ("immers", "for / since / indeed", "medium"),
            ("namelijk", "namely / that is to say", "high"),
            ("wel", "indeed / truly / certainly", "medium"),
            ("toch", "yet / still / nevertheless", "medium"),
        ]
        for dutch, english, confidence in defaults:
            self.entries[dutch] = TermEntry(dutch=dutch, english=english, confidence=confidence)

    def save(self):
        """Save termbase to disk in v2 format."""
        data = {
            "_meta": {
                "version": "2.0",
                "schema": "sense-aware",
            },
            "terms": {k: v.to_dict() for k, v in self.entries.items()},
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get(self, dutch: str) -> Optional[TermEntry]:
        """Get entry by Dutch term."""
        return self.entries.get(dutch.lower().strip())

    def get_sense(self, dutch: str, context: str = "") -> Optional[Sense]:
        """Get the best-matching sense for a term in context.

        If the term has no senses, returns a synthetic Sense from the flat entry.
        """
        entry = self.get(dutch)
        if not entry:
            return None

        if entry.senses:
            return entry.get_best_sense(context)

        # Fallback: synthetic sense from flat entry
        return Sense(
            sense_id=f"{dutch}-default",
            preferred_english=entry.english,
            context_trigger=entry.context,
            confidence=entry.confidence,
            status="approved" if entry.confidence in ("high", "locked") else "proposed",
        )

    def add(self, entry: TermEntry, overwrite: bool = False):
        """Add or update an entry."""
        key = entry.dutch.lower().strip()
        if key in self.entries and not overwrite:
            return False
        self.entries[key] = entry
        self.save()
        return True

    def lock_term(self, dutch: str):
        """Lock a term to prevent drift (highest confidence)."""
        key = dutch.lower().strip()
        if key in self.entries:
            self.entries[key].confidence = "locked"
            for s in self.entries[key].senses:
                s.status = "locked"
            self.save()

    def detect_drift(self, text: str, context: str = "") -> list[dict]:
        """Scan text for potential terminology drift.

        Returns list of alerts: [{term, expected, found, context}]
        """
        alerts = []
        text_lower = text.lower()

        for key, entry in self.entries.items():
            # Only check high/locked confidence terms
            if entry.confidence not in ("high", "locked") and not any(
                s.status in ("locked", "approved") for s in entry.senses
            ):
                continue

            # Check if Dutch term appears but English translation doesn't
            if key in text_lower:
                # Use sense-aware expected translation
                sense = entry.get_best_sense(context) if entry.senses else None
                if sense:
                    expected = sense.preferred_english.lower()
                else:
                    expected = entry.english.lower()

                # Split multi-word translations
                expected_parts = expected.split(" / ")[0].split()

                # Look within a window around the Dutch term
                idx = text_lower.find(key)
                window_start = max(0, idx - 200)
                window_end = min(len(text_lower), idx + 200)
                window = text_lower[window_start:window_end]

                # Check if any expected part is in window
                found = any(part in window for part in expected_parts if len(part) > 3)

                if not found:
                    alerts.append({
                        "term": key,
                        "expected": sense.preferred_english if sense else entry.english,
                        "found": "MISSING",
                        "context": context or f"near position {idx}",
                        "severity": "high" if (sense and sense.status == "locked") or entry.confidence == "locked" else "medium"
                    })

        return alerts

    def get_prompt_block(self, max_entries: int = 100) -> str:
        """Generate a terminology block for injection into prompts."""
        lines = ["## MANDATORY TERMINOLOGY (do not deviate)", ""]

        # Prioritize locked and high-confidence terms
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: (
                0 if e.confidence == "locked" else 1 if e.confidence == "high" else 2,
                -len(e.senses),
            ),
        )

        for entry in sorted_entries[:max_entries]:
            marker = "🔒" if entry.confidence == "locked" else "⭐" if entry.confidence == "high" else ""
            polysemy_marker = " [POLYSEMOUS]" if entry.is_polysemous else ""

            if entry.senses:
                # Show all locked/approved senses
                for sense in entry.senses:
                    if sense.status not in ("locked", "approved"):
                        continue
                    sense_marker = "🔒" if sense.status == "locked" else "⭐"
                    lines.append(f"- {sense_marker} **{entry.dutch}** ({sense.sense_id}) → {sense.preferred_english}")
                    if sense.context_trigger:
                        lines.append(f"  Context: {sense.context_trigger}")
            else:
                lines.append(f"- {marker} **{entry.dutch}**{polysemy_marker} → {entry.english}")

            if entry.notes:
                lines.append(f"  Note: {entry.notes}")

        return "\n".join(lines)

    def stats(self) -> dict:
        """Return termbase statistics."""
        total = len(self.entries)
        locked = sum(1 for e in self.entries.values() if e.confidence == "locked")
        high = sum(1 for e in self.entries.values() if e.confidence == "high")
        flagged = sum(1 for e in self.entries.values() if e.review_flag)
        polysemous = sum(1 for e in self.entries.values() if e.is_polysemous)
        total_senses = sum(len(e.senses) for e in self.entries.values())
        return {
            "total_entries": total,
            "locked": locked,
            "high_confidence": high,
            "review_flags": flagged,
            "polysemous_terms": polysemous,
            "total_senses": total_senses,
            "path": str(self.path)
        }


if __name__ == "__main__":
    # Test
    tb = Termbase()
    print(tb.stats())
    print("\nPrompt block (first 10 entries):")
    print(tb.get_prompt_block(max_entries=10))

    # Test sense-aware lookup
    print("\n--- Sense-aware lookup tests ---")
    for term in ["recht", "volk", "geest", "vermogen"]:
        sense = tb.get_sense(term, context="")
        if sense:
            print(f"  {term} → {sense.preferred_english} (status: {sense.status})")
        else:
            print(f"  {term} → NOT FOUND")
