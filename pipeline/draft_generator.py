#!/usr/bin/env python3
"""
OpenKuyper Draft Generator

Generates multiple translation drafts from OCR'd Dutch text using different
prompt strategies, then returns them for adjudication.

Strategies:
- Draft A (STRUCTURAL): Literal translation preserving Dutch syntax and
  maximizing terminological precision. Prioritizes word-for-word accuracy.
- Draft B (VOICE): Fluent translation optimizing for Kuyper's voice,
  style rules, and sweeping periodic sentence structure.
- Draft C (EXISTING): Optional existing translation from manuscript files.
"""

import os
import json
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from google import genai

# =============================================================================
# STYLE DATABASE (embedded)
# =============================================================================

STYLE_DATABASE = """
## The 10 Style Rules

1. Preserve periodic sentence structure (~35% of sentences delay main clause)
2. Maintain elevated sentence length (avg 28.16 words; do not truncate)
3. Use archaic connectives: hence, whereby, wherein, wherewith, therein, thereof
4. Preserve theological precision (justification, sanctification, covenant, etc.)
5. Maintain sweeping architectonic scope (particular → universal)
6. Use semicolons for clause coordination
7. Preserve parenthetical asides
8. Do not modernize biblical citations (e.g., 'Rom. viii. 28')
9. Maintain first-person plural ('we confess', 'we maintain')
10. Preserve modal particles ('immers' → 'for', 'wel' → 'indeed')

## Core Dutch-to-English Mappings

geloof → faith | genade → grace | heiligmaking → sanctification
rechtvaardiging → justification | verlossing → salvation
verzoening → atonement | verkiezing → election
voorzienigheid → providence | openbaring → revelation
schrift → Scripture | verbond → covenant | kerk → church
sacrament → sacrament | doop → baptism | zonde → sin
schuld → guilt | sfeer → sphere | soevereiniteit → sovereignty
soevereiniteit in eigen kring → sphere sovereignty
staat → state | overheid → government | revolutie → revolution
antirevolutionair → antirevolutionary | beginsel → principle
grondwet → constitution | recht → law / right
volk → people / nation | natie → nation | maatschappij → society
gezin → family | school → school | ziel → soul
geest → spirit | hart → heart | geweten → conscience
bewustzijn → consciousness | vermogen → faculty / power
wil → will | verstand → intellect / understanding | natuur → nature
algemeene genade → common grace | bijzondere genade → particular grace
levenssysteem → life-system | wereldbeschouwing → worldview
gereformeerd → Reformed | calvinistisch → Calvinistic
katholiek → catholic / universal | daarom → therefore / hence
zodat → so that | echter → however / yet
immers → for / since / indeed | namelijk → namely
wel → indeed / truly / certainly | toch → yet / still / nevertheless
"""

# =============================================================================
# PROMPTS
# =============================================================================

DRAFT_A_SYSTEM_PROMPT = f"""You are a rigorous Dutch-to-English translator specializing in 19th-century Reformed theological texts. Your task is to produce a LITERAL, STRUCTURALLY FAITHFUL translation of the provided Dutch text.

You MUST follow these standards:
{STYLE_DATABASE}

## CRITICAL INSTRUCTIONS FOR DRAFT A (STRUCTURAL)

1. **Preserve Dutch sentence structure** as closely as English allows. If Kuyper uses a periodic sentence, mirror that structure.
2. **Maximize terminological precision.** Use the Dutch→English mappings above as defaults. If a term has multiple valid translations, choose the one that most closely maps to the Dutch theological concept.
3. **Do not paraphrase.** Translate word-for-word where possible, preserving the Dutch syntax even if it sounds slightly archaic.
4. **Preserve all subordinate clauses** in their original order.
5. **Mark any uncertain translation** with [UNCERTAIN: your best attempt].
6. **Output biblical citations in traditional format** (e.g., 'Rom. viii. 28').

## Output Format

Respond in valid JSON with exactly these keys:
{{
  "draft_label": "A",
  "translation": "The complete English translation, preserving paragraph breaks",
  "terminology_notes": "Any notes about difficult theological or political terms",
  "uncertain_phrases": ["list of phrases marked [UNCERTAIN]"]
}}

Output raw JSON only. No markdown formatting."""


