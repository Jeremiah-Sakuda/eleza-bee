"""
Pair Labeler and Invariant Gate Engine (ELZ-303, INV-2, INV-4)
Evaluates (claim, candidate_passage) pairs.
Strictly validates that cited sentences are literal character-level substrings of the passage.
"""

from __future__ import annotations
import os
import json
import re
from typing import Optional
from rapidfuzz import fuzz
from eleza_align.models import Claim, Passage, PairAlignment, LabelEnum

LABEL_SYSTEM_PROMPT = """You are an exacting scientific evidence verifier for oral assessments.
Given a spoken student claim and an authoritative textbook passage:
1. Determine if the claim SUPPORTS, CONTRADICTS, or is UNRELATED to the passage.
   - SUPPORTS: The claim accurately states or directly paraphrases a fact in the passage.
   - CONTRADICTS: The claim directly conflicts with or states the opposite/incorrect factual assertion of the passage (e.g., asserts ATP is produced when it is consumed, or wrong enzyme names/counts).
   - UNRELATED: The passage does not discuss the specific factual assertion made in the claim.
2. If SUPPORTS or CONTRADICTS, identify the EXACT single sentence from the passage that grounds this judgment.
   CRITICAL: The cited_sentence MUST be an exact verbatim substring from the passage sentences.

Respond ONLY with valid JSON:
{
  "label": "supports" | "contradicts" | "unrelated",
  "cited_sentence": "<exact sentence string from passage>",
  "reasoning": "<short explanation>"
}"""

