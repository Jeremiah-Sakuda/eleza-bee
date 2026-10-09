# eleza-align

A standalone, deterministic claim-to-passage alignment library for spoken learning transcripts, oral assessments, and wearable audio.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`eleza-align` solves a key challenge in conversational learning and oral defense: **measuring what a speaker explained without notes against a canonical source text.**

Rather than prompting a generative model with an open-ended "rate this answer" prompt, `eleza-align` implements an invariant-preserving, four-stage pipeline:

1. **Claim Segmentation:** Breaks spoken transcripts at sentence boundaries while deterministically filtering verbal disfluencies ("um", "like", "so basically").
2. **Hybrid Candidate Retrieval:** Pairs BM25 lexical search with ngram/dense scoring to identify the top-$k$ candidate passages within the unit curriculum. Below-threshold claims are pruned as unaligned.
3. **Strict Invariant Pair Verification (INV-2):** Classifies candidate pairs as `supports`, `contradicts`, or `unrelated`. Requires exact substring verification against the cited text.
4. **Unit Coverage Aggregation:** Reports exact coverage: what was **Covered**, what was **Skipped**, and what was **Contradicted**, with side-by-side evidence spans.

`eleza-align` has no dependency on specific wearables or biology domains; it accepts transcripts with utterance IDs and passages with passage IDs.

## Installation

```bash
pip install eleza-align
```

## Quick Example

```python
from eleza_align import ClaimSegmenter, HybridRetriever, PairLabeler, CoverageEngine
from eleza_align.models import Passage, TranscriptUtterance

# 1. Define source passages
passages = [
    Passage(
        passage_id="p01",
        text="Hexokinase phosphorylates glucose into glucose-6-phosphate consuming one ATP.",
        sentences=["Hexokinase phosphorylates glucose into glucose-6-phosphate consuming one ATP."]
    )
]

# 2. Segment transcript
segmenter = ClaimSegmenter()
utterances = [
    TranscriptUtterance(utterance_id="u01", text="Um, so first hexokinase takes glucose and uses an ATP to phosphorylate it.", speaker="wearer")
]
claims = segmenter.segment_utterances(utterances)

# 3. Retrieve & Label
retriever = HybridRetriever(passages)
candidates = retriever.retrieve(claims[0], top_k=2)

labeler = PairLabeler()
results = labeler.label_pairs([(claims[0], p) for p in candidates])
```

## Invariants

- **INV-2 Source-bound:** Every covered and contradicted claim cites an exact substring from the passage.
- **INV-3 Evidence, not verdict:** Reports the speaker's words next to the text's words. No arbitrary score.
- **INV-4 Deterministic first:** Claim pruning and retrieval are rule- and metric-based before any LLM verification.
