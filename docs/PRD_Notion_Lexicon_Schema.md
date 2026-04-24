# PRD: Notion Lexicon Schema — Two-Database Architecture

> **For:** Notion AI (autofill)  
> **Project:** OpenKuyper — Abraham Kuyper's *Antirevolutionaire Staatkunde* translation  
> **Goal:** Replace the flat 1:1 termbase with a polysemy-aware two-database schema  
> **Status:** Draft — ready for Notion AI to review and build  

---

## 1. Problem Statement

The current **📚 Project Lexicon** uses one row per Dutch term with a single `Preferred English` field. This fails for polysemous terms like:

| Dutch term | English senses | Current failure |
|---|---|---|
| **recht** | law (statute), Right (moral order), justice, legal entitlement | One row forced to `law / right` — pipeline can't choose |
| **volk** | people (organic), nation (political), populace (crowd) | Context-oblivious rendering |
| **geest** | spirit (human), Spirit (Holy) | Capitalization rule depends on sense, not just term |
| **vermogen** | faculty (psychological), power (political), wealth (economic) | Wrong domain = wrong register |

**Consequence:** The translation pipeline (`pipeline/termbase.py`, `three_tier_pipeline.py`) cannot auto-select the correct English rendering. Humans must intervene in every paragraph.

---

## 2. Solution: Two Linked Databases

Split the lexicon into:

1. **📚 Project Lexicon** — canonical lemmas (terms)
2. **🔬 Lexicon Senses** — individual semantic senses (synsets), linked to lemmas

This mirrors WordNet architecture: `Lemma → [Sense 1, Sense 2, Sense 3]`.

---

## 3. Database 1: 📚 Project Lexicon (enhanced existing)

**Parent page:** `0f4ec9a4-4002-4124-afd1-70e586a6ddf8` (Kuyper Translation workspace)

### Properties to keep (from existing DB `b675507f-bad8-4478-abeb-00745a893f65`)

| Property | Type | Existing? | Notes |
|---|---|---|---|
| Term (Dutch/Latin) | Title | ✅ Keep | Canonical lemma |
| Status | Status | ✅ Keep | Proposed → Approved → Locked |
| Key Term Tag | Multi-select | ✅ Keep | Recht-family, State/Overheid, Church/ecclesiology, Movements/Proper nouns, Latin/Greek |
| Appears in | Multi-select | ✅ Keep | Foreword, Vol 1 — Ch I, Vol 1 — Ch II+, Vol 2 |
| Owner | People | ✅ Keep | Translator owner |
| Created | Created time | ✅ Keep | Auto |
| Last edited | Last edited time | ✅ Keep | Auto |

### Properties to add

| Property | Type | Purpose |
|---|---|---|
| **Senses** | **Relation → 🔬 Lexicon Senses** | **NEW.** One-to-many link. Every term can have 1–N senses. |
| **Sense Count** | Formula (number) | `prop("Senses").length()` — quick visual of polysemy |
| **ODWN Enriched** | Checkbox | True if the Notion Worker has auto-populated senses from Dutch WordNet |
| **Drift Alerts** | Rich text | Auto-populated by worker when pipeline detects wrong sense usage |
| **Treatment (default)** | Select | Keep (italicize), Render, Render + keep on first occurrence, Contextual (see rules) — fallback when no sense-specific rule matches |
| **Notes** | Rich text | General translator notes about the term |

### Properties to remove

| Property | Action | Why |
|---|---|---|
| Preferred English | **Remove** | Moved to 🔬 Lexicon Senses (sense-specific) |
| Disallowed variants | **Remove** | Moved to 🔬 Lexicon Senses (sense-specific) |
| Context Rules | **Remove** | Moved to 🔬 Lexicon Senses (sense-specific, per-sense triggers) |
| First-occurrence gloss | **Remove** | Moved to 🔬 Lexicon Senses |
| Examples (authoritative) | **Remove** | Moved to 🔬 Lexicon Senses |
| Scope / Definition | **Remove** | Moved to 🔬 Lexicon Senses |

---

## 4. Database 2: 🔬 Lexicon Senses (new)

**Parent page:** Same as 📚 Project Lexicon (`0f4ec9a4-4002-4124-afd1-70e586a6ddf8`)