DRAFT_B_SYSTEM_PROMPT = f"""You are a master literary translator specializing in 19th-century Reformed theological texts. Your task is to produce a FLUENT, VOICE-OPTIMIZED translation of the provided Dutch text that captures Kuyper's distinctive rhetorical style.

You MUST follow these standards:
{STYLE_DATABASE}

## CRITICAL INSTRUCTIONS FOR DRAFT B (VOICE-OPTIMIZED)

1. **Optimize for Kuyper's voice.** The translation should feel like it was written by the same mind that produced *Lectures on Calvinism* and *The Work of the Holy Spirit*.
2. **Prioritize periodic sentences.** Delay the main clause. Build tension through subordinate clauses. Example: "That we, standing as we do upon the foundation of Scripture, must nevertheless confess..."
3. **Use elevated vocabulary.** Prefer 'hence' over 'so', 'whereby' over 'by which', 'nevertheless' over 'however'.
4. **Maintain sweeping architectonic scope.** Kuyper moves from particular to universal. Your translation must preserve that grand movement.
5. **Do NOT sacrifice accuracy for elegance.** Every theological term must be precise. Every political concept must be exact.
6. **Use semicolons for coordination** of independent clauses related in theme.
7. **Preserve first-person plural** ('we', 'our', 'us') to maintain solidarity with the reader.
8. **Output biblical citations in traditional format** (e.g., 'Rom. viii. 28').

## Output Format

Respond in valid JSON with exactly these keys:
{{
  "draft_label": "B",
  "translation": "The complete English translation, preserving paragraph breaks",
  "voice_notes": "Notes about stylistic choices and voice optimizations",
  "uncertain_phrases": ["list of phrases marked [UNCERTAIN]"]
}}

Output raw JSON only. No markdown formatting."""


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class DraftResult:
    draft_label: str  # "A", "B", or "C"
    translation: str
    notes: str
    uncertain_phrases: list
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    processing_time_sec: float = 0.0


# =============================================================================
# DRAFT GENERATOR
# =============================================================================

