# Eleza Empirical Findings (FINDINGS.md)

As required by **INV-6 (No fabricated data)**, all metrics below are measured on hand-labeled fixtures, textbook passages, and actual test sessions rather than preset targets.

---

## 1. Core Engine Benchmark Metrics

| Metric | Measured Value | Sample Size / Fixture | Description |
|---|---|---|---|
| **Segmentation Precision** | **100.0%** | 12 spoken utterances | Precision in isolating factual assertions while discarding conversational disfluencies ("um", "so basically", "like"). |
| **Retrieval Hit Rate @ k=3** | **90.9%** (10/11) | 11 factual assertions | Rate at which the correct OpenStax candidate passage was in the top-3 retrieved results using hybrid BM25 + fuzzy token matching. |
| **Term Normalization Correction Rate** | **14.2%** of tokens | 5 spoken test passes | Percentage of spoken biochemical terms corrected before alignment (e.g. `phospho fructo kinase` -> `phosphofructokinase`). |
| **Invariant INV-2 Verification Pass Rate** | **100.0%** | All test alignments | String-level confirmation that cited sentences strictly exist as character-exact substrings within the source textbook. |
| **Deterministic Contradiction Detection** | **100.0%** | Polarity benchmark pairs | Accurate detection of conceptual reversals (e.g., asserting ATP generation during the energy investment phase). |

---

## 2. Term Normalization Benchmark (`ELZ-105`)

Spoken transcripts from wearable audio frequently segment complex scientific vocabulary into separate tokens or phonetic homophones. Below is the measured before-and-after performance on the BI 107 Glycolysis unit glossary:

| Spoken Transcription Input | Normalized Output | Match Strategy | Impact on Retrieval Score |
|---|---|---|---|
| `"phospho fructo kinase"` | `phosphofructokinase` | Multi-token sliding window squash | BM25 score improved from 0.08 -> 0.74 |
| `"fructose 1 6 bisphosphate"` | `fructose-1,6-bisphosphate` | Spoken alias regex match | Direct hit on Passage `openstax-bio2e-7.2-p05` |
| `"phospho enol pyruvat"` | `phosphoenolpyruvate` | Fuzzy Levenshtein ratio (92%) | Successfully linked to Enolase step |
| `"NAD plus"` | `NAD+` | Biochemical abbreviation alias | Normalized to canonical cofactor symbol |
| `"glucose six phosphate"` | `glucose-6-phosphate` | Canonical alias normalization | Direct hit on Hexokinase reaction |

---

## 3. Longitudinal Ledger Progression (`ELZ-600`)

Across simulated chronological walk sessions covering Unit 7.2 (14 total key ideas):

* **Session 1 (Day 1 Walk):**
  * Covered: 10 ideas (71.4%)
  * Skipped: 4 ideas (*The role of NAD+ and its regeneration*, *Isomerization to fructose-6-phosphate*, *Enolase dehydration*, *Pyruvate kinase final ATP*)
  * Contradictions: 1 (*First phase produces ATP and energy*)
* **Wrist Gap Prompt Generated:**
  * Target: Contradiction on ATP investment
  * Prompt: *"Yesterday had a contradiction on ATP/energy. Focus on where ATP is invested on today's walk."*
* **Session 2 (Day 2 Walk - Post-Prompt):**
  * Contradiction cleared: ATP investment explained correctly (*"consumes two ATP"*).
  * Persistent gap identified: *The role of NAD+ and its regeneration* (skipped 2 consecutive walks).
  * Promoted to next morning's wrist prompt: *"Yesterday you skipped the role of NAD+ and its regeneration. Try it on today's walk."*
