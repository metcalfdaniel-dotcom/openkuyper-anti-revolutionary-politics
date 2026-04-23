#!/usr/bin/env python3
"""
OpenKuyper Three-Tier Pipeline

Tier 1: Gemini 2.5 Flash — OCR + Draft generation (fast, cheap)
Tier 2: Gemini 2.5 Pro — Adjudication (nuanced reasoning, expensive)
Tier 3: Gemini 2.5 Flash — Final polish + dual output (fast, cheap)

Produces TWO editions:
1. CLEAN EDITION: Polished English text only
2. CRITICAL EDITION: English text + all translator notes, alternatives, rationale

Usage:
    python three_tier_pipeline.py --pdf path/to/vol1.pdf --start 11 --end 16
"""

import os
import sys
import json
import time
import argparse
import io
import warnings
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

# Suppress Python 3.9 EOL warnings from google-auth
warnings.filterwarnings("ignore", category=FutureWarning, module="google.auth")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.oauth2")
warnings.filterwarnings("ignore", category=FutureWarning, module="google.api_core")

import PIL.Image

sys.path.insert(0, str(Path(__file__).parent))

from google.genai import Client, types
from termbase import Termbase


# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_PDF_V1 = PROJECT_ROOT / "source-materials" / "antirevolutionai01kuyp.pdf"

# Model assignments
TIER1_MODEL = "gemini-2.5-flash"      # OCR + Draft A/B generation
TIER2_MODEL = "gemini-2.5-pro"        # Adjudication (the judge)
TIER3_MODEL = "gemini-2.5-flash"      # Final polish + compilation

# Cost tracking (per 1M tokens)
FLASH_INPUT_COST = 0.15
FLASH_OUTPUT_COST = 0.60
PRO_INPUT_COST = 1.25   # Pro is ~8x more expensive
PRO_OUTPUT_COST = 5.00

# =============================================================================
# CONTEXT-AWARE TERMINOLOGY RULES
# =============================================================================

TERMINOLOGY_CONTEXT_RULES = """
## CRITICAL: Context-Aware Translation Rules

### "Recht" (Dutch) — THE MOST IMPORTANT TERM
This word carries a profound dual meaning that English splits into two words:
- **"Law"** (*Lex*): Written statute, decree, positive legislation, institutional legal framework
- **"Right"** (*Ius*): Divine moral order, inherent justice, what is inherently "right", pre-political moral entitlement

**CONTEXT RULES:**
1. INSTITUTIONAL/JURISPRUDENTIAL context → "LAW":
   - When discussing the state, courts, legal systems, positive legislation
   - "Rechtsstaat" = "Constitutional State" or "Rule-of-Law State"
   - "het geschreven recht" = "written law / positive law"
   - "bron van het recht" when discussing legislation = "source of law"

2. MORAL/THEOLOGICAL context → "RIGHT":
   - When discussing divine ordinance, God's justice, natural law
   - When contrasting with French Revolution's arbitrary will
   - In the philosophical tetrad: the Good, the Beautiful, the True, the RIGHT
   - "Recht" alongside "Onrecht" (wrong/injustice) = "Right"
   - "bron van het recht" when discussing God's ordinance = "source of Right"

3. ETYMOLOGICAL discussions → preserve ambiguity: "Law / Right"

### Other Polysemous Terms
- "Geest" = "spirit" (human spirit OR Holy Spirit — context determines)
- "Katholiek" = often "universal" not "Roman Catholic"
- "Wetenschap" = "science" (in Kuyper's era: systematized knowledge / academic discipline)
- "Volk" = "people" (organic sense) or "nation" — prefer "people" for organic collective
"""

# =============================================================================
# TIER 1: OCR + DRAFT GENERATION (Flash)
# =============================================================================

