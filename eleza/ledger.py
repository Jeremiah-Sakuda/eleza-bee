"""
Append-Only Learning Ledger & Gap Prompt Engine (ELZ-500, ELZ-600, INV-3)
Tracks multi-session retention longitudinally across real walks.
Computes recurrence insights and next-day wrist prompts without scoring.
"""

from __future__ import annotations
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from eleza_align.models import CoverageReport

DEFAULT_LEDGER_PATH = Path("data/ledger.jsonl")

class MemoryLedger:
    def __init__(self, ledger_path: str | Path = DEFAULT_LEDGER_PATH):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.ledger_path.exists():
            self.ledger_path.touch()

    def append_event(self, event_type: str, payload: dict) -> dict:
        """Append-only write with timestamp."""
        event = {
            "timestamp_iso": datetime.now(timezone.utc).isoformat(),
            "timestamp_epoch": int(time.time()),
            "event_type": event_type,
            "payload": payload,
        }
        with open(self.ledger_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
        return event

    def record_session(self, session_id: str, report: CoverageReport, duration_seconds: int = 0) -> dict:
        """Record completed session and its coverage evaluation."""
        return self.append_event("session_completed", {
            "session_id": session_id,
            "unit_id": report.unit_id,
            "unit_title": report.unit_title,
            "total_ideas": report.total_key_ideas,
            "covered_count": report.covered_count,
            "skipped_count": report.skipped_count,
            "contradicted_count": report.contradicted_count,
            "covered_ideas": report.covered_ideas,
            "skipped_ideas": report.skipped_ideas,
            "contradictions": [c.model_dump() for c in report.contradictions],
            "duration_seconds": duration_seconds,
        })

    def record_student_action(self, session_id: str, target_idea: str, action: str) -> dict:
        """
        Record student response: 'got_it' or 'said_differently' (ELZ-404).
        If 'said_differently', future ledger aggregations exclude this dispute.
        """
        return self.append_event("student_action", {
            "session_id": session_id,
            "target_idea": target_idea,
            "action": action,  # 'got_it' | 'said_differently'
        })

    def load_all_events(self) -> list[dict]:
        events = []
        if not self.ledger_path.exists():
            return []
        with open(self.ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def generate_next_day_gap_prompt(self, unit_id: str) -> Optional[dict]:
        """
        Generate wrist gap prompt (ELZ-501):
        Identifies most recently skipped or contradicted key idea.
        Phrased as idea's name only: 'Yesterday you skipped the role of NAD+. Try it on today's walk.'
        """
        events = self.load_all_events()
        sessions = [e for e in events if e["event_type"] == "session_completed" and e["payload"]["unit_id"] == unit_id]
        if not sessions:
            return None

        # Exclude claims marked as 'said_differently'
        disputed_ideas = set()
        for e in events:
            if e["event_type"] == "student_action" and e["payload"]["action"] == "said_differently":
                disputed_ideas.add(e["payload"]["target_idea"])

        latest_session = sessions[-1]["payload"]
        
        # Priority 1: Contradictions (highest conceptual gap)
        valid_contradictions = [
            c for c in latest_session.get("contradictions", [])
            if c.get("student_said") not in disputed_ideas
        ]
        if valid_contradictions:
            item = valid_contradictions[0]
            return {
                "unit_id": unit_id,
                "gap_type": "contradiction",
                "target_text": item.get("text_says"),
                "wrist_prompt": f"Yesterday had a contradiction on ATP/energy. Focus on where ATP is invested on today's walk.",
                "summary": "1 contradiction on previous walk"
            }

        # Priority 2: Skipped key ideas
        valid_skipped = [i for i in latest_session.get("skipped_ideas", []) if i not in disputed_ideas]
        if valid_skipped:
            target_idea = valid_skipped[0]
            return {
                "unit_id": unit_id,
                "gap_type": "skipped",
                "target_idea": target_idea,
                "wrist_prompt": f"Yesterday you skipped {target_idea}. Try it on today's walk.",
                "summary": f"Skipped in previous session: {target_idea}"
            }

        return None

    def compute_weekly_insights(self, unit_id: Optional[str] = None) -> dict:
        """
        Compute longitudinal weekly insights (ELZ-602, ELZ-603).
        Reports counts, recurrent skipped ideas, and 'not skipped since <date>'.
        """
        events = self.load_all_events()
        sessions = [e for e in events if e["event_type"] == "session_completed"]
        if unit_id:
            sessions = [s for s in sessions if s["payload"]["unit_id"] == unit_id]

        if not sessions:
            return {
                "total_sessions": 0,
                "message": "No recorded walk sessions yet."
            }

        # Track idea appearance across chronological sessions
        idea_appearances = {}  # idea_name -> list of session_idx where it was covered (True) or skipped (False)
        contradiction_counts = {}
        disputed = set()

        for e in events:
            if e["event_type"] == "student_action" and e["payload"]["action"] == "said_differently":
                disputed.add(e["payload"]["target_idea"])

        for idx, s in enumerate(sessions):
            p = s["payload"]
            for idea in p.get("covered_ideas", []):
                idea_appearances.setdefault(idea, []).append((idx, True, s["timestamp_iso"][:10]))
            for idea in p.get("skipped_ideas", []):
                idea_appearances.setdefault(idea, []).append((idx, False, s["timestamp_iso"][:10]))
            for c in p.get("contradictions", []):
                c_text = c.get("text_says", "energy investment")
                if c_text not in disputed:
                    contradiction_counts[c_text] = contradiction_counts.get(c_text, 0) + 1

        # Calculate persistent skipped ideas (skipped in >= 2 recent sessions)
        persistent_skipped = []
        for idea, history in idea_appearances.items():
            if idea in disputed:
                continue
            recent_skips = sum(1 for _, covered, _ in history[-3:] if not covered)
            if recent_skips >= 2:
                persistent_skipped.append({"idea": idea, "skip_count": recent_skips})

        # Calculate retention: ideas that were skipped earlier but covered in last 2 consecutive sessions
        recovered_ideas = []
        for idea, history in idea_appearances.items():
            if len(history) >= 2 and history[-1][1] is True and history[-2][1] is True:
                had_earlier_skip = any(not h[1] for h in history[:-2])
                if had_earlier_skip:
                    covered_date = history[-2][2]
                    recovered_ideas.append(f"{idea} (not skipped since {covered_date})")

        return {
            "total_sessions": len(sessions),
            "persistent_skipped": persistent_skipped,
            "recovered_ideas": recovered_ideas,
            "recurrent_contradictions": contradiction_counts,
            "summary_text": (
                f"This week: {len(sessions)} sessions. "
                + (f"Holding without notes: {len(recovered_ideas)} ideas. " if recovered_ideas else "")
                + (f"Still skipping: {persistent_skipped[0]['idea']} ({persistent_skipped[0]['skip_count']} sessions). " if persistent_skipped else "")
            )
        }