**Title:** `🔬 Lexicon Senses`

**Description:** `Individual semantic senses (synsets) for Dutch terms. One term = many senses. Each sense has its own English rendering, domain, and context trigger.`

### Properties

| Property | Type | Required | Description / Example |
|---|---|---|---|
| **Sense ID** | Title | ✅ | Unique ID. Format: `{term}-{sense-key}` or ODWN synset ID. E.g., `recht-law`, `recht-right`, `recht-justice` |
| **Parent Term** | Relation → 📚 Project Lexicon | ✅ | Back-link to the canonical lemma |
| **Preferred English** | Rich text | ✅ | The exact English rendering for THIS sense only. E.g., for `recht-law`: `"law"`; for `recht-right`: `"Right"` (capitalized) |
| **Disallowed variants** | Rich text | ❌ | Variants that must NOT be used for this sense. E.g., for `recht-law`: `"justice, right, statute"` |
| **Gloss (Dutch)** | Rich text | ❌ | ODWN definition or manual definition in Dutch. E.g., `"een door de overheid vastgestelde regel"` |
| **Domain** | Select | ✅ | `politics` / `law` / `theology` / `philosophy` / `psychology` / `history` / `general` |
| **Context Trigger** | Rich text | ✅ | **The most important field.** Rules for WHEN to use this sense. Natural language + keyword triggers. E.g., `"INSTITUTIONAL context: preceded by 'geschreven', 'staats-', 'burgerlijk'; discussing courts, legislation, legal systems"` |
| **Part of Speech** | Select | ❌ | `noun` / `verb` / `adjective` / `adverb` / `proper noun` |
| **ILI (Princeton WN)** | Rich text | ❌ | Inter-Lingual Index code linking to Princeton WordNet. E.g., `i12345` |
| **ODWN Synset ID** | Rich text | ❌ | Original Open Dutch WordNet synset identifier |
| **Examples (authoritative)** | Rich text | ❌ | 1–2 approved sentence usages from the translation |
| **Confidence** | Select | ✅ | `High` / `Medium` / `Low` |
| **Status** | Status | ✅ | `Proposed` → `Approved` → `Locked` |
| **Treatment** | Select | ❌ | Override the parent term's default treatment for this sense. Options: `Keep (italicize)`, `Render`, `Render + keep on first occurrence`, `Contextual (see rules)` |
| **First-occurrence gloss** | Rich text | ❌ | Exact parenthetical/footnote wording for first occurrence of THIS sense |
| **Created** | Created time | ✅ | Auto |
| **Last edited** | Last edited time | ✅ | Auto |

### Select options to pre-populate

**Domain:**
- politics
- law
- theology
- philosophy
- psychology
- history
- general

**Confidence:**
- High
- Medium
- Low

**Status (Status type):**
- Proposed (To-do group)
- Approved (In progress group)
- Locked (In progress group)
- Deprecated (Complete group)

**Treatment:**
- Keep (italicize)
- Render
- Render + keep on first occurrence
- Contextual (see rules)

**Part of Speech:**
- noun
- verb
- adjective
- adverb
- proper noun

---

## 5. Example Data (pilot terms)

### 📚 Project Lexicon — `recht`

| Property | Value |
|---|---|
| Term (Dutch/Latin) | `recht` |
| Status | Approved |
| Key Term Tag | Recht-family, State/Overheid |
| Appears in | Foreword, Vol 1 — Ch I |
| Senses | → linked to 3 sense rows |
| Sense Count | 3 |
| ODWN Enriched | ✅ |
| Treatment (default) | Contextual (see rules) |
| Notes | Polysemous core term. Always disambiguate by domain. |

### 🔬 Lexicon Senses — row 1: `recht-law`

| Property | Value |
|---|---|
| Sense ID | `recht-law` |
| Parent Term | → `recht` |
| Preferred English | `law` |
| Disallowed variants | `justice, right, statute` |
| Gloss (Dutch) | `een door de overheid vastgestelde regel` |
| Domain | `law` |
| Context Trigger | `INSTITUTIONAL context: preceded by "geschreven", "staats-", "burgerlijk"; discussing courts, legislation, legal systems, positive law. "Rechtsstaat" = "constitutional state". "Bron van het recht" when discussing legislation = "source of law"` |
| Part of Speech | `noun` |
| Confidence | `High` |
| Status | `Locked` |
| Treatment | `Render` |
| First-occurrence gloss | — |

