# OCR Refinement & LaTeX Compilation Plan

> **Status:** This is an AI-generated translation currently under review. The existing English text was produced by AI and needs systematic human verification against the Dutch source. This plan outlines the path forward for refining the OCR, improving the translation, and producing print-ready volumes.

## Part 1: OCR Tool Options for Dutch → English Translation Pipeline

### Tier 1: Best-in-Class (Recommended)

#### 1. **PDFMathTranslate** ⭐ 32.5k stars
- **Repo:** `PDFMathTranslate/PDFMathTranslate`
- **License:** AGPL-3.0
- **Best for:** Full PDF translation with preserved formatting
- **Translation backends:** OpenAI, Gemini, DeepL, Ollama (local), Google
- **Why it fits:** Preserves original layout, produces bilingual output, supports custom translation APIs. Can pipe Dutch PDF → bilingual Dutch/English PDF with original formatting intact.
- **CLI usage:** `pdf2zh antirevolutionai01kuyp.pdf -l en -s nl --service openai`
- **Cost:** Free with Ollama (local), ~$5-15 per volume with Claude/Gemini API
- **Limitation:** Optimized for scientific papers; may need tuning for 19th-century Dutch typography

#### 2. **Marker** ⭐ 33k stars
- **Repo:** `datalab-to/marker` (formerly `VikParuchuri/marker`)
- **License:** GPL-3.0
- **Best for:** PDF → Markdown extraction with high accuracy
- **Why it fits:** Best-in-class PDF-to-Markdown conversion. Handles complex layouts, footnotes, headers. Produces clean Markdown ready for translation pipeline.
- **CLI usage:** `marker_single antirevolutionai01kuyp.pdf output/ --langs nl`
- **Cost:** Free (runs locally on GPU/CPU)
- **Pipeline:** Marker extracts Dutch text → Claude/Gemini translates → human refines

#### 3. **MinerU** ⭐ 57k stars
- **Repo:** `opendatalab/MinerU`
- **License:** Apache-2.0
- **Best for:** Complex document parsing with reading order preservation
- **Why it fits:** Top-ranked in PDF parsing benchmarks. Handles tables, footnotes, multi-column layouts. Outputs clean Markdown/JSON. Better than Marker for documents with complex page layouts.
- **CLI usage:** `magic-pdf -p antirevolutionai01kuyp.pdf -o output/`
- **Cost:** Free (local), or API via OpenDataLoader
- **Pipeline:** MinerU extracts → translation LLM → human review

### Tier 2: Specialized Tools

#### 4. **Docling** ⭐ 56k stars
- **Repo:** `docling-project/docling`
- **License:** MIT
- **Best for:** Document parsing for AI/LLM pipelines
- **Why it fits:** IBM-backed, excellent for structured document extraction. MIT license (most permissive). Good for extracting text that feeds into translation LLMs.

#### 5. **TranslateBooksWithLLMs** ⭐ 555 stars
- **Repo:** `hydropix/TranslateBooksWithLLMs`
- **License:** MIT
- **Best for:** Full-length book translation with format preservation
- **Translation backends:** Ollama, OpenAI, Gemini, Mistral, OpenRouter
- **Why it fits:** Specifically designed for book-length translation. Resumes where left off. No file size limits. Preserves formatting.

#### 6. **translate-book (Claude Code skill)** ⭐ 565 stars
- **Repo:** `deusyu/translate-book`
- **License:** MIT
- **Best for:** Claude-powered parallel book translation
- **Why it fits:** Uses Claude Code's parallel subagents to translate entire books. Fast, high-quality output. Supports PDF/DOCX/EPUB input.

#### 7. **PaddleOCR** ⭐ 73k stars
- **Repo:** `PaddlePaddle/PaddleOCR`
- **License:** Apache-2.0
- **Best for:** Raw OCR when PDF text layer is poor
- **Why it fits:** If the Dutch PDFs have poor text extraction, PaddleOCR can do image-based OCR. Supports 100+ languages. Has Dutch language models.

#### 8. **GLM-OCR** ⭐ 4.2k stars
- **Repo:** `zai-org/GLM-OCR`
- **License:** Apache-2.0
- **Best for:** Fast, comprehensive OCR with AI understanding
- **Why it fits:** Combines OCR with LLM understanding. Good for historical documents with unusual typography.

### Tier 3: Dutch-Specific

#### 9. **byt5-base-dutch-ocr-correction** (Hugging Face)
- **Model:** `ml6team/byt5-base-dutch-ocr-correction`
- **Best for:** Post-OCR correction of Dutch text
- **Why it fits:** Specifically trained to fix OCR errors in Dutch text. Use as a post-processing step after any OCR tool.

---

## Part 2: Recommended OCR Pipeline

