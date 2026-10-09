"""
Eleza Review Surface & Session Server (ELZ-400, ELZ-700, INV-2, INV-3)
Delivers the post-walk parallel span review, ledger insights, and wrist notifications.
"""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from eleza_align.models import (
    UnitMap,
    KeyIdea,
    Passage,
    TranscriptUtterance,
)
from eleza_align.segmenter import ClaimSegmenter
from eleza_align.retriever import HybridRetriever
from eleza_align.labeler import PairLabeler
from eleza_align.coverage import CoverageEngine
from eleza.normalizer import TermNormalizer
from eleza.ledger import MemoryLedger
from eleza.bee_service import BeeSessionService

app = FastAPI(title="Eleza Student Review Surface", version="1.0.0")

STATIC_DIR = Path("eleza/static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

DATA_DIR = Path("data")
ledger = MemoryLedger(DATA_DIR / "ledger.jsonl")
bee_service = BeeSessionService()

class ActionRequest(BaseModel):
    session_id: str
    target_idea: str
    action: str  # 'got_it' | 'said_differently'

def load_unit_map() -> UnitMap:
    with open(DATA_DIR / "openstax_bio2e_ch7.json") as f:
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
    with open(DATA_DIR / "course_map_bi107.yaml") as f:
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

@app.get("/api/bee/status")
def get_bee_status():
    return bee_service.check_connection()

@app.get("/api/ledger")
def get_ledger_data():
    insights = ledger.compute_weekly_insights("glycolysis")
    gap_prompt = ledger.generate_next_day_gap_prompt("glycolysis")
    events = ledger.load_all_events()
    return {
        "insights": insights,
        "gap_prompt": gap_prompt,
        "total_events": len(events),
        "events": events[-10:],
    }

@app.post("/api/action")
def record_action(req: ActionRequest):
    if req.action not in ["got_it", "said_differently"]:
        raise HTTPException(status_code=400, detail="Invalid action type")
    evt = ledger.record_student_action(req.session_id, req.target_idea, req.action)
    return {"status": "recorded", "event": evt}

@app.post("/api/session/evaluate-sample")
def evaluate_sample_walk():
    """Simulates/evaluates the real fixture walk session and commits to ledger."""
    with open("fixtures/labeled_session_claims.json") as f:
        fixtures = json.load(f)

    unit_map = load_unit_map()
    normalizer = TermNormalizer.from_json("data/openstax_bio2e_ch7.json")

    # Build raw utterances representing the student walk
    raw_utterances = [
        "Eleza, glycolysis.",
        "Glucose enters the cell and glycolysis takes place anaerobically in the cytoplasm.",
        "Glycolysis breaks down one six-carbon glucose into two three-carbon pyruvates.",
        "Hexokinase phosphorylates glucose into glucose-6-phosphate using up one molecule of ATP.",
        "An isomerase then converts glucose-6-phosphate into its isomer fructose-6-phosphate.",
        "Phosphofructokinase acts as a rate-limiting enzyme and adds another phosphate with a second ATP.",
        "Aldolase cleaves the sugar into dihydroxyacetone phosphate and glyceraldehyde-3-phosphate.",
        "The first phase produces ATP and energy for the cell.", # Intentional contradiction!
        "Glyceraldehyde-3-phosphate dehydrogenase oxidizes G3P while reducing NAD+ to NADH.",
        "Phosphoglycerate kinase produces ATP by substrate-level phosphorylation.",
        "Enolase causes dehydration to form high energy phosphoenolpyruvate.",
        "Pyruvate kinase catalyzes the last step yielding another ATP and pyruvate.",
        "Eleza, done."
    ]

    session_id = f"sess-walk-{int(os.times()[4] * 1000)}"
    utterances = []
    for idx, text in enumerate(raw_utterances[1:-1]): # skip boundary markers
        norm = normalizer.normalize(text)
        utterances.append(TranscriptUtterance(
            utterance_id=f"u{idx+1:02d}",
            text=norm.normalized_text,
            speaker="wearer"
        ))

    segmenter = ClaimSegmenter()
    claims = segmenter.segment_utterances(utterances)

    retriever = HybridRetriever(unit_map.passages, threshold=0.20)
    labeler = PairLabeler()

    alignments = []
    for claim in claims:
        candidates = retriever.retrieve(claim, top_k=1)
        if candidates:
            best_passage, score = candidates[0]
            align = labeler.label_pair(claim, best_passage, score=score)
            alignments.append(align)

    engine = CoverageEngine(unit_map)
    report = engine.evaluate(alignments)

    # Save to ledger
    ledger.record_session(session_id, report, duration_seconds=840)

    return {
        "session_id": session_id,
        "report": report.model_dump(),
        "summary_notification": f"Glycolysis: {report.covered_count} of {report.total_key_ideas} ideas, {report.contradicted_count} contradiction",
    }

class LiveSpeechRequest(BaseModel):
    transcript: str
    speaker: str = "wearer"

@app.post("/api/session/process-speech")
def process_live_speech(req: LiveSpeechRequest):
    """Processes real speech captured from the browser microphone."""
    if not req.transcript.strip():
        raise HTTPException(status_code=400, detail="Empty transcript")

    unit_map = load_unit_map()
    normalizer = TermNormalizer.from_json("data/openstax_bio2e_ch7.json")
    session_id = f"sess-mic-{int(os.times()[4] * 1000)}"

    # Normalize spoken input
    norm = normalizer.normalize(req.transcript)
    utterance = TranscriptUtterance(
        utterance_id="u-live-01",
        text=norm.normalized_text,
        speaker=req.speaker
    )

    segmenter = ClaimSegmenter()
    claims = segmenter.segment_utterances([utterance])

    if not claims:
        # Fallback to direct claim if segmenter filtered short sentence
        claims = [from_text(session_id, norm.normalized_text)]

    retriever = HybridRetriever(unit_map.passages, threshold=0.15)
    labeler = PairLabeler()

    alignments = []
    for claim in claims:
        candidates = retriever.retrieve(claim, top_k=1)
        if candidates:
            best_passage, score = candidates[0]
            align = labeler.label_pair(claim, best_passage, score=score)
            alignments.append(align)

    engine = CoverageEngine(unit_map)
    report = engine.evaluate(alignments)
    ledger.record_session(session_id, report, duration_seconds=120)

    return {
        "session_id": session_id,
        "report": report.model_dump(),
        "summary_notification": f"Glycolysis: {report.covered_count} of {report.total_key_ideas} ideas, {report.contradicted_count} contradiction",
    }

def from_text(sess_id: str, text: str):
    from eleza_align.models import Claim
    return Claim(claim_id=f"{sess_id}-c1", utterance_id="u-live-01", text=text, speaker="wearer")

@app.get("/api/session/latest")
def get_latest_session():
    events = ledger.load_all_events()
    session_events = [e for e in events if e["event_type"] == "session_completed"]
    if not session_events:
        # Run sample evaluation to initialize ledger
        return evaluate_sample_walk()

    latest = session_events[-1]["payload"]
    return {
        "session_id": latest["session_id"],
        "report": latest,
        "summary_notification": f"Glycolysis: {latest['covered_count']} of {latest['total_ideas']} ideas, {latest['contradicted_count']} contradiction",
    }

@app.get("/", response_class=HTMLResponse)
def index_page():
    with open(STATIC_DIR / "index.html", encoding="utf-8") as f:
        return f.read()