TIER1_SYSTEM_PROMPT = f"""You are a scholarly Dutch-to-English translator specializing in 19th-century Reformed theological and political texts.

{TERMINOLOGY_CONTEXT_RULES}

## OCR Instructions
1. Read the scanned Dutch text carefully. Preserve old orthography.
2. Mark unclear words with [unclear: best guess].
3. Do NOT modernize Dutch spelling. Transcribe what you see.
4. Preserve paragraph structure.

## Translation Instructions (Draft A — Faithful/Periodic)
1. Translate into English following Kuyper's voice: sweeping, periodic, elevated
2. Average sentence length: ~28 words
3. Use archaic connectives: hence, whereby, therein, nevertheless
4. Preserve theological precision
5. Biblical citations: traditional format (Rom. viii. 28)
6. First-person plural (we, our, us)
7. DO NOT MODERNIZE

## Output Format
Respond in valid JSON:
{{
  "page_number": "...",
  "dutch_ocr": "complete Dutch transcription",
  "english_draft_a": "faithful/periodic translation",
  "unclear_words": [],
  "notes": "translator notes"
}}
"""

TIER1_DRAFT_B_PROMPT = """Provide a literal, word-for-word gloss of this Dutch text into simple English. Do not worry about style or elegance. Just translate the meaning directly and clearly."""


# =============================================================================
# TIER 2: ADJUDICATION (Pro)
# =============================================================================

TIER2_SYSTEM_PROMPT = f"""You are a senior scholarly editor specializing in 19th-century Reformed theological translations. Your task is to compare multiple English drafts of the same Dutch text and select the single best translation.

{TERMINOLOGY_CONTEXT_RULES}

## Selection Criteria (ranked by priority)

1. **Theological Precision** (weight: 30%)
   - Correct technical terms (sphere sovereignty, covenant of grace)
   - Context-aware polysemous terms (especially "Recht" = Law vs Right)
   - Biblical citations in traditional format

2. **Voice Fidelity** (weight: 30%)
   - Kuyper's voice: sweeping, periodic, elevated
   - Sentence length ~28 words
   - Archaic connectives present

3. **Structural Integrity** (weight: 20%)
   - Periodic sentences preserved
   - Semicolons for clause coordination
   - Parenthetical asides maintained

4. **Avoid Modernization** (weight: 15%)
   - Not contemporary English smoothness
   - "Useful and faithful over polished"

5. **Consistency** (weight: 5%)
   - Matches established terminology

## Output Format
{{
  "winner": "A" or "B" or "C" or "MERGED",
  "winner_text": "complete winning translation",
  "rationale": "3-5 sentence explanation",
  "scores": {{
    "A": {{"theological": 0-10, "voice": 0-10, "structure": 0-10, "modernization": 0-10, "consistency": 0-10}},
    "B": {{"theological": 0-10, "voice": 0-10, "structure": 0-10, "modernization": 0-10, "consistency": 0-10}},
    "C": {{"theological": 0-10, "voice": 0-10, "structure": 0-10, "modernization": 0-10, "consistency": 0-10}}
  }},
  "critical_notes": [
    {{
      "term": "problematic term",
      "issue": "what's wrong or questionable",
      "alternatives": ["alternative 1", "alternative 2"],
      "recommendation": "suggested improvement"
    }}
  ],
  "flags": ["list of concerns"]
}}
"""


# =============================================================================
# TIER 3: FINAL POLISH + DUAL OUTPUT (Flash)
# =============================================================================

TIER3_SYSTEM_PROMPT = f"""You are a scholarly editor preparing a final, polished translation of a 19th-century Dutch theological text.

{TERMINOLOGY_CONTEXT_RULES}

Your task: Take the selected winning translation and produce TWO outputs:

1. CLEAN EDITION: The polished English text alone, ready for publication.
2. CRITICAL EDITION: The English text with inline translator notes [like this] wherever:
   - A Dutch word has no exact English equivalent
   - Theological/philosophical ambiguity exists
   - The translation choice could be contested
   - Historical/cultural context needs explanation

Format your response as JSON:
{{
  "clean_edition": " polished text without notes ",
  "critical_edition": "text with [notes: like this] for contested terms",
  "polish_changes": ["list of changes made from input to output"]
}}
"""


# =============================================================================
# PIPELINE CLASS
# =============================================================================

