"""
Comprehensive Pipeline Test Suite for eleza-align (ELZ-305, ELZ-306, INV-2)
Tests Segmentation, Hybrid Retrieval, Invariant Verification, and Coverage.
"""

import json
from pathlib import Path
import pytest
import yaml

from eleza_align.models import (
    TranscriptUtterance,
    Passage,
    KeyIdea,
    UnitMap,
    LabelEnum,
)
from eleza_align.segmenter import ClaimSegmenter
from eleza_align.retriever import HybridRetriever
from eleza_align.labeler import PairLabeler
from eleza_align.coverage import CoverageEngine

DATA_JSON_PATH = Path("data/openstax_bio2e_ch7.json")
COURSE_MAP_PATH = Path("data/course_map_bi107.yaml")
FIXTURES_PATH = Path("fixtures/labeled_session_claims.json")

@pytest.fixture
def passages():
    with open(DATA_JSON_PATH) as f:
        data = json.load(f)
    return [
        Passage(
            passage_id=p["passage_id"],
            text=p["text"],
            sentences=p["sentences"],
            section=p.get("section"),
            subsection=p.get("subsection")
        )
        for p in data["passages"]
    ]

@pytest.fixture
def unit_map(passages):
    with open(COURSE_MAP_PATH) as f:
        cmap = yaml.safe_load(f)
    unit_data = cmap["units"][0]
    key_ideas = [
        KeyIdea(
            id=k["id"],
            name=k["name"],
            passage_id=k["passage_id"],
            description=k.get("description")
        )
        for k in unit_data["key_ideas"]
    ]
    return UnitMap(
        id=unit_data["id"],
        title=unit_data["title"],
        passages=passages,
        key_ideas=key_ideas
    )

@pytest.fixture
def fixture_claims():
    with open(FIXTURES_PATH) as f:
        return json.load(f)

def test_claim_segmentation_disfluency_stripping():
    segmenter = ClaimSegmenter()
    utterances = [
        TranscriptUtterance(
            utterance_id="u01",
            text="Um, like so basically hexokinase puts a phosphate on glucose. And so then isomerase changes it to fructose 6-phosphate.",
            speaker="wearer"
        ),
        TranscriptUtterance(
            utterance_id="u02",
            text="Hey man, what's up?",
            speaker="passerby"  # Non-wearer should be filtered by INV-1
        )
    ]
    claims = segmenter.segment_utterances(utterances)
    assert len(claims) == 2  # Only wearer's 2 assertions
    assert not claims[0].text.lower().startswith("um")
    assert not claims[0].text.lower().startswith("like")
    assert "hexokinase" in claims[0].text.lower()
    assert "isomerase" in claims[1].text.lower()

def test_retrieval_hit_rate_at_k(passages, fixture_claims):
    retriever = HybridRetriever(passages, threshold=0.20)
    hits = 0
    testable_claims = [c for c in fixture_claims if c["expected_passage_id"] is not None]

    for item in testable_claims:
        from eleza_align.models import Claim
        claim = Claim(claim_id=item["claim_id"], utterance_id=item["utterance_id"], text=item["text"])
        candidates = retriever.retrieve(claim, top_k=3)
        retrieved_ids = [p.passage_id for p, score in candidates]
        if item["expected_passage_id"] in retrieved_ids:
            hits += 1

    hit_rate = hits / len(testable_claims)
    print(f"\nRetrieval Hit Rate @ k=3: {hit_rate:.1%} ({hits}/{len(testable_claims)})")
    assert hit_rate >= 0.85  # At least 85% hit rate on benchmark

def test_invariant_2_strict_verification(passages):
    labeler = PairLabeler()
    p = passages[0]
    # An exact sentence from p
    valid_sentence = p.sentences[0]
    assert labeler.verify_invariant_2(p, valid_sentence) is True

    # A fabricated sentence not in p
    invalid_sentence = "This sentence was hallucinated by an AI model and is not in the textbook."
    assert labeler.verify_invariant_2(p, invalid_sentence) is False

def test_pair_labeling_and_contradiction_detection(passages, fixture_claims):
    labeler = PairLabeler()
    passage_by_id = {p.passage_id: p for p in passages}

    contradiction_fixture = next(c for c in fixture_claims if c["expected_label"] == "contradicts")
    from eleza_align.models import Claim
    claim = Claim(
        claim_id=contradiction_fixture["claim_id"],
        utterance_id=contradiction_fixture["utterance_id"],
        text=contradiction_fixture["text"]
    )
    target_passage = passage_by_id[contradiction_fixture["expected_passage_id"]]
    alignment = labeler.label_pair(claim, target_passage, score=0.85)
    assert alignment.label == LabelEnum.CONTRADICTS
    assert alignment.cited_sentence is not None
    assert labeler.verify_invariant_2(target_passage, alignment.cited_sentence)

def test_end_to_end_coverage_report(unit_map, fixture_claims):
    passages = unit_map.passages
    passage_by_id = {p.passage_id: p for p in passages}
    retriever = HybridRetriever(passages, threshold=0.20)
    labeler = PairLabeler()

    alignments = []
    from eleza_align.models import Claim
    for item in fixture_claims:
        claim = Claim(claim_id=item["claim_id"], utterance_id=item["utterance_id"], text=item["text"])
        candidates = retriever.retrieve(claim, top_k=1)
        if candidates:
            best_passage, score = candidates[0]
            align = labeler.label_pair(claim, best_passage, score=score)
            alignments.append(align)

    engine = CoverageEngine(unit_map)
    report = engine.evaluate(alignments)

    assert report.total_key_ideas == 14
    assert report.covered_count > 0
    assert report.contradicted_count >= 1
    # Check that skipped count equals total - covered
    assert report.skipped_count == report.total_key_ideas - report.covered_count

    report_text = engine.format_text_report(report)
    assert "Eleza Session Report: Glycolysis" in report_text
    assert "## Covered Ideas" in report_text
    assert "## Contradicted" in report_text
    assert "## Skipped Ideas" in report_text
