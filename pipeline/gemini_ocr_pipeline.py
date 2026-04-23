#!/usr/bin/env python3
"""
OpenKuyper Gemini OCR + Translation Pipeline

Uses Gemini 2.5 Flash to:
1. OCR scanned Dutch pages from Antirevolutionaire Staatkunde
2. Translate into English following the Kuyper Voice Standards

Requires: GOOGLE_API_KEY environment variable or in ~/.config/opencode/opencode.json
"""

import os
import sys
import json
import time
import base64
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional
from io import BytesIO

from google.genai import Client, types
from PIL import Image, ImageEnhance
from pdf2image import convert_from_path

# =============================================================================
# CONFIGURATION
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_PDF_V1 = PROJECT_ROOT / "source-materials" / "antirevolutionai01kuyp.pdf"
SOURCE_PDF_V2 = PROJECT_ROOT / "source-materials" / "antirevolutiona02kuyp.pdf"
OUTPUT_DIR = PROJECT_ROOT / "manuscript" / "foreword"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Image processing settings
IMAGE_MAX_DIM = 1024  # Resize to max 1024px on longest edge (cost/quality balance)
IMAGE_DPI = 150       # DPI for PDF-to-image conversion
IMAGE_FORMAT = "JPEG"
IMAGE_QUALITY = 85

# Gemini settings
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_TEMPERATURE = 0.1  # Low temperature for consistency
GEMINI_MAX_OUTPUT_TOKENS = 8192

# Cost tracking (Flash 2.5 pricing as of 2025)
COST_PER_1M_INPUT_TOKENS = 0.15
COST_PER_1M_OUTPUT_TOKENS = 0.60

# =============================================================================
# STYLE DATABASE (embedded for self-containment)
# =============================================================================

STYLE_DATABASE = """
# OpenKuyper Translation Voice Standards

## Mandate: Useful and Faithful over Polished
Do not modernize Kuyper's prose. Maintain sweeping periodic sentences, elevated classical vocabulary, and theological precision.

## Aggregated Metrics (from 4 reference texts, 5,123 sentences)
- Average sentence length: 28.16 words (modern English: 15-20)
- Periodic sentences: ~35% (main clause delayed)
- Long sentences (30+ words): 1,850 (36%)

## The 10 Style Rules

1. Preserve periodic sentence structure
   Priority: CRITICAL
   Rationale: Kuyper uses periodic sentences in ~35% of sentences. Main clause should often be delayed.
   Example: "That we, standing as we do upon the foundation of Scripture, must nevertheless confess..."

2. Maintain elevated sentence length
   Priority: CRITICAL
   Rationale: Average sentence length across texts is 28.16 words. Do not truncate.

3. Use archaic connectives and adverbials
   Priority: HIGH
   Rationale: 'Hence', 'whereby', 'therein', 'nevertheless' are characteristic markers.
   Example: "Hence it follows that..."

4. Preserve theological precision in terminology
   Priority: CRITICAL
   Rationale: Terms like 'justification', 'sanctification', 'covenant' have specific technical meanings.
   Example: "The covenant of grace"

5. Maintain sweeping architectonic scope
   Priority: HIGH
   Rationale: Kuyper moves from particular to universal, from historical to systematic.
   Example: "...and thus we see how all things work together for the consummation of His eternal purpose."

6. Use semicolons for clause coordination
   Priority: MEDIUM
   Example: "The state has its own sphere; the church has hers; and neither may trespass upon the other."

7. Preserve parenthetical asides
   Priority: MEDIUM
   Example: "The principle (and here we touch the very heart of the matter) is..."

8. Do not modernize biblical citations
   Priority: MEDIUM
   Use traditional abbreviations: 'Rom. viii. 28', not 'Romans 8:28'.

9. Maintain Kuyper's use of first-person plural
   Priority: HIGH
   Kuyper frequently uses 'we', 'our', 'us' to create solidarity with the reader.
   Example: "We confess... We maintain..."

10. Preserve modal particles and rhetorical grounding
    Priority: HIGH
    Dutch particles like 'immers', 'wel', 'toch' carry modal weight. English must capture the grounding.
    Example: "For (immers) we must not forget..."

## Core Dutch-to-English Mappings

| Dutch | English | Confidence | Notes |
|-------|---------|------------|-------|
| geloof | faith | high | |
| genade | grace | high | |
| heiligmaking | sanctification | high | |
| rechtvaardiging | justification | high | |
| verlossing | salvation | high | |
| verzoening | atonement | high | |
| verkiezing | election | high | |
| voorzienigheid | providence | high | |
| openbaring | revelation | high | |
| schrift | Scripture | high | |
| verbond | covenant | high | |
| kerk | church | high | |
| sacrament | sacrament | high | |
| doop | baptism | high | |
| zonde | sin | high | |
| schuld | guilt | high | |
| sfeer | sphere | high | |
| soevereiniteit | sovereignty | high | |
| soevereiniteit in eigen kring | sphere sovereignty | high | |
| staat | state | high | |
| overheid | government | high | |
| revolutie | revolution | high | |
| antirevolutionair | antirevolutionary | high | |
| beginsel | principle | high | |
| grondwet | constitution | high | |
| recht | law / right | medium | Polysemous: means both law and right/justice |
| volk | people / nation | medium | Often 'people' in organic sense |
| natie | nation | high | |
| maatschappij | society | high | |
| gezin | family | high | |
| school | school | high | |
| ziel | soul | high | |
| geest | spirit | high | Polysemous: human spirit or Holy Spirit |
| hart | heart | high | |
| geweten | conscience | high | |
| bewustzijn | consciousness | high | |
| vermogen | faculty / power | medium | |
| wil | will | high | |
| verstand | intellect / understanding | medium | |
| natuur | nature | high | |
| algemeene genade | common grace | high | |
| bijzondere genade | particular grace / special grace | high | |
| levenssysteem | life-system / life and thought system | high | |
| wereldbeschouwing | worldview / world-and-life view | high | |
| gereformeerd | Reformed / Calvinistic | high | |
| calvinistisch | Calvinistic | high | |
| katholiek | catholic / universal | medium | Often means universal, not Roman Catholic |
| daarom | therefore / hence | high | |
| zodat | so that | high | |
| echter | however / yet | high | |
| immers | for / since / indeed | medium | Kuyper uses 'immers' frequently for causal grounding |
| namelijk | namely / that is to say | high | |
| wel | indeed / truly / certainly | medium | Modal particle, often concessive |
| toch | yet / still / nevertheless | medium | |

## Elevated Vocabulary to Preserve
being, hence, principle, knowledge, existence, thought, conception, reason, idea, ground, testimony, operation, certainty, judgment, direct, organic, confidence, nevertheless, thereby, essence, immediate, whereby, foundation, organism, notwithstanding, persuasion, structure, perception, conclusion, basis, thereof, assurance, wherewith, therein, herein, lofty, wherein, proposition, hereby, magnificent, sentence, indirect, notion, clause

## Archaic Connectives to Use
hence, whereby, wherein, whereof, wherewith, thereby, therein, thereof, herein, hereby, aforesaid, foregoing, nevertheless, notwithstanding, persuasion, testimony
"""