@dataclass
class PageResult:
    page_number: str
    dutch_ocr: str
    draft_a: str
    draft_b: str
    draft_c: Optional[str]
    winner: str
    winner_text: str
    clean_edition: str
    critical_edition: str
    evaluation: dict
    cost_usd: float
    processing_time_sec: float


class ThreeTierPipeline:
    def __init__(self):
        self.termbase = Termbase()
        api_key = self._load_api_key()
        self.client = Client(api_key=api_key)
        
        # Store model names and configs for tiered generation
        self.tier1_config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_mime_type="application/json",
            system_instruction=TIER1_SYSTEM_PROMPT,
        )
        
        self.tier2_config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_mime_type="application/json",
            system_instruction=TIER2_SYSTEM_PROMPT,
        )
        
        self.tier3_config = types.GenerateContentConfig(
            temperature=0.1,
            max_output_tokens=8192,
            response_mime_type="application/json",
            system_instruction=TIER3_SYSTEM_PROMPT,
        )
        
        self.total_cost = 0.0
        self.total_pages = 0
    
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
    
    def process_page(self, image_bytes: bytes, page_label: str, 
                     existing_haiku: Optional[str] = None) -> PageResult:
        """Process a single page through all three tiers."""
        start_time = time.time()
        page_cost = 0.0
        
        print(f"\n{'='*60}")
        print(f"Processing {page_label}")
        print(f"{'='*60}")
        
        # === TIER 1: OCR + Draft A (Flash) ===
        print("TIER 1: OCR + Draft A (Flash)...", end=" ", flush=True)
        t1_result = self._tier1_ocr(image_bytes)
        print(f"OK ({t1_result['input_tokens']}+{t1_result['output_tokens']} tokens)")
        page_cost += self._calc_cost(t1_result['input_tokens'], t1_result['output_tokens'], is_pro=False)
        
        # Generate Draft B (also Flash, separate call)
        print("TIER 1: Draft B (Flash)...", end=" ", flush=True)
        draft_b = self._tier1_draft_b(t1_result['dutch_ocr'])
        print("OK")
        
        # === TIER 2: Adjudication (Pro) ===
        print("TIER 2: Adjudication (Pro)...", end=" ", flush=True)
        t2_result = self._tier2_adjudicate(
            dutch=t1_result['dutch_ocr'],
            draft_a=t1_result['english_draft_a'],
            draft_b=draft_b,
            draft_c=existing_haiku,
        )
        print(f"Winner: {t2_result['winner']}")
        page_cost += self._calc_cost(t2_result['input_tokens'], t2_result['output_tokens'], is_pro=True)
        
        # === TIER 3: Final Polish (Flash) ===
        print("TIER 3: Final Polish (Flash)...", end=" ", flush=True)
        t3_result = self._tier3_polish(t2_result['winner_text'])
        print("OK")
        page_cost += self._calc_cost(t3_result['input_tokens'], t3_result['output_tokens'], is_pro=False)
        
        elapsed = time.time() - start_time
        self.total_cost += page_cost
        self.total_pages += 1
        
        print(f"Page cost: ${page_cost:.4f} | Total: ${self.total_cost:.4f}")
        
        return PageResult(
            page_number=t1_result.get('page_number', page_label),
            dutch_ocr=t1_result['dutch_ocr'],
            draft_a=t1_result['english_draft_a'],
            draft_b=draft_b,
            draft_c=existing_haiku,
            winner=t2_result['winner'],
            winner_text=t2_result['winner_text'],
            clean_edition=t3_result['clean_edition'],
            critical_edition=t3_result['critical_edition'],
            evaluation=t2_result['evaluation'],
            cost_usd=page_cost,
            processing_time_sec=elapsed,
        )
    
    def _tier1_ocr(self, image_bytes: bytes) -> dict:
        """Tier 1: OCR + Draft A via Flash."""
        import PIL.Image
        import io
        image = PIL.Image.open(io.BytesIO(image_bytes))
        user_prompt = "OCR and translate this page from Kuyper's Antirevolutionaire Staatkunde. Output valid JSON only."
        
        response = self.client.models.generate_content(
            model=TIER1_MODEL,
            contents=[user_prompt, image],
            config=self.tier1_config,
        )
        
        try:
            data = json.loads(self._extract_json(response.text))
        except json.JSONDecodeError as e:
            print(f"    JSON parse error: {e}")
            print(f"    Raw response (first 500 chars): {response.text[:500]}")
            raise
        
        data['input_tokens'] = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        data['output_tokens'] = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        return data
    
    def _tier1_draft_b(self, dutch_text: str) -> str:
        """Tier 1: Generate literal Draft B via Flash."""
        response = self.client.models.generate_content(
            model=TIER1_MODEL,
            contents=f"{TIER1_DRAFT_B_PROMPT}\n\n{dutch_text}",
            config=self.tier1_config,
        )
        return response.text
    
    def _tier2_adjudicate(self, dutch: str, draft_a: str, draft_b: str, 
                          draft_c: Optional[str]) -> dict:
        """Tier 2: Adjudication via Pro."""
        prompt = f"""Compare these English drafts of the same Dutch text and select the best.

## Source Dutch
{dutch}

## Draft A (Faithful/Periodic)
{draft_a}

## Draft B (Literal Gloss)
{draft_b}
"""
        if draft_c:
            prompt += f"\n## Draft C (Existing Translation)\n{draft_c}\n"
        
        prompt += "\nSelect the winner and provide detailed evaluation."
        
        response = self.client.models.generate_content(
            model=TIER2_MODEL,
            contents=prompt,
            config=self.tier2_config,
        )
        
        result = json.loads(self._extract_json(response.text))
        result['input_tokens'] = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        result['output_tokens'] = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        return result
    
    def _tier3_polish(self, winner_text: str) -> dict:
        """Tier 3: Final polish via Flash."""
        prompt = f"Polish this translation and produce both Clean and Critical editions:\n\n{winner_text}"
        response = self.client.models.generate_content(
            model=TIER3_MODEL,
            contents=prompt,
            config=self.tier3_config,
        )
        
        data = json.loads(self._extract_json(response.text))
        data['input_tokens'] = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        data['output_tokens'] = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        return data
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from response, handling markdown wrappers and truncation."""
        text = text.strip()
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        # Handle truncated JSON by finding the last complete object
        if not text.endswith("}"):
            # Find last complete key-value pair and close the JSON
            last_brace = text.rfind("}")
            if last_brace > 0:
                text = text[:last_brace+1]
            else:
                # No closing brace found, try to reconstruct
                text = text + "}"
        
        return text
    
    def _calc_cost(self, input_tokens: int, output_tokens: int, is_pro: bool) -> float:
        """Calculate API cost."""
        if is_pro:
            return (input_tokens / 1_000_000 * PRO_INPUT_COST + 
                    output_tokens / 1_000_000 * PRO_OUTPUT_COST)
        else:
            return (input_tokens / 1_000_000 * FLASH_INPUT_COST + 
                    output_tokens / 1_000_000 * FLASH_OUTPUT_COST)
    
    def compile_editions(self, results: list[PageResult], output_dir: Path):
        """Compile both Clean and Critical editions."""
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean Edition
        clean_lines = [
            "# Antirevolutionaire Staatkunde — Foreword",
            "## Clean English Edition",
            "",
            f"**Generated:** {time.strftime('%Y-%m-%d')}",
            f"**Pipeline:** Three-Tier (Flash→Pro→Flash)",
            f"**Model:** {TIER1_MODEL} / {TIER2_MODEL}",
            "",
            "---",
            "",
        ]
        
        # Critical Edition
        critical_lines = [
            "# Antirevolutionaire Staatkunde — Foreword",
            "## Critical Edition with Translator Notes",
            "",
            f"**Generated:** {time.strftime('%Y-%m-%d')}",
            f"**Pipeline:** Three-Tier (Flash→Pro→Flash)",
            f"**Model:** {TIER1_MODEL} / {TIER2_MODEL}",
            "",
            "---",
            "",
        ]
        
        for result in results:
            if result.dutch_ocr.strip():
                clean_lines.extend([
                    f"## Page {result.page_number}",
                    "",
                    result.clean_edition,
                    "",
                    "---",
                    "",
                ])
                
                critical_lines.extend([
                    f"## Page {result.page_number}",
                    "",
                    "### Dutch Original",
                    result.dutch_ocr,
                    "",
                    "### English Translation (Critical)",
                    result.critical_edition,
                    "",
                    "### Adjudication Notes",
                    f"- **Winner:** Draft {result.winner}",
                    f"- **Rationale:** {result.evaluation.get('rationale', 'N/A')}",
                ])
                
                if result.evaluation.get('critical_notes'):
                    critical_lines.append("- **Critical Notes:**")
                    for note in result.evaluation['critical_notes']:
                        critical_lines.append(f"  - *{note.get('term', 'Term')}*: {note.get('issue', '')}")
                        if note.get('alternatives'):
                            critical_lines.append(f"    Alternatives: {', '.join(note['alternatives'])}")
                
                critical_lines.extend([
                    "",
                    "---",
                    "",
                ])
        
        # Write files
        clean_path = output_dir / "foreword_CLEAN.md"
        critical_path = output_dir / "foreword_CRITICAL.md"
        
        clean_path.write_text("\n".join(clean_lines), encoding="utf-8")
        critical_path.write_text("\n".join(critical_lines), encoding="utf-8")
        
        print(f"\nCompiled editions:")
        print(f"  Clean:    {clean_path}")
        print(f"  Critical: {critical_path}")


def main():
    parser = argparse.ArgumentParser(description="OpenKuyper Three-Tier Pipeline")
    parser.add_argument("--pdf", type=Path, default=SOURCE_PDF_V1)
    parser.add_argument("--start", type=int, default=11)
    parser.add_argument("--end", type=int, default=16)
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "manuscript" / "foreword")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    
    from gemini_ocr_pipeline import preprocess_image, image_to_bytes
    from pdf2image import convert_from_path
    
    pipeline = ThreeTierPipeline()
    results = []
    
    print(f"\n{'='*60}")
    print(f"THREE-TIER PIPELINE")
    print(f"Tier 1 (Flash): OCR + Draft A/B")
    print(f"Tier 2 (Pro):   Adjudication")
    print(f"Tier 3 (Flash): Polish + Dual Output")
    print(f"{'='*60}\n")
    
    if args.dry_run:
        print("DRY RUN — skipping API calls")
        return
    
    # Convert PDF pages
    print(f"Converting PDF pages {args.start}-{args.end}...")
    images = convert_from_path(args.pdf, dpi=150, first_page=args.start, 
                               last_page=args.end, fmt="jpeg")
    print(f"Converted {len(images)} pages\n")
    
    for idx, pil_image in enumerate(images, start=args.start):
        page_label = f"p{idx:04d}"
        
        # Preprocess
        processed = preprocess_image(pil_image)
        image_bytes = image_to_bytes(processed)
        
        # Process through three tiers
        try:
            result = pipeline.process_page(image_bytes, page_label)
            results.append(result)
            
            # Save individual result
            result_file = args.output_dir / f"{page_label}_result.json"
            result_file.parent.mkdir(parents=True, exist_ok=True)
            with open(result_file, "w", encoding="utf-8") as f:
                json.dump(asdict(result), f, indent=2, ensure_ascii=False)
            
            time.sleep(1)  # Rate limit buffer
            
        except Exception as e:
            print(f"ERROR on page {idx}: {e}")
    
    # Compile final editions
    if results:
        pipeline.compile_editions(results, args.output_dir)
    
    print(f"\n{'='*60}")
    print("PIPELINE COMPLETE")
    print(f"{'='*60}")
    print(f"Pages: {pipeline.total_pages}")
    print(f"Total cost: ${pipeline.total_cost:.4f} USD")
    print(f"Output: {args.output_dir}")


if __name__ == "__main__":
    main()