### 🔬 Lexicon Senses — row 2: `recht-right`

| Property | Value |
|---|---|
| Sense ID | `recht-right` |
| Parent Term | → `recht` |
| Preferred English | `Right` |
| Disallowed variants | `law, justice, privilege` |
| Gloss (Dutch) | `dat wat moreel juist is; het goede, het schone, het ware, het recht` |
| Domain | `philosophy` |
| Context Trigger | `MORAL/THEOLOGICAL context: contrasted with "Onrecht" (wrong/injustice); in the philosophical tetrad alongside Good, True, Beautiful; discussing divine ordinance, God's justice, natural law. "Bron van het recht" when discussing God's ordinance = "source of Right". Capitalize when used as noun of art.` |
| Part of Speech | `noun` |
| Confidence | `High` |
| Status | `Locked` |
| Treatment | `Render` |
| First-occurrence gloss | `Right (divine moral order)` |

### 🔬 Lexicon Senses — row 3: `recht-justice`

| Property | Value |
|---|---|
| Sense ID | `recht-justice` |
| Parent Term | → `recht` |
| Preferred English | `justice` |
| Disallowed variants | `law, right` |
| Gloss (Dutch) | `gerechtigheid; recht doen` |
| Domain | `philosophy` |
| Context Trigger | `PREDICATE context: in verbal constructions like "recht doen" = "to do justice"; abstract discussion of fairness and equity (not statutory law, not divine ordinance).` |
| Part of Speech | `noun` |
| Confidence | `Medium` |
| Status | `Approved` |
| Treatment | `Render` |
| First-occurrence gloss | — |

---

## 6. Views to create

### 📚 Project Lexicon views

1. **All Terms** (default table) — all properties visible
2. **Polysemous Terms** (table) — filter: `Sense Count > 1`
3. **Needs Enrichment** (table) — filter: `ODWN Enriched is Unchecked`
4. **Locked** (table) — filter: `Status = Locked`
5. **By Domain** (board) — group by `Key Term Tag`

### 🔬 Lexicon Senses views

1. **All Senses** (default table)
2. **By Parent Term** (table) — group by `Parent Term`
3. **By Domain** (board) — group by `Domain`
4. **Locked Senses** (table) — filter: `Status = Locked`
5. **Needs Review** (table) — filter: `Status = Proposed`
6. **Recht-family** (table) — filter: `Parent Term.Key Term Tag contains Recht-family`

---

## 7. Integration with existing Notion DB

The existing **📚 Project Lexicon** (`b675507f-bad8-4478-abeb-00745a893f65`) has **70 entries** already populated. The migration path:

1. **Back up existing data** (export to CSV)
2. **Add the new properties** (Senses relation, Sense Count, ODWN Enriched, Drift Alerts, Treatment default, Notes)
3. **Create 🔬 Lexicon Senses** as a new database on the same parent page
4. **For monosemous terms** (single sense): create 1 sense row, copy `Preferred English` and `Context Rules` into it, link it back
5. **For polysemous terms** (e.g., `recht`, `volk`, `geest`): create multiple sense rows, manually split the existing `Preferred English` and `Context Rules` across senses
6. **Remove deprecated properties** from 📚 Project Lexicon once senses are migrated

---

## 8. Success Criteria

- [ ] Every term with >1 sense has ≥2 rows in 🔬 Lexicon Senses
- [ ] The `Context Trigger` field is detailed enough that a non-Dutch-speaking editor can pick the right sense
- [ ] Views allow filtering by domain and by parent term
- [ ] Existing 70 entries are migrated without data loss
- [ ] Notion Worker can read both databases via API and compile `kuyper_termbase.json`

---

## 9. Open Questions

1. Should we add a `Frequency` property to senses (how often each sense appears in the text) for prioritization?
2. Should `Context Trigger` be structured (e.g., keyword list) or freeform natural language?
3. Do we need a third database for **Collocations** (e.g., "recht doen", "in eigen kring")?

---

*Prepared for Notion AI autofill review.*