# =============================================================================
# SYSTEM PROMPT
# =============================================================================

SYSTEM_PROMPT = f"""You are a scholarly Dutch-to-English translator specializing in 19th-century Reformed theological and political texts. Your task is to OCR a scanned page from Abraham Kuyper's *Antirevolutionaire Staatkunde* (1916) and translate it into English.

You have access to the following authoritative style database derived from algorithmic analysis of 5,123 sentences across 4 existing English translations of Kuyper's works. You MUST follow these standards.

{STYLE_DATABASE}

---

## OCR Instructions

1. The input is a scanned page from a 1916 Dutch book. The text may be in old Dutch orthography (e.g., using "ij" ligatures, Fraktur-like typefaces, or old spelling conventions).
2. Read the Dutch text carefully. Do not guess at unclear words — mark them with [unclear: best guess].
3. Preserve line breaks and paragraph structure from the original.
4. Do NOT modernize the Dutch spelling. Transcribe what you see.
5. If there are footnotes, mark them clearly with [FOOTNOTE: text].
6. If there are marginal notes or page numbers, preserve them with [MARGIN: text].

## Translation Instructions

1. Translate the transcribed Dutch into English following ALL 10 style rules above.
2. Use the Dutch-to-English mappings provided as your default terminology.
3. Maintain Kuyper's sentence structure: long, periodic, sweeping.
4. Do NOT modernize. Do NOT make it sound like contemporary English.
5. Preserve theological and political precision.
6. If a Dutch word has no exact English equivalent (e.g., 'immers', 'wel'), translate the modal force, not just the dictionary definition.
7. Output biblical citations in traditional format (e.g., 'Rom. viii. 28').

## Output Format

Respond in valid JSON with exactly these keys:

{{
  "page_number": "original page number if visible, else null",
  "dutch_ocr": "The complete transcribed Dutch text, preserving paragraphs",
  "english_translation": "The complete English translation, preserving paragraph breaks",
  "unclear_words": ["list of words marked [unclear]"],
  "notes": "Any translator notes about difficult passages, ambiguous terms, or style choices"
}}

Do not include markdown formatting around the JSON. Output raw JSON only.
"""

# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TranslationResult:
    page_number: Optional[str]
    dutch_ocr: str
    english_translation: str
    unclear_words: list
    notes: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    processing_time_sec: float = 0.0


@dataclass
class CostTracker:
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    pages_processed: int = 0
    
    def add(self, input_tokens: int, output_tokens: int):
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        cost = (input_tokens / 1_000_000 * COST_PER_1M_INPUT_TOKENS +
                output_tokens / 1_000_000 * COST_PER_1M_OUTPUT_TOKENS)
        self.total_cost_usd += cost
        self.pages_processed += 1
    
    def report(self) -> str:
        return (f"Pages: {self.pages_processed} | "
                f"Input tokens: {self.total_input_tokens:,} | "
                f"Output tokens: {self.total_output_tokens:,} | "
                f"Est. cost: ${self.total_cost_usd:.4f} USD")


# =============================================================================
# IMAGE PREPROCESSING
# =============================================================================

def preprocess_image(pil_image: Image.Image) -> Image.Image:
    """Resize and enhance image for OCR while keeping token costs reasonable."""
    # Resize to max dimension
    pil_image.thumbnail((IMAGE_MAX_DIM, IMAGE_MAX_DIM), Image.Resampling.LANCZOS)
    
    # Convert to grayscale (reduces tokens, improves text contrast)
    if pil_image.mode != "L":
        pil_image = pil_image.convert("L")
    
    # Enhance contrast
    enhancer = ImageEnhance.Contrast(pil_image)
    pil_image = enhancer.enhance(1.5)
    
    # Enhance sharpness slightly
    enhancer = ImageEnhance.Sharpness(pil_image)
    pil_image = enhancer.enhance(1.2)
    
    return pil_image


def image_to_bytes(pil_image: Image.Image) -> bytes:
    """Convert PIL image to JPEG bytes for API upload."""
    buffer = BytesIO()
    pil_image.save(buffer, format=IMAGE_FORMAT, quality=IMAGE_QUALITY)
    return buffer.getvalue()


# =============================================================================
# GEMINI API
# =============================================================================

def load_api_key() -> str:
    """Load Google API key from env or OpenCode config."""
    key = os.environ.get("GOOGLE_API_KEY")
    if key:
        return key
    
    config_path = Path.home() / ".config" / "opencode" / "opencode.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
            key = config["provider"]["google"]["options"]["apiKey"]
            return key
        except (KeyError, json.JSONDecodeError):
            pass
    
    raise RuntimeError(
        "GOOGLE_API_KEY not found. Set environment variable or configure in ~/.config/opencode/opencode.json"
    )


def setup_gemini():
    """Configure Gemini API."""
    api_key = load_api_key()
    client = Client(api_key=api_key)
    
    config = types.GenerateContentConfig(
        temperature=GEMINI_TEMPERATURE,
        max_output_tokens=GEMINI_MAX_OUTPUT_TOKENS,
        response_mime_type="application/json",
        system_instruction=SYSTEM_PROMPT,
    )
    return client, config


def translate_page(client, config, image_bytes: bytes, page_label: str) -> TranslationResult:
    """Send a page image to Gemini and get structured translation."""
    start_time = time.time()
    
    image = Image.open(BytesIO(image_bytes))
    
    # The user prompt is minimal since the system instruction carries the heavy context
    user_prompt = (
        "OCR and translate this page from Abraham Kuyper's *Antirevolutionaire Staatkunde*. "
        "Follow the voice standards in your system instruction. "
        "Output valid JSON with keys: page_number, dutch_ocr, english_translation, unclear_words, notes."
    )
    
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[user_prompt, image],
        config=config,
    )
    
    elapsed = time.time() - start_time
    
    # Parse usage metadata
    input_tokens = response.usage_metadata.prompt_token_count if response.usage_metadata else 0
    output_tokens = response.usage_metadata.candidates_token_count if response.usage_metadata else 0
    
    # Parse JSON response
    try:
        data = json.loads(response.text)
    except json.JSONDecodeError:
        # Sometimes the model wraps JSON in markdown
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        data = json.loads(text)
    
    result = TranslationResult(
        page_number=data.get("page_number"),
        dutch_ocr=data.get("dutch_ocr", ""),
        english_translation=data.get("english_translation", ""),
        unclear_words=data.get("unclear_words", []),
        notes=data.get("notes", ""),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=(input_tokens / 1_000_000 * COST_PER_1M_INPUT_TOKENS +
                  output_tokens / 1_000_000 * COST_PER_1M_OUTPUT_TOKENS),
        processing_time_sec=elapsed,
    )
    
    return result


# =============================================================================
# BATCH PROCESSING
# =============================================================================

