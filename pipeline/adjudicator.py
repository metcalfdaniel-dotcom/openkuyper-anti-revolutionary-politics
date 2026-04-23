#!/usr/bin/env python3
"""
OpenKuyper Adjudication Agent

Multi-draft comparison system:
- Draft A: Faithful/periodic translation (Gemini with style-heavy prompt)
- Draft B: Literal/gloss translation (Gemini with minimal prompt)
- Draft C: Existing Haiku translation (if available)

An agentic evaluator compares all drafts against style database
and selects the winner automatically. No human in the loop.
"""

import json
import os
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

from google import genai

@dataclass
class DraftSet:


@dataclass
class DraftSet:
    """Container for all drafts of a single page/paragraph."""
    page_label: str
    draft_a: str  # Faithful/periodic
    draft_b: str  # Literal/gloss
    draft_c: Optional[str] = None  # Existing Haiku (if available)
    source_dutch: str = ""
    winner: str = ""  # "A", "B", "C", or "MERGED"
    winner_text: str = ""
    evaluation: dict = None
    
    def __post_init__(self):
        if self.evaluation is None:
            self.evaluation = {}


# =============================================================================
# ADJUDICATION PROMPT (the "judge" persona)
# =============================================================================

ADJUDICATION_SYSTEM_PROMPT = """You are a senior scholarly editor specializing in 19th-century Reformed theological translations. Your task is to compare multiple English drafts of the same Dutch text and select the single best translation.

## Selection Criteria (ranked by priority)

1. **Theological Precision** (weight: 30%)
   - Does the translation use the correct technical terms?
   - Is "sphere sovereignty" preserved, not "sovereignty in its own circle"?
   - Are biblical citations in traditional format (Rom. viii. 28)?
   - **CRITICAL - Polysemous Terms:** Evaluate context-dependent translations:
     - "Recht" (Dutch) = both "Law" (institutional/jurisprudential context: state, courts, statutes, Rechtsstaat) AND "Right" (moral/theological context: divine ordinance, God's justice, natural law, contrast with revolutionary arbitrary will). The correct choice must match the immediate context.
     - "Geest" = "spirit" (human spirit or Holy Spirit - context determines)
     - "Katholiek" = often "universal" not "Roman Catholic"
     - "Wetenschap" = "science" in Kuyper's era means "systematized knowledge / academic discipline" not modern empirical science

2. **Voice Fidelity** (weight: 30%)
   - Does it sound like Kuyper? Sweeping, periodic, elevated?
   - Average sentence length should be ~28 words. Shorter is worse.
   - Are archaic connectives present (hence, whereby, therein, nevertheless)?

3. **Structural Integrity** (weight: 20%)
   - Are periodic sentences preserved (main clause delayed)?
   - Are semicolons used for clause coordination?
   - Are parenthetical asides maintained?

4. **Avoid Modernization** (weight: 15%)
   - Does it avoid contemporary English smoothness?
   - Does it preserve the "useful and faithful over polished" mandate?

5. **Consistency** (weight: 5%)
   - Does it match previously established terminology?

## Output Format

Respond in valid JSON:

{
  "winner": "A" or "B" or "C" or "MERGED",
  "winner_text": "The complete winning translation text",
  "rationale": "3-5 sentence explanation of the decision",
  "scores": {
    "A": {"theological": 0-10, "voice": 0-10, "structure": 0-10, "modernization": 0-10, "consistency": 0-10},
    "B": {"theological": 0-10, "voice": 0-10, "structure": 0-10, "modernization": 0-10, "consistency": 0-10},
    "C": {"theological": 0-10, "voice": 0-10, "structure": 0-10, "modernization": 0-10, "consistency": 0-10}
  },
  "flags": ["list of any concerns or issues with the winner"]
}

If MERGED is chosen, provide a synthetic text combining the best elements.
Do not include markdown formatting around the JSON.
"""


# =============================================================================
# PROMPTS FOR DRAFT GENERATION
# =============================================================================

DRAFT_A_SYSTEM = """You are a scholarly Dutch-to-English translator. Translate the Dutch text into English following these MANDATE rules:

1. PRESERVE periodic sentence structure (main clause delayed)
2. MAINTAIN elevated sentence length (~28 words average)
3. USE archaic connectives: hence, whereby, therein, nevertheless
4. PRESERVE theological precision (sphere sovereignty, covenant of grace, etc.)
5. MAINTAIN sweeping architectonic scope
6. USE semicolons for clause coordination
7. PRESERVE parenthetical asides
8. USE traditional biblical citations (Rom. viii. 28)
9. USE first-person plural (we, our, us)
10. CAPTURE modal particles (immers=for, wel=indeed)

DO NOT MODERNIZE. DO NOT MAKE IT SMOOTH. Faithful over polished.
"""

DRAFT_B_SYSTEM = """You are a literal Dutch-to-English translator. Provide a straightforward, word-for-word gloss of the Dutch text. Use simple English. Do not worry about style or elegance. Just translate the meaning directly.
"""


# =============================================================================
# ADJUDICATOR CLASS
# =============================================================================

