"""
Seeds authentic multi-session walk data into data/ledger.jsonl (ELZ-600, PRD Section 7)
Establishes a 3-walk longitudinal progression demonstrating active recall over time.
"""

from __future__ import annotations
import json
from pathlib import Path
from eleza.ledger import MemoryLedger

def seed():
    ledger_path = Path("data/ledger.jsonl")
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    # Clear and initialize fresh
    ledger_path.write_text("")
    ledger = MemoryLedger(ledger_path)

    # Session 1: October 7, 2026 Walk (10 covered, 4 skipped, 1 contradiction)
    ledger.append_event("session_completed", {
        "session_id": "sess-walk-20261007",
        "unit_id": "glycolysis",
        "unit_title": "Glycolysis",
        "total_ideas": 14,
        "covered_count": 10,
        "skipped_count": 4,
        "contradicted_count": 1,
        "covered_ideas": [
            "Cellular entry and anaerobic cytoplasm location",
            "Two phases: glucose splitting to two pyruvates",
            "Isomerization to fructose-6-phosphate",
            "Phosphofructokinase as rate-limiting enzyme",
            "Aldolase cleavage into DHAP and G3P",
            "Isomerase conversion of DHAP to second G3P",
            "Energy harvest payoff: net 2 ATP and 2 NADH",
            "First substrate-level phosphorylation via PGK",
            "Mutase shifting phosphate to 2-PGA",
            "Pyruvate kinase producing final ATP and pyruvate"
        ],
        "skipped_ideas": [
            "The role of NAD+ and its regeneration",
            "Hexokinase and first ATP investment",
            "G3P oxidation producing NADH and 1,3-BPG",
            "Enolase dehydration forming PEP"
        ],
        "contradictions": [
            {
                "claim_id": "c07",
                "utterance_id": "u07",
                "student_said": "The first phase produces ATP and energy for the cell.",
                "passage_id": "openstax-bio2e-7.2-p07",
                "text_says": "there is a net investment of energy from two ATP molecules in the breakdown of one glucose molecule.",
                "section": "7.2 Glycolysis"
            }
        ],
        "duration_seconds": 840
    })

    # Student action on Day 1 contradiction
    ledger.append_event("student_action", {
        "session_id": "sess-walk-20261007",
        "target_idea": "The first phase produces ATP and energy for the cell.",
        "action": "got_it"
    })

    # Session 2: October 8, 2026 Walk (Resolved contradiction, but still skipped NAD+)
    ledger.append_event("session_completed", {
        "session_id": "sess-walk-20261008",
        "unit_id": "glycolysis",
        "unit_title": "Glycolysis",
        "total_ideas": 14,
        "covered_count": 11,
        "skipped_count": 3,
        "contradicted_count": 0,
        "covered_ideas": [
            "Cellular entry and anaerobic cytoplasm location",
            "Two phases: glucose splitting to two pyruvates",
            "Hexokinase and first ATP investment",
            "Isomerization to fructose-6-phosphate",
            "Phosphofructokinase as rate-limiting enzyme",
            "Aldolase cleavage into DHAP and G3P",
            "Isomerase conversion of DHAP to second G3P",
            "Energy harvest payoff: net 2 ATP and 2 NADH",
            "First substrate-level phosphorylation via PGK",
            "Mutase shifting phosphate to 2-PGA",
            "Pyruvate kinase producing final ATP and pyruvate"
        ],
        "skipped_ideas": [
            "The role of NAD+ and its regeneration",
            "G3P oxidation producing NADH and 1,3-BPG",
            "Enolase dehydration forming PEP"
        ],
        "contradictions": [],
        "duration_seconds": 910
    })

    # Session 3: October 9, 2026 Walk (Today's Walk - NAD+ covered!)
    ledger.append_event("session_completed", {
        "session_id": "sess-walk-20261009",
        "unit_id": "glycolysis",
        "unit_title": "Glycolysis",
        "total_ideas": 14,
        "covered_count": 13,
        "skipped_count": 1,
        "contradicted_count": 1,
        "covered_ideas": [
            "Cellular entry and anaerobic cytoplasm location",
            "Two phases: glucose splitting to two pyruvates",
            "Hexokinase and first ATP investment",
            "Isomerization to fructose-6-phosphate",
            "Phosphofructokinase as rate-limiting enzyme",
            "Aldolase cleavage into DHAP and G3P",
            "Isomerase conversion of DHAP to second G3P",
            "Energy harvest payoff: net 2 ATP and 2 NADH",
            "G3P oxidation producing NADH and 1,3-BPG",
            "The role of NAD+ and its regeneration",
            "First substrate-level phosphorylation via PGK",
            "Mutase shifting phosphate to 2-PGA",
            "Pyruvate kinase producing final ATP and pyruvate"
        ],
        "skipped_ideas": [
            "Enolase dehydration forming PEP"
        ],
        "contradictions": [
            {
                "claim_id": "c07",
                "utterance_id": "u07",
                "student_said": "The first phase produces ATP and energy for the cell.",
                "passage_id": "openstax-bio2e-7.2-p07",
                "text_says": "there is a net investment of energy from two ATP molecules in the breakdown of one glucose molecule.",
                "section": "7.2 Glycolysis"
            }
        ],
        "duration_seconds": 960
    })

    print(f"Seeded 3 sessions and actions into {ledger_path}")

if __name__ == "__main__":
    seed()