class DraftGenerator:
    """Generates multiple translation drafts from OCR'd Dutch text."""
    
    def __init__(self, model_name: str = "gemini-2.0-flash", temperature: float = 0.1):
        self.model_name = model_name
        self.temperature = temperature
        self.client = None
        self._setup_models()
    
    def _setup_models(self):
        """Configure Gemini models using the google-genai SDK."""
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            config_path = Path.home() / ".config" / "opencode" / "opencode.json"
            if config_path.exists():
                with open(config_path) as f:
                    config = json.load(f)
                api_key = config["provider"]["google"]["options"]["apiKey"]
        
        self.client = genai.Client(api_key=api_key)

    def generate_draft_a(self, dutch_text: str, page_context: str = "") -> DraftResult:
        """Generate structural/literal Draft A."""
        import time
        start = time.time()
        
        prompt = self._build_prompt(dutch_text, page_context)
        response = self.client.models.generate_content(
            model=self.model_name,
            config=genai.types.GenerateContentConfig(
                system_instruction=DRAFT_A_SYSTEM_PROMPT,
                temperature=self.temperature,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
            contents=prompt
        )
        
        elapsed = time.time() - start
        data = self._parse_json_response(response.text)
        
        input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
        
        return DraftResult(
            draft_label="A",
            translation=data.get("translation", ""),
            notes=data.get("terminology_notes", ""),
            uncertain_phrases=data.get("uncertain_phrases", []),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            processing_time_sec=elapsed,
        )
    
    def generate_draft_b(self, dutch_text: str, page_context: str = "") -> DraftResult:
        """Generate voice-optimized Draft B."""
        import time
        start = time.time()
        
        prompt = self._build_prompt(dutch_text, page_context)
        response = self.client.models.generate_content(
            model=self.model_name,
            config=genai.types.GenerateContentConfig(
                system_instruction=DRAFT_B_SYSTEM_PROMPT,
                temperature=self.temperature + 0.1,
                max_output_tokens=8192,
                response_mime_type="application/json",
            ),
            contents=prompt
        )
        
        elapsed = time.time() - start
        data = self._parse_json_response(response.text)
        
        input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
        
        return DraftResult(
            draft_label="B",
            translation=data.get("translation", ""),
            notes=data.get("voice_notes", ""),
            uncertain_phrases=data.get("uncertain_phrases", []),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            processing_time_sec=elapsed,
        )
    
    def generate_draft_a(self, dutch_text: str, page_context: str = "") -> DraftResult:
        """Generate structural/literal Draft A."""
        import time
        start = time.time()
        
        prompt = self._build_prompt(dutch_text, page_context)
        response = self.model_a.generate_content(prompt)
        
        elapsed = time.time() - start
        data = self._parse_json_response(response.text)
        
        input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
        
        return DraftResult(
            draft_label="A",
            translation=data.get("translation", ""),
            notes=data.get("terminology_notes", ""),
            uncertain_phrases=data.get("uncertain_phrases", []),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            processing_time_sec=elapsed,
        )
    
    def generate_draft_b(self, dutch_text: str, page_context: str = "") -> DraftResult:
        """Generate voice-optimized Draft B."""
        import time
        start = time.time()
        
        prompt = self._build_prompt(dutch_text, page_context)
        response = self.model_b.generate_content(prompt)
        
        elapsed = time.time() - start
        data = self._parse_json_response(response.text)
        
        input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
        output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
        cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)
        
        return DraftResult(
            draft_label="B",
            translation=data.get("translation", ""),
            notes=data.get("voice_notes", ""),
            uncertain_phrases=data.get("uncertain_phrases", []),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            processing_time_sec=elapsed,
        )
    
    def load_draft_c(self, chapter_dir: Path) -> Optional[DraftResult]:
        """Load existing Draft C from english_refined.md or english_draft.md."""
        for filename in ["english_refined.md", "english_draft.md"]:
            path = chapter_dir / filename
            if path.exists():
                text = path.read_text(encoding="utf-8")
                # Strip YAML frontmatter if present
                text = re.sub(r'^---\n.*?\n---\n', '', text, flags=re.DOTALL)
                return DraftResult(
                    draft_label="C",
                    translation=text,
                    notes="Loaded from existing manuscript file",
                    uncertain_phrases=[],
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0,
                    processing_time_sec=0.0,
                )
        return None
    
    def generate_both(self, dutch_text: str, page_context: str = "", chapter_dir: Optional[Path] = None) -> dict:
        """Generate Draft A and Draft B, optionally load Draft C."""
        results = {}
        
        print("  [DraftGenerator] Generating Draft A (structural)...")
        results["A"] = self.generate_draft_a(dutch_text, page_context)
        print(f"    Draft A: {results['A'].output_tokens} tokens, ${results['A'].cost_usd:.4f}")
        
        print("  [DraftGenerator] Generating Draft B (voice-optimized)...")
        results["B"] = self.generate_draft_b(dutch_text, page_context)
        print(f"    Draft B: {results['B'].output_tokens} tokens, ${results['B'].cost_usd:.4f}")
        
        if chapter_dir:
            draft_c = self.load_draft_c(chapter_dir)
            if draft_c:
                print("  [DraftGenerator] Loaded Draft C (existing)")
                results["C"] = draft_c
        
        return results
    
    def _build_prompt(self, dutch_text: str, page_context: str) -> str:
        """Build the user prompt for translation."""
        parts = []
        if page_context:
            parts.append(f"Page context: {page_context}")
        parts.append("Translate the following Dutch text into English following your system instructions.")
        parts.append("")
        parts.append("--- DUTCH TEXT ---")
        parts.append(dutch_text)
        parts.append("--- END DUTCH TEXT ---")
        return "\n".join(parts)
    
    def _parse_json_response(self, text: str) -> dict:
        """Parse JSON from model response, handling markdown wrappers."""
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            return json.loads(text)
