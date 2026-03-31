# Kuyper Translation Protocol

> **Status:** This is an AI-generated translation currently under review. This protocol defines the standards for refining and verifying the translation against the Dutch source text.

## 1. Core Objective & Persona

This protocol governs the English translation and refinement of Abraham Kuyper's *Antirevolutionary Politics*. The overarching goal is to achieve a formal, scholarly, and exactingly precise translation that captures Kuyper's dominant, authoritative, and deeply theological public voice.

The translation must reject modern colloquialisms and dynamic equivalence where it risks theological imprecision. The target register is Late 19th/Early 20th Century Academic Reformed prose, mirroring the exact aesthetic of *Lectures on Calvinism*.

This is an **open translation** — the current AI-generated draft is under review and open to public critique and improvement.

## 2. Ground Truth Benchmarks

- **Primary Voice Ground Truth:** *Lectures on Calvinism* (1898 Stone Lectures). This is the definitive standard for Kuyper's English cadence, argument structure, and rhetorical force.
- **Terminological Ground Truth:** *The Work of the Holy Spirit* and *To Be Near Unto God* (trans. Henri de Vries / John Hendrik de Vries). These serve as the baseline for precise theological nomenclature and devotional warmth where it intersects with political theory.

## 3. Stylometric Constraints (The Kuyperian Aesthetic)

- **Cadence & Syntax:** Kuyper writes in sweeping, highly structured periodic sentences. Do not arbitrarily chop his long sentences into staccato modern English unless the original Dutch syntax makes the English entirely unreadable. Preserve his structural parallelism (e.g., "Not A, but B"; "Just as X, so also Y").
- **Rhetorical Posture:** Authoritative, architectonic, and polemical, yet grounded in adoration. He speaks as a statesman-theologian.
- **Vocabulary:** Use elevated, precise, and classical vocabulary (e.g., *ordinance*, *sphere*, *sovereignty*, *antithesis*, *regeneration*, *organic*). Avoid modern secular sociology terms (do not use *values*, *lifestyle*, *social construct*).

## 4. Theological & Semantic Mandates (Sphere Sovereignty)

- **Sphere Sovereignty (Souvereiniteit in eigen kring):** Translate consistently. The concept that state, church, family, and society have independent authority delegated directly by God.
- **Common Grace (Gemeene Gratie):** Translate consistently. God's restraint of sin and bestowal of natural gifts upon the unregenerate.
- **Antithesis:** The fundamental spiritual division between the regenerate (those guided by the Word of God) and the unregenerate (those operating from human autonomy).
- **The Ordinances of God:** Translate *ordinantiën* as "ordinances" or "divine decrees," never merely as "rules" or "laws."
- **Organic vs. Mechanical:** Preserve Kuyper's distinction between *organic* (living, God-ordained natural growth like the family or society) and *mechanical* (artificial, state-imposed structures).

## 5. Execution Pipeline Directives (OpenCode Agent)

When refining the draft using `gemini-2.5-flash` or `gemini-2.5-pro`:

1. **Source Alignment:** Compare the existing English draft strictly against the `dutch_source.md` to identify mistranslations, dropped nuances, or flattened rhetoric.
2. **Review against Ground Truth:** Does the refined English match the syntactic weight and vocabulary of *Lectures on Calvinism*?
3. **No Paraphrasing:** Do not summarize. Maintain the full weight and length of Kuyper's argument.

## 6. Formatting

- Retain all paragraph breaks exactly as they appear in the Dutch source.
- Section headers (e.g., § 1. ...) must be kept intact and formatted cleanly in Markdown.
- Footnotes and annotations must be preserved.
