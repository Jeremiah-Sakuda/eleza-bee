"""
Eleza Session Agent Skill (ELZ-503, PRD Section 5)
Packages the complete loop for coding agents, power users, and hackathon judges:
1. Pulls latest wearable session data from Bee (via CLI, sync, or MCP).
2. Normalizes biochemical terms against the active unit course map.
3. Runs eleza-align to produce claim-passage alignments and coverage.
4. Appends to the longitudinal ledger and outputs the structured report.
"""

from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from eleza_align.models import (
    TranscriptUtterance,
    UnitMap,
    KeyIdea,
    Passage,
)
from eleza_align.segmenter import ClaimSegmenter
from eleza_align.retriever import HybridRetriever
from eleza_align.labeler import PairLabeler
from eleza_align.coverage import CoverageEngine
from eleza.normalizer import TermNormalizer
from eleza.ledger import MemoryLedger
from eleza.bee_service import BeeSessionService

def load_unit(course_map_path: str = "data/course_map_bi107.yaml", openstax_path: str = "data/openstax_bio2e_ch7.json") -> UnitMap:
    with open(openstax_path, encoding="utf-8") as f:
        data = json.load(f)
    passages = [
        Passage(
            passage_id=p["passage_id"],
            text=p["text"],
            sentences=p["sentences"],
            section=p.get("section"),
            subsection=p.get("subsection")
        )
        for p in data["passages"]
    ]
    import yaml
    with open(course_map_path, encoding="utf-8") as f:
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

def run_skill(unit_id: str = "glycolysis", mock_if_offline: bool = True) -> dict:
    """Execute the eleza-session Agent Skill pipeline."""
    unit_map = load_unit()
    normalizer = TermNormalizer.from_json("data/openstax_bio2e_ch7.json")
    bee = BeeSessionService()
    ledger = MemoryLedger("data/ledger.jsonl")

    conn = bee.check_connection()
    raw_utterances = []

    if conn["installed"] and conn["authenticated"]:
        # Try fetching real conversation utterances from Bee
        daily = bee.fetch_daily_context()
        conversations = daily.get("conversations", [])
        for c in conversations:
            for u in c.get("utterances", []):
                raw_utterances.append({
                    "id": u.get("id", "u-bee"),
                    "text": u.get("text", ""),
                    "speaker": u.get("speaker", "wearer")
                })

    if not raw_utterances and mock_if_offline:
        # Ground truth fixture walk playback
        with open("fixtures/labeled_session_claims.json", encoding="utf-8") as f:
            fixtures = json.load(f)
        for idx, item in enumerate(fixtures):
            raw_utterances.append({
                "id": f"u{idx+1:02d}",
                "text": item["text"],
                "speaker": "wearer"
            })

    # Normalize terms
    utterances = []
    total_replacements = 0
    for u in raw_utterances:
        norm = normalizer.normalize(u["text"])
        total_replacements += norm.replacement_count
        utterances.append(TranscriptUtterance(
            utterance_id=u["id"],
            text=norm.normalized_text,
            speaker=u.get("speaker", "wearer")
        ))

    # Segment
    segmenter = ClaimSegmenter()
    claims = segmenter.segment_utterances(utterances)

    # Retrieve & Label
    retriever = HybridRetriever(unit_map.passages, threshold=0.20)
    labeler = PairLabeler()

    alignments = []
    for claim in claims:
        candidates = retriever.retrieve(claim, top_k=1)
        if candidates:
            best_passage, score = candidates[0]
            align = labeler.label_pair(claim, best_passage, score=score)
            alignments.append(align)

    # Coverage
    engine = CoverageEngine(unit_map)
    report = engine.evaluate(alignments)

    # Record to ledger
    session_id = f"skill-sess-{len(ledger.load_all_events()) + 1}"
    ledger.record_session(session_id, report, duration_seconds=900)

    # Generate wrist prompt
    gap_prompt = ledger.generate_next_day_gap_prompt(unit_id)
    text_report = engine.format_text_report(report)

    return {
        "session_id": session_id,
        "unit_title": unit_map.title,
        "covered_count": report.covered_count,
        "total_key_ideas": report.total_key_ideas,
        "contradicted_count": report.contradicted_count,
        "normalizations_applied": total_replacements,
        "gap_prompt": gap_prompt,
        "text_report": text_report,
        "report": report.model_dump(),
    }

def main():
    parser = argparse.ArgumentParser(description="Run eleza-session Agent Skill")
    parser.add_argument("--unit", default="glycolysis", help="Unit ID to evaluate")
    parser.add_argument("--json", action="store_true", help="Output JSON result")
    args = parser.parse_args()

    result = run_skill(unit_id=args.unit)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["text_report"])
        if result["gap_prompt"]:
            print("\n--- NEXT-DAY WRIST GAP PROMPT ---")
            print(result["gap_prompt"]["wrist_prompt"])

if __name__ == "__main__":
    main()
