"""
eleza-align: Deterministic claim-to-passage alignment engine.
"""

from eleza_align.models import (
    TranscriptUtterance,
    Claim,
    Passage,
    KeyIdea,
    UnitMap,
    PairAlignment,
    LabelEnum,
    CoverageReport,
    ContradictionItem,
)
from eleza_align.segmenter import ClaimSegmenter
from eleza_align.retriever import HybridRetriever
from eleza_align.labeler import PairLabeler
from eleza_align.coverage import CoverageEngine

__version__ = "0.1.0"

__all__ = [
    "TranscriptUtterance",
    "Claim",
    "Passage",
    "KeyIdea",
    "UnitMap",
    "PairAlignment",
    "LabelEnum",
    "CoverageReport",
    "ContradictionItem",
    "ClaimSegmenter",
    "HybridRetriever",
    "PairLabeler",
    "CoverageEngine",
]