### Option A: Local-First (Free, Highest Quality Control)
```
Dutch PDF → MinerU (extraction) → byt5 Dutch OCR correction → 
Claude/Gemini translation (via API) → Human refinement → LaTeX compilation
```
**Cost:** ~$10-20 in API credits for translation
**Time:** 2-3 days of processing + human review

### Option B: All-in-One Translation
```
Dutch PDF → PDFMathTranslate (direct bilingual output) → 
Human refinement against ground truth → LaTeX compilation
```
**Cost:** ~$15-30 in API credits
**Time:** 1-2 days processing + human review

### Option C: Book Translation Pipeline
```
Dutch PDF → Marker (clean Markdown) → TranslateBooksWithLLMs → 
Human refinement → LaTeX compilation
```
**Cost:** ~$10-25 in API credits
**Time:** 2-3 days processing + human review

### Option D: Claude Code Parallel (Fastest)
```
Dutch PDF → Marker (clean Markdown) → translate-book (Claude subagents) → 
Human refinement → LaTeX compilation
```
**Cost:** ~$20-40 in Claude API credits
**Time:** 4-8 hours processing + human review

---

## Part 3: Systematic Translation Workflow

### Phase 1: Source Preparation (Week 1)
1. **Extract Dutch text** from original PDFs using MinerU or Marker
2. **Run Dutch OCR correction** with byt5 model on extracted text
3. **Validate extraction** against original PDFs (spot-check 10% of pages)
4. **Split into chapters/sections** matching original structure
5. **Create tracking spreadsheet** with chapter status (extracted → translated → refined → verified)

### Phase 2: Translation Pipeline (Weeks 2-4)
1. **Batch translate** using chosen pipeline (Option A-D above)
2. **Apply translation protocol** from `config/kuyper_translation_protocol.md`
3. **Ground truth comparison** against Stone Lectures for voice matching
4. **Terminology consistency** check against glossary
5. **Human refinement pass** on each chapter (dutch_source → english_draft → english_refined)
6. **Open review** — publish drafts for public critique and improvement

### Phase 3: Quality Assurance (Week 5)
1. **Cross-reference check** — verify theological terms match De Vries translations
2. **Stylistic audit** — ensure Kuyperian cadence and periodic sentences preserved
3. **Footnote verification** — all citations and references accurate
4. **Parallel text alignment** — Dutch and English line up section-by-section

### Phase 4: LaTeX Compilation (Weeks 6-8)
See Part 4 below for detailed LaTeX plan.

---

## Part 4: LaTeX Compilation Plan

### Volume Structure

Each volume follows this structure:

```latex
\documentclass[11pt,twoside,openright]{book}
% Or use memoir class for more control
\documentclass[11pt,twoside,openright]{memoir}
```

### Volume I: Principles
```
kuyper-vol1/
├── frontmatter/
│   ├── titlepage.tex          # Title page with translator credit
│   ├── copyright.tex          # Rights & attribution page
│   ├── preface.tex            # Translator's preface
│   ├── foreword.tex           # Kuyper's original foreword
│   └── contents.tex           # Table of contents
├── mainmatter/
│   ├── ch01-introduction.tex  # §§ 1-10
│   ├── ch02-concept-of-law.tex
│   ├── ch03-sense-of-right.tex
│   ├── ...                    # All chapters
│   └── chXX-conclusion.tex
├── backmatter/
│   ├── appendix-a-glossary.tex     # Appendix A: Theological Glossary
│   ├── appendix-b-biographical.tex # Appendix B: Biographical Register
│   ├── appendix-c-synopticon.tex   # Appendix C: Syntopicon Cross-References
│   └── index.tex                   # Master Index
├── vol1.tex                   # Master document
└── vol1-style.sty             # Volume-specific style overrides
```

### Volume II: Application
```
kuyper-vol2/
├── frontmatter/
│   ├── titlepage.tex
│   ├── copyright.tex
│   └── contents.tex
├── mainmatter/
│   ├── ch01-suffrage.tex
│   ├── ch02-education.tex
│   ├── ...                    # All application chapters
│   └── chXX-conclusion.tex
├── backmatter/
│   ├── appendix-a-glossary.tex     # Appendix A: Theological Glossary (Vol 2 additions)
│   ├── appendix-b-biographical.tex # Appendix B: Biographical Register (Vol 2 additions)
│   ├── appendix-c-synopticon.tex   # Appendix C: Syntopicon Cross-References
│   └── index.tex
├── vol2.tex
└── vol2-style.sty
```

### Volume III: Companion & Master Index
```
kuyper-vol3/
├── frontmatter/
│   ├── titlepage.tex
│   ├── copyright.tex
│   └── contents.tex
├── mainmatter/
│   ├── part1-glossary.tex     # Encyclopedic Glossary of Neo-Calvinist Concepts
│   ├── part2-biographical.tex # Biographical Register of Key Figures
│   └── part3-index.tex        # Master Index
├── backmatter/
│   ├── appendix-a-timeline.tex     # Appendix A: Kuyper's Life & Historical Timeline
│   ├── appendix-b-bibliography.tex # Appendix B: Bibliography & Source References
│   └── appendix-c-methodology.tex  # Appendix C: Translation Methodology & AI Disclosure
├── vol3.tex
└── vol3-style.sty
```