def process_pages(
    pdf_path: Path,
    start_page: int,
    end_page: int,
    output_dir: Path,
    tracker: CostTracker,
    dry_run: bool = False,
) -> list[TranslationResult]:
    """Process a range of pages from a PDF."""
    client, config = setup_gemini()
    results = []
    
    print(f"Processing pages {start_page}–{end_page} from {pdf_path.name}")
    print(f"Output directory: {output_dir}")
    print(f"Dry run: {dry_run}")
    print("-" * 60)
    
    # Convert PDF pages to images
    print("Converting PDF to images...")
    images = convert_from_path(
        pdf_path,
        dpi=IMAGE_DPI,
        first_page=start_page,
        last_page=end_page,
        fmt="jpeg",
    )
    print(f"Converted {len(images)} pages")
    
    for idx, pil_image in enumerate(images, start=start_page):
        page_label = f"{pdf_path.stem}_p{idx:04d}"
        print(f"\n[{idx}/{end_page}] Processing {page_label}...", end=" ", flush=True)
        
        if dry_run:
            print("DRY RUN — skipping API call")
            continue
        
        try:
            # Preprocess image
            processed = preprocess_image(pil_image)
            image_bytes = image_to_bytes(processed)
            
            # Call Gemini
            result = translate_page(client, config, image_bytes, page_label)
            results.append(result)
            tracker.add(result.input_tokens, result.output_tokens)
            
            # Save individual page result
            page_file = output_dir / f"{page_label}.json"
            with open(page_file, "w", encoding="utf-8") as f:
                json.dump(asdict(result), f, indent=2, ensure_ascii=False)
            
            print(f"OK ({result.processing_time_sec:.1f}s | {tracker.report()})")
            
            # Brief pause to avoid rate limits
            time.sleep(0.5)
            
        except Exception as e:
            print(f"ERROR: {e}")
            # Save error record
            error_file = output_dir / f"{page_label}_ERROR.txt"
            error_file.write_text(f"Page {idx}\nError: {e}\n", encoding="utf-8")
    
    return results


def compile_markdown(results: list[TranslationResult], output_path: Path):
    """Compile individual JSON results into a single markdown file."""
    lines = []
    lines.append("# Antirevolutionaire Staatkunde — Foreword")
    lines.append("")
    lines.append("**Translated by:** OpenKuyper Gemini Pipeline")
    lines.append("**Model:** gemini-2.5-flash")
    lines.append("**Voice Standard:** OpenKuyper Comprehensive Style Database v1.0")
    lines.append("")
    lines.append("---")
    lines.append("")
    
    for result in results:
        lines.append(f"## Page {result.page_number or '?'}")
        lines.append("")
        lines.append("### Dutch (OCR)")
        lines.append("")
        lines.append(result.dutch_ocr)
        lines.append("")
        lines.append("### English Translation")
        lines.append("")
        lines.append(result.english_translation)
        lines.append("")
        if result.unclear_words:
            lines.append(f"**Unclear words:** {', '.join(result.unclear_words)}")
        if result.notes:
            lines.append(f"**Notes:** {result.notes}")
        lines.append("")
        lines.append("---")
        lines.append("")
    
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Compiled markdown: {output_path}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="OpenKuyper Gemini OCR + Translation Pipeline")
    parser.add_argument("--pdf", type=Path, default=SOURCE_PDF_V1,
                        help="Path to source PDF (default: Vol 1)")
    parser.add_argument("--start", type=int, default=1,
                        help="First page to process (1-indexed)")
    parser.add_argument("--end", type=int, default=20,
                        help="Last page to process (1-indexed)")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR,
                        help="Output directory for results")
    parser.add_argument("--dry-run", action="store_true",
                        help="Convert images but do not call API")
    parser.add_argument("--compile", action="store_true",
                        help="Compile existing JSON results into markdown")
    args = parser.parse_args()
    
    if args.compile:
        # Compile mode: read all JSONs and produce markdown
        json_files = sorted(args.output_dir.glob("*.json"))
        results = []
        for jf in json_files:
            with open(jf, encoding="utf-8") as f:
                data = json.load(f)
            results.append(TranslationResult(**data))
        
        md_path = args.output_dir / "foreword_compiled.md"
        compile_markdown(results, md_path)
        return
    
    # Process mode
    tracker = CostTracker()
    results = process_pages(
        pdf_path=args.pdf,
        start_page=args.start,
        end_page=args.end,
        output_dir=args.output_dir,
        tracker=tracker,
        dry_run=args.dry_run,
    )
    
    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(tracker.report())
    print(f"Output files: {args.output_dir}")
    
    # Auto-compile markdown
    if results and not args.dry_run:
        md_path = args.output_dir / "foreword_draft.md"
        compile_markdown(results, md_path)


if __name__ == "__main__":
    main()