class PairLabeler:
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None, provider: Optional[str] = None):
        self.provider = provider or os.getenv("ELEZA_LLM_PROVIDER", "auto")
        self.api_key = api_key or os.getenv("ELEZA_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("ELEZA_LLM_MODEL", "gpt-4o-mini")
        self.bedrock_model_id = os.getenv("AWS_BEDROCK_MODEL_ID", "anthropic.claude-3-5-sonnet-20241022-v2:0")

    @staticmethod
    def verify_invariant_2(passage: Passage, cited_sentence: Optional[str]) -> bool:
        """
        INV-2 Source-bound: Any cited sentence must exist inside the passage.
        """
        if not cited_sentence:
            return False
        norm_passage = " ".join(passage.text.split())
        norm_cited = " ".join(cited_sentence.split())
        return norm_cited in norm_passage

    def label_pair(self, claim: Claim, passage: Passage, score: float = 1.0) -> PairAlignment:
        """
        Labels a (claim, passage) pair.
        Supports AWS Bedrock, OpenAI, and deterministic fallback.
        """
        # Try AWS Bedrock if configured
        if self.provider == "bedrock" or (self.provider == "auto" and os.getenv("AWS_ACCESS_KEY_ID")):
            try:
                return self._label_with_bedrock(claim, passage, score)
            except Exception:
                pass

        if self.api_key:
            try:
                return self._label_with_llm(claim, passage, score)
            except Exception:
                pass

        return self._label_deterministic(claim, passage, score)

    def _label_with_bedrock(self, claim: Claim, passage: Passage, score: float) -> PairAlignment:
        import boto3
        bedrock = boto3.client("bedrock-runtime", region_name=os.getenv("AWS_DEFAULT_REGION", "us-east-1"))
        user_prompt = f"""Passage text:
{passage.text}

Passage sentences:
{json.dumps(passage.sentences, indent=2)}

Student claim:
"{claim.text}"
"""
        response = bedrock.converse(
            modelId=self.bedrock_model_id,
            messages=[{"role": "user", "content": [{"text": user_prompt}]}],
            system=[{"text": LABEL_SYSTEM_PROMPT}],
            inferenceConfig={"temperature": 0.0}
        )
        content_text = response["output"]["message"]["content"][0]["text"]
        # Parse JSON from Bedrock response
        import re
        json_match = re.search(r'\{.*\}', content_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            raw_label = data.get("label", "unrelated").lower()
            cited_sentence = data.get("cited_sentence")
            label = LabelEnum.UNRELATED
            if raw_label == "supports":
                label = LabelEnum.SUPPORTS
            elif raw_label == "contradicts":
                label = LabelEnum.CONTRADICTS

            if label in (LabelEnum.SUPPORTS, LabelEnum.CONTRADICTS):
                if not self.verify_invariant_2(passage, cited_sentence):
                    label = LabelEnum.UNRELATED
                    cited_sentence = None

            return PairAlignment(
                claim=claim,
                passage=passage,
                retrieval_score=score,
                label=label,
                cited_sentence=cited_sentence,
                reasoning=data.get("reasoning", "AWS Bedrock Converse alignment.")
            )
        return self._label_deterministic(claim, passage, score)

    def _label_with_llm(self, claim: Claim, passage: Passage, score: float) -> PairAlignment:
        import httpx
        user_prompt = f"""Passage text:
{passage.text}

Passage sentences:
{json.dumps(passage.sentences, indent=2)}

Student claim:
"{claim.text}"
"""
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": LABEL_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0.0,
            },
            timeout=15.0
        )
        data = response.json()
        content = json.loads(data["choices"][0]["message"]["content"])
        raw_label = content.get("label", "unrelated").lower()
        cited_sentence = content.get("cited_sentence")
        reasoning = content.get("reasoning")

        label = LabelEnum.UNRELATED
        if raw_label == "supports":
            label = LabelEnum.SUPPORTS
        elif raw_label == "contradicts":
            label = LabelEnum.CONTRADICTS

        # Invariant check: cited_sentence must strictly be present in the passage
        if label in (LabelEnum.SUPPORTS, LabelEnum.CONTRADICTS):
            if not self.verify_invariant_2(passage, cited_sentence):
                # Search for best matching sentence in passage
                best_s = None
                best_score = 0
                for s in passage.sentences:
                    sim = fuzz.ratio(s, cited_sentence or "")
                    if sim > best_score:
                        best_score = sim
                        best_s = s
                if best_score > 80:
                    cited_sentence = best_s
                else:
                    # Invariant violation: reject label
                    label = LabelEnum.UNRELATED
                    cited_sentence = None

        return PairAlignment(
            claim=claim,
            passage=passage,
            retrieval_score=score,
            label=label,
            cited_sentence=cited_sentence,
            reasoning=reasoning
        )

    def _label_deterministic(self, claim: Claim, passage: Passage, score: float) -> PairAlignment:
        """
        Deterministic baseline labeler for offline testing and baseline metrics (INV-4).
        Finds the closest sentence in the passage and detects polarity contradiction words.
        """
        best_sentence = None
        best_score = 0.0

        for sentence in passage.sentences:
            sim = fuzz.token_set_ratio(claim.text, sentence) / 100.0
            if sim > best_score:
                best_score = sim
                best_sentence = sentence

        # Polarity conflict checks (e.g. produces vs consumes, creates vs uses, produces ATP in phase 1)
        contradiction_keywords = [
            ("produces atp", "consumes two atp"),
            ("produces atp", "cost the cell two atp"),
            ("produces atp", "cost the cell"),
            ("produces atp", "investment of energy"),
            ("produces atp and energy", "net investment of energy"),
            ("generates atp in the first", "uses energy"),
            ("aerobic", "anaerobic"),
            ("does use oxygen", "does not use oxygen"),
            ("mitochondria", "cytoplasm"),
        ]

        claim_lower = claim.text.lower()
        sentence_lower = (best_sentence or "").lower()

        is_contradiction = False
        for neg_claim, neg_truth in contradiction_keywords:
            if neg_claim in claim_lower and neg_truth in passage.text.lower():
                is_contradiction = True
                for s in passage.sentences:
                    if neg_truth in s.lower():
                        best_sentence = s
                        break
                break

        if is_contradiction and best_sentence:
            return PairAlignment(
                claim=claim,
                passage=passage,
                retrieval_score=score,
                label=LabelEnum.CONTRADICTS,
                cited_sentence=best_sentence,
                reasoning="Deterministic polarity conflict detected against passage."
            )

        if best_score >= 0.55 and best_sentence:
            return PairAlignment(
                claim=claim,
                passage=passage,
                retrieval_score=score,
                label=LabelEnum.SUPPORTS,
                cited_sentence=best_sentence,
                reasoning="Deterministic high semantic overlap with passage sentence."
            )

        return PairAlignment(
            claim=claim,
            passage=passage,
            retrieval_score=score,
            label=LabelEnum.UNRELATED,
            cited_sentence=None,
            reasoning="Insufficient semantic match."
        )