### Two Appendices Per Volume

**Appendix A: Theological Glossary** (per volume)
- Volume-specific terms with definitions
- Cross-references to other volumes
- Dutch original terms with English translations
- Sphere Sovereignty, Common Grace, Antithesis, etc.

**Appendix B: Biographical Register** (per volume)
- Figures mentioned in that volume
- Groen van Prinsterer, Thorbecke, Schaepman, etc.
- Brief biographical sketches with relevance to Kuyper's argument

**Volume III Additional Appendices:**
- **Appendix A:** Kuyper's Life & Historical Timeline (1837-1920)
- **Appendix B:** Bibliography & Source References (all works cited)
- **Appendix C:** Translation Methodology & AI Disclosure

### Master Style Package (`kuyper-common.sty`)
```latex
% Shared across all volumes
\usepackage{fontspec}
\usepackage{polyglossia}
\setmainlanguage{english}
\setotherlanguage{dutch}

% Typography: Garamond or similar classical serif
\setmainfont{EB Garamond}[
  Ligatures=TeX,
  Numbers=OldStyle,
]

% Section formatting matching Kuyper's original § numbering
\newcommand{\sectionnum}[1]{\S\,#1}

% Dutch term highlighting
\newcommand{\dutch}[1]{\textit{#1}}
\newcommand{\term}[2]{\textbf{#1} (\dutch{#2})}

% Footnote style matching scholarly edition
\renewcommand{\thefootnote}{\arabic{footnote}}

% Page headers with volume/chapter info
\pagestyle{ruled}
```

### Build System
```makefile
# Makefile for building all volumes
VOLUMES = vol1 vol2 vol3

all: $(VOLUMES)

vol1:
	cd kuyper-vol1 && xelatex vol1.tex && biber vol1 && xelatex vol1.tex && xelatex vol1.tex

vol2:
	cd kuyper-vol2 && xelatex vol2.tex && biber vol2 && xelatex vol2.tex && xelatex vol2.tex

vol3:
	cd kuyper-vol3 && xelatex vol3.tex && biber vol3 && xelatex vol3.tex && xelatex vol3.tex

clean:
	rm -f */*.aux */*.log */*.out */*.toc */*.bbl */*.blg

pdf: all
	# Output: kuyper-vol1/vol1.pdf, kuyper-vol2/vol2.pdf, kuyper-vol3/vol3.pdf
```

### Index Generation
```bash
# Use existing NLP-enhanced index data
python scripts/generate_latex_index.py \
  --input editions/Antirevolutionary_Politics_Vol3_Master_Index.md \
  --output kuyper-vol3/mainmatter/part3-index.tex

# Generate synopticon cross-references
python scripts/generate_latex_synopticon.py \
  --input scripts/synopticon_data.json \
  --output kuyper-vol3/backmatter/appendix-c-synopticon.tex
```

### Print-Ready Output
- **Trim size:** 6" × 9" (standard academic)
- **Font:** EB Garamond 11pt (classical, readable)
- **Margins:** 0.75" inner, 0.5" outer (gutter for binding)
- **Headers:** Chapter title (verso) / Section title (recto)
- **Footnotes:** Bottom of page, single-spaced
- **Output:** PDF suitable for print-on-demand (IngramSpark, Amazon KDP)

---

## Part 5: Cost Estimates

| Pipeline | OCR Cost | Translation Cost | Human Review | Total |
|----------|----------|-----------------|-------------|-------|
| Option A (Local MinerU) | $0 | $10-20 | 40-60 hrs | $10-20 + time |
| Option B (PDFMathTranslate) | $0 | $15-30 | 30-50 hrs | $15-30 + time |
| Option C (Marker + TranslateBooks) | $0 | $10-25 | 40-60 hrs | $10-25 + time |
| Option D (Marker + Claude parallel) | $0 | $20-40 | 20-40 hrs | $20-40 + time |

**Recommendation:** Option D for speed, Option A for cost control. Both produce equivalent quality — the difference is in processing time and human review burden.

---

## Part 6: Next Steps

1. **Choose OCR pipeline** from options above
2. **Set up LaTeX project structure** in this repo (`kuyper-vol1/`, `kuyper-vol2/`, `kuyper-vol3/`)
3. **Install dependencies** (`pip install marker-pdf`, `pip install pdf2zh`, etc.)
4. **Run extraction** on Dutch source PDFs
5. **Begin systematic translation** chapter by chapter
6. **Compile LaTeX** as chapters are completed (incremental builds)
7. **Generate indices** from completed translation data
8. **Final proofread** and print-ready PDF generation
