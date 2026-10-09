"""
Claim Segmentation Engine (ELZ-301, INV-4)
Splits conversational transcripts into testable assertions at sentence boundaries.
Filters conversational disfluencies and filler words deterministically.
"""

from __future__ import annotations
import re
from eleza_align.models import TranscriptUtterance, Claim

# Common verbal disfluencies and discourse markers to strip at boundaries
DISFLUENCY_PATTERNS = [
    r'^(?:um|uh|er|ah|like|you know|so basically|okay so|and so|well|wait|yeah|alright)\s*,\s*',
    r'^(?:um|uh|er|ah|like|you know|so basically|okay so|and so|well|wait|yeah|alright)\b\s*',
    r'\b(?:um|uh|er|ah)\b',
]

class ClaimSegmenter:
    def __init__(self, min_token_length: int = 4):
        self.min_token_length = min_token_length

    def clean_text(self, text: str) -> str:
        cleaned = text.strip()
        for pat in DISFLUENCY_PATTERNS:
            cleaned = re.sub(pat, '', cleaned, flags=re.IGNORECASE)
        # Collapse multiple spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    def segment_text(self, text: str) -> list[str]:
        # Split on sentence end punctuation or pauses
        raw_splits = re.split(r'(?<=[.!?])\s+|(?<=\w)\s*;\s*', text)
        sentences = []
        for s in raw_splits:
            cleaned = self.clean_text(s)
            # Filter fragments that are too short or non-assertive
            tokens = cleaned.split()
            if len(tokens) >= self.min_token_length:
                # Ensure starts capitalized
                if cleaned:
                    cleaned = cleaned[0].upper() + cleaned[1:]
                sentences.append(cleaned)
        return sentences

    def segment_utterance(self, utterance: TranscriptUtterance) -> list[Claim]:
        segments = self.segment_text(utterance.text)
        claims = []
        for idx, text in enumerate(segments):
            claim_id = f"{utterance.utterance_id}-c{idx+1:02d}"
            claims.append(Claim(
                claim_id=claim_id,
                utterance_id=utterance.utterance_id,
                text=text,
                speaker=utterance.speaker,
                timestamp_ms=utterance.timestamp_ms,
                raw_span=utterance.text,
            ))
        return claims

    def segment_utterances(self, utterances: list[TranscriptUtterance]) -> list[Claim]:
        all_claims = []
        for u in utterances:
            # Filter non-wearer utterances per INV-1
            if u.speaker.lower() in ["wearer", "user", "self"]:
                all_claims.extend(self.segment_utterance(u))
        return all_claims
