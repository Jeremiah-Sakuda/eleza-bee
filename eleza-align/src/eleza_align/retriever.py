"""
Candidate Passage Retrieval Engine (ELZ-302, INV-4)
Hybrid lexical (BM25) and token-overlap retrieval with similarity threshold pruning.
"""

from __future__ import annotations
import re
from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz
from eleza_align.models import Claim, Passage

def tokenize(text: str) -> list[str]:
    # Lowercase alphanumeric tokenization
    return re.findall(r'[a-zA-Z0-9\+\-]+', text.lower())

class HybridRetriever:
    def __init__(self, passages: list[Passage], threshold: float = 0.25):
        self.passages = passages
        self.threshold = threshold
        self.corpus_tokens = [tokenize(p.text) for p in passages]
        self.bm25 = BM25Okapi(self.corpus_tokens) if self.corpus_tokens else None

    def retrieve(self, claim: Claim, top_k: int = 3) -> list[tuple[Passage, float]]:
        """
        Returns list of (Passage, score) tuples that meet or exceed self.threshold.
        If no candidate meets the threshold, returns empty list (unaligned).
        """
        if not self.passages or not self.bm25:
            return []

        claim_tokens = tokenize(claim.text)
        if not claim_tokens:
            return []

        bm25_scores = self.bm25.get_scores(claim_tokens)
        max_bm25 = max(bm25_scores) if max(bm25_scores) > 0 else 1.0

        candidates = []
        for idx, passage in enumerate(self.passages):
            # Normalized BM25 score [0, 1]
            norm_bm25 = bm25_scores[idx] / max_bm25 if max_bm25 > 0 else 0.0

            # Token set ratio score [0, 1] using rapidfuzz
            token_ratio = fuzz.token_set_ratio(claim.text, passage.text) / 100.0

            # Hybrid weighted combination (60% BM25, 40% token overlap)
            hybrid_score = round(0.60 * norm_bm25 + 0.40 * token_ratio, 4)

            if hybrid_score >= self.threshold:
                candidates.append((passage, hybrid_score))

        # Sort descending by hybrid score
        candidates.sort(key=lambda x: x[1], reverse=True)
        return candidates[:top_k]
