# Eleza (Bee Wearable AI)

> **Eleza shows you what you can explain without the notes in front of you.**

Built for the **Amazon Developer Hackathon: Build, Ship, Shape**  
* **Primary Track:** Bee (Wearable AI) — *Education Priority*  
* **Mini Challenge:** Open Source (`eleza-align`)  

---

## 1. The Problem

Students study by re-reading notes or listening to lecture recordings, which creates an illusion of competence. Explaining material out loud, unaided, is what builds lasting retention (the Feynman technique / retrieval practice). Almost nobody does it because nothing tells them whether what they said was accurate. Meanwhile, oral assessment is expanding across universities (e.g., BU EC 427 grading code via interview), so the first time students discover their gaps is when they are already being graded.

Eleza turns an outdoor walk into an active recall session:
1. **Screenless Capture:** The student speaks out loud while walking wearing Bee (on Apple Watch). No notes, no screen checks.
2. **Never Interrupts (INV-5):** Eleza never breaks the student's train of thought while walking.
3. **Evidence, Not Verdict (INV-3):** After the session closes, the report arrives. It shows what was **Covered**, what was **Skipped**, and where the student **Contradicted** the text—displaying the student's exact words next to the textbook's words. No arbitrary score or grade.
4. **On-Wrist Gap Prompt (ELZ-501):** The next morning, the wrist displays a single reminder targeting yesterday's gap (*"Yesterday you skipped the role of NAD+. Try it on today's walk."*).
5. **Longitudinal Memory Ledger (ELZ-600):** Over weeks, an append-only ledger tracks which concepts hold without notes and which keep slipping.

---

## 2. Architecture

```
Apple Watch running Bee
      │  (Bee processes audio, produces transcript)
      ▼
bee stream / bee sync  ──►  Eleza session service
                                 │
                                 ├─ Session boundaries: vocal start/stop markers or silence timeout (ELZ-103)
                                 ├─ Term normalization against unit glossary (ELZ-105)
                                 ├─ eleza-align (open-source MIT package):
                                 │     Claim segmenter → Hybrid retriever → Pair labeler (INV-2) → Coverage
                                 ├─ Parallel span report builder (ELZ-401)
                                 ├─ Append-only memory ledger (ELZ-601)
                                 └─ Bee MCP (ELZ-502): daily context & facts integration
                                 │
                                 ▼
                     Mirrored Apple Watch notification after walk: "Glycolysis: 10 of 14 ideas, 1 contradiction"
                     Interactive parallel span review on phone
                     Next-morning gap prompt on the wrist
```

---

## 3. Open Source Mini-Challenge: `eleza-align`

As part of the Open Source Mini-Challenge, the core domain logic has been decoupled into a standalone, MIT-licensed Python package: **`eleza-align`** (located in [`eleza-align/`](file:///Users/jerem/Desktop/Projects/2025%20Fall%20Projects/2026%20Fall%20Projects/Amazon%20Developer%20Hackathon/Eleza/eleza-align/)).

* **Package:** `eleza-align` (MIT License)
* **What it does:** Provides a domain-agnostic, invariant-preserving primitive for aligning spoken conversational transcripts against authoritative texts.
* **Why it matters:** Solves the hallucination and evaluation problem for oral defense and wearable audio by enforcing character-exact substring verification (**INV-2**).
* **Test Suite & Benchmarks:** 10 hand-labeled test fixtures achieving **90.9% retrieval hit rate @ k=3** and **100% Invariant-2 verification**.

---

## 4. Significant Update Statement (Rules Compliance)

Before August 31, 2026, Eleza existed as an instructor-side post-hoc tool for analyzing pre-recorded oral defense recordings.

**Everything in this submission was built during the hackathon submission window (Aug 31 – Oct 23, 2026):**
* Real-time Bee wearable audio integration on Apple Watch via `@beeai/cli stream` and `sync`.
* The `eleza-align` standalone library, designed, tested, and open-sourced under MIT.
* Deterministic biochemical `TermNormalizer` with sliding-window n-gram squashing.
* Ingestion pipeline for OpenStax Biology 2e Chapter 7 with stable paragraph IDs and key idea mapping.
* The student-side review surface with parallel span comparison and dispute actions (*"I said it differently"*).
* Append-only longitudinal ledger, weekly recurrence insights, and next-day wrist gap prompts.
* The pre-hackathon baseline commit is tagged `pre-hackathon`.

---

## 5. Quickstart & Testing

### Installation

```bash
# 1. Clone repository
git clone https://github.com/jerem/eleza.git
cd eleza

# 2. Create virtual environment & install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -e eleza-align
pip install -r requirements.txt
```

### Running Test Suite

```bash
# Run all unit tests across normalizer, pipeline, and server
PYTHONPATH=eleza-align/src:. pytest -v
```

### Launching the Review Surface

```bash
# Start the local review surface and watch preview
python3 -m uvicorn eleza.server:app --reload --port 8000
```
Open [http://localhost:8000](http://localhost:8000) to inspect the parallel span review, run walk simulations, and view the longitudinal ledger.

---

## 6. Developer Feedback & Friction Logs

* Full empirical findings and benchmark numbers: [`docs/FINDINGS.md`](file:///Users/jerem/Desktop/Projects/2025%20Fall%20Projects/2026%20Fall%20Projects/Amazon%20Developer%20Hackathon/Eleza/docs/FINDINGS.md)
* Devpost 6-field friction log for 10% bonus: [`docs/FRICTION-LOG.md`](file:///Users/jerem/Desktop/Projects/2025%20Fall%20Projects/2026%20Fall%20Projects/Amazon%20Developer%20Hackathon/Eleza/docs/FRICTION-LOG.md)
* Engineering build log: [`docs/BUILD-LOG.md`](file:///Users/jerem/Desktop/Projects/2025%20Fall%20Projects/2026%20Fall%20Projects/Amazon%20Developer%20Hackathon/Eleza/docs/BUILD-LOG.md)

### Product Feedback on Bee Developer Tools:
* **Bee CLI (`@beeai/cli 0.7.3`):** Fast setup, clean command structure (`stream`, `sync`, `mcp`, `facts`). Onboarding took under 10 minutes.
* **What worked well:** The JSON streaming flag (`--json --types new-utterance`) delivers clean real-time events with low latency.
* **What needs work:** Polysyllabic technical terms are frequently split into separate tokens; cellular network handoffs require manual stream reconnections.
* **Would build again?** **Yes.** Bee enables a fundamentally calm, ambient interaction paradigm that smartphones cannot replicate.

---

## 7. Attribution & License

* `eleza-align` is licensed under the [MIT License](file:///Users/jerem/Desktop/Projects/2025%20Fall%20Projects/2026%20Fall%20Projects/Amazon%20Developer%20Hackathon/Eleza/eleza-align/LICENSE).
* Course text: OpenStax *Biology 2e* (Chapter 7: Cellular Respiration / Glycolysis), licensed under [Creative Commons Attribution 4.0 International (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).
