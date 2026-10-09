"""
Data models for eleza-align (ELZ-300, INV-2).
Domain-agnostic abstractions for utterances, claims, passages, labels, and coverage.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

class LabelEnum(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    UNRELATED = "unrelated"

class TranscriptUtterance(BaseModel):
    utterance_id: str
    text: str
    speaker: str = "wearer"
    timestamp_ms: Optional[int] = None

class Claim(BaseModel):
    claim_id: str
    utterance_id: str
    text: str
    speaker: str = "wearer"
    timestamp_ms: Optional[int] = None
    raw_span: Optional[str] = None

class Passage(BaseModel):
    passage_id: str
    text: str
    sentences: list[str] = Field(default_factory=list)
    section: Optional[str] = None
    subsection: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

class KeyIdea(BaseModel):
    id: str
    name: str
    passage_id: str
    description: Optional[str] = None

class UnitMap(BaseModel):
    id: str
    title: str
    passages: list[Passage]
    key_ideas: list[KeyIdea]

class PairAlignment(BaseModel):
    claim: Claim
    passage: Passage
    retrieval_score: float
    label: LabelEnum
    cited_sentence: Optional[str] = None
    reasoning: Optional[str] = None

class ContradictionItem(BaseModel):
    claim_id: str
    utterance_id: str
    student_said: str
    passage_id: str
    text_says: str
    section: Optional[str] = None

class CoverageReport(BaseModel):
    unit_id: str
    unit_title: str
    total_key_ideas: int
    covered_count: int
    skipped_count: int
    contradicted_count: int
    covered_ideas: list[str]
    skipped_ideas: list[str]
    contradictions: list[ContradictionItem]
    alignments: list[PairAlignment] = Field(default_factory=list)