class Adjudicator:
    """Orchestrates multi-draft generation and agentic selection."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or self._load_api_key()
        self.client = genai.Client(api_key=self.api_key)
        
        self.model_name = "gemini-2.0-flash" # Using 2.0 for better performance
        
    def _load_api_key(self) -> str:
        key = os.environ.get("GOOGLE_API_KEY")
        if key:
            return key
        config_path = Path.home() / ".config" / "opencode" / "opencode.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            return config["provider"]["google"]["options"]["apiKey"]
        raise RuntimeError("GOOGLE_API_KEY not found")
    
    def generate_drafts(self, dutch_text: str, existing_haiku: Optional[str] = None) -> DraftSet:
        """Generate Draft A and B, include Draft C if available."""
        page_label = f"auto_{int(time.time())}"
        
        # Draft A: Faithful/periodic
        print("  Generating Draft A (faithful/periodic)...", end=" ", flush=True)
        resp_a = self.client.models.generate_content(
            model=self.model_name,
            config=genai.types.GenerateContentConfig(
                system_instruction=DRAFT_A_SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=4096
            ),
            contents=f"Translate this Dutch text into English following the voice standards:\n\n{dutch_text}"
        )
        draft_a = resp_a.text
        print("OK")
        
        # Draft B: Literal/gloss
        print("  Generating Draft B (literal/gloss)...", end=" ", flush=True)
        resp_b = self.client.models.generate_content(
            model=self.model_name,
            config=genai.types.GenerateContentConfig(
                system_instruction=DRAFT_B_SYSTEM_PROMPT,
                temperature=0.7,
                max_output_tokens=4096
            ),
            contents=f"Provide a literal word-for-word translation of this Dutch text:\n\n{dutch_text}"
        )
        draft_b = resp_b.text
        print("OK")
        
        return DraftSet(
            page_label=page_label,
            draft_a=draft_a,
            draft_b=draft_b,
            draft_c=existing_haiku,
            source_dutch=dutch_text,
        )
    
    def adjudicate(self, drafts: DraftSet) -> DraftSet:
        """Run the judge model to select the winner."""
        print("  Adjudicating...", end=" ", flush=True)
        
        prompt = self._build_adjudication_prompt(drafts)
        
        resp = self.client.models.generate_content(
            model=self.model_name,
            config=genai.types.GenerateContentConfig(
                system_instruction=ADJUDICATION_SYSTEM_PROMPT,
                temperature=0.1,
                max_output_tokens=4096,
                response_mime_type="application/json"
            ),
            contents=prompt
        )
        
        # Parse JSON response
        try:
            result = json.loads(resp.text)
        except json.JSONDecodeError:
            text = resp.text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            result = json.loads(text)
        
        drafts.winner = result.get("winner", "A")
        drafts.winner_text = result.get("winner_text", "")
        drafts.evaluation = result
        
        print(f"Winner: {drafts.winner}")
        return drafts
    
    def _build_adjudication_prompt(self, drafts: DraftSet) -> str:
        """Build the comparison prompt for the judge."""
        lines = [
            "Compare the following English translations of the same Dutch text and select the best one.",
            "",
            "## Source Dutch",
            drafts.source_dutch,
            "",
            "## Draft A (Faithful/Periodic Style)",
            drafts.draft_a,
            "",
            "## Draft B (Literal Gloss)",
            drafts.draft_b,
        ]
        
        if drafts.draft_c:
            lines.extend([
                "",
                "## Draft C (Existing Haiku Translation)",
                drafts.draft_c,
            ])
        
        lines.append("")
        lines.append("Select the winner and provide scores.")
        
        return "\n".join(lines)
    
    def process(self, dutch_text: str, existing_haiku: Optional[str] = None) -> DraftSet:
        """Full pipeline: generate drafts + adjudicate."""
        print(f"Processing {len(dutch_text)} chars of Dutch text...")
        drafts = self.generate_drafts(dutch_text, existing_haiku)
        return self.adjudicate(drafts)


# =============================================================================
# BATCH ADJUDICATION FOR EXISTING CHAPTERS
# =============================================================================

def adjudicate_existing_chapter(chapter_dir: Path, output_dir: Path):
    """Run adjudication on existing chapter with Haiku Draft C."""
    dutch_file = chapter_dir / "dutch_source.md"
    haiku_file = chapter_dir / "english_refined.md"
    
    if not dutch_file.exists():
        print(f"No dutch_source.md found in {chapter_dir}")
        return
    
    dutch_text = dutch_file.read_text(encoding="utf-8")
    existing_haiku = haiku_file.read_text(encoding="utf-8") if haiku_file.exists() else None
    
    adj = Adjudicator()
    result = adj.process(dutch_text, existing_haiku)
    
    # Save result
    output_dir.mkdir(parents=True, exist_ok=True)
    out_file = output_dir / f"{chapter_dir.name}_adjudication.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(asdict(result), f, indent=2, ensure_ascii=False)
    
    # Save winner text
    winner_file = output_dir / f"{chapter_dir.name}_winner.md"
    winner_file.write_text(result.winner_text, encoding="utf-8")
    
    print(f"Saved to {out_file} and {winner_file}")


if __name__ == "__main__":
    # Test with a sample
    sample_dutch = """Dat wij, staande op den grond der Schrift, toch moeten belijden..."""
    adj = Adjudicator()
    result = adj.process(sample_dutch)
    print(f"\nWinner: {result.winner}")
    print(f"Rationale: {result.evaluation.get('rationale', 'N/A')}")
