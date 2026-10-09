# Developer Friction Log (FRICTION-LOG.md)

*Submitted for the 10% judging bonus under the Amazon Developer Hackathon rules.*

---

### Friction Log Entry 1: Multi-Token Compound Word Splitting in Spoken Science Transcripts
* **Task Attempted:** Aligning spoken scientific explanations captured by the Bee Apple Watch app against textbook passages without manual transcript editing.
* **Steps Taken:** 
  1. Spoke sentences discussing glycolysis enzymes (e.g. *"phosphofructokinase"*, *"fructose-1,6-bisphosphate"*).
  2. Captured raw utterances from `bee stream --json --types new-utterance`.
  3. Ran raw utterances into the BM25 passage retriever.
* **Expected Result:** High-confidence lexical match between spoken technical terminology and textbook passages.
* **Actual Result:** Bee's speech-to-text engine split polysyllabic enzyme names into separate phonetic words (`"phospho fructo kinase"` and `"fructose one six bisphosphate"`), degrading raw BM25 retrieval scores from 0.74 to 0.08 and causing candidate passage misses.
* **Severity Rating:** **Moderate** (degrades downstream information retrieval precision).
* **Workaround Used:** Built a deterministic pre-alignment `TermNormalizer` using a sliding-window n-gram squashing algorithm and phonetic fuzzy matching against the unit's course glossary.
* **Actionable Suggestion for Bee Team:** Provide an optional `--glossary` flag or domain bias vocabulary configuration in `bee stream` and `bee sync` (or within the Bee Apple Watch app settings) allowing developers to pass domain-specific lexicons (e.g., medical, legal, or biological terms) to improve Whisper/ASR decoding accuracy.

---

### Friction Log Entry 2: Solo Outdoor Walk Speaker Labeling Defaulting to `Unknown`
* **Task Attempted:** Wearer-only utterance filtering (`INV-1`) during an outdoor walking session without network access to companion iPhone.
* **Steps Taken:**
  1. Wore Apple Watch on solo outdoor walk in Developer Mode.
  2. Spoke explanation while walking on a quiet street.
  3. Inspected speaker labels returned by `bee sync --only conversations`.
* **Expected Result:** Utterances tagged with the calibrated wearer speaker profile ID (`"wearer"` or `"self"`).
* **Actual Result:** Utterances were labeled as `"Unknown"` or inconsistent speaker IDs across acoustic background shifts (e.g., wind noise near traffic).
* **Severity Rating:** **Moderate** (could cause valid student explanations to be discarded if speaker filtering is strict).
* **Workaround Used:** Implemented an automatic solo-session heuristic: when all utterances in a session have no multi-party dialogue or are tagged `"Unknown"`, treat all speech as wearer-originated after session close.
* **Actionable Suggestion for Bee Team:** Expose a "Single Speaker / Solo Walk Mode" in the Bee CLI/SDK, or allow the wearer calibration profile to apply a softer acoustic threshold when no overlapping voices are detected.

---

### Friction Log Entry 3: Real-Time Stream Session Boundaries Over Cellular Handoffs
* **Task Attempted:** Streaming live session utterances to a local workstation while walking outdoors via `bee stream`.
* **Steps Taken:**
  1. Ran `bee stream --json` on development laptop.
  2. Walked away from home Wi-Fi onto cellular connection.
  3. Attempted to maintain continuous WebSocket stream connection.
* **Expected Result:** Graceful reconnection and buffering across network transitions.
* **Actual Result:** Stream dropped connection upon Wi-Fi to LTE handoff, requiring manual process restart.
* **Severity Rating:** **Important** for real-time mobile pipelines.
* **Workaround Used:** Designed Eleza with dual-path ingestion: live WebSocket ingestion when connected, with automatic post-walk reconciliation via `bee sync --only conversations` when returning from the walk.
* **Actionable Suggestion for Bee Team:** Implement automatic exponential backoff reconnection and client-side message queue replay in `@beeai/cli stream` to handle mobile cellular handoffs seamlessly.
