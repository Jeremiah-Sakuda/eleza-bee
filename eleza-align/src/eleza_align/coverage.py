"""
Coverage Aggregation Engine (ELZ-304, ELZ-401, INV-3)
Computes Covered, Skipped, and Contradicted unit ideas without editorializing or scoring.
"""

from __future__ import annotations
from eleza_align.models import (
    UnitMap,
    PairAlignment,
    LabelEnum,
    CoverageReport,
    ContradictionItem,
)

class CoverageEngine:
    def __init__(self, unit_map: UnitMap):
        self.unit_map = unit_map

    def evaluate(self, alignments: list[PairAlignment]) -> CoverageReport:
        # Index passage support & contradiction
        supported_passages = set()
        contradicted_passages = set()
        contradiction_items = []

        for align in alignments:
            p_id = align.passage.passage_id
            if align.label == LabelEnum.SUPPORTS:
                supported_passages.add(p_id)
            elif align.label == LabelEnum.CONTRADICTS:
                contradicted_passages.add(p_id)
                contradiction_items.append(ContradictionItem(
                    claim_id=align.claim.claim_id,
                    utterance_id=align.claim.utterance_id,
                    student_said=align.claim.text,
                    passage_id=p_id,
                    text_says=align.cited_sentence or align.passage.text,
                    section=align.passage.section or align.passage.subsection
                ))

        covered_ideas = []
        skipped_ideas = []

        for idea in self.unit_map.key_ideas:
            if idea.passage_id in supported_passages:
                covered_ideas.append(idea.name)
            else:
                skipped_ideas.append(idea.name)

        return CoverageReport(
            unit_id=self.unit_map.id,
            unit_title=self.unit_map.title,
            total_key_ideas=len(self.unit_map.key_ideas),
            covered_count=len(covered_ideas),
            skipped_count=len(skipped_ideas),
            contradicted_count=len(contradiction_items),
            covered_ideas=covered_ideas,
            skipped_ideas=skipped_ideas,
            contradictions=contradiction_items,
            alignments=alignments,
        )

    @staticmethod
    def format_text_report(report: CoverageReport) -> str:
        """
        Fixed report format (ELZ-401, INV-3):
        Covered (count, ideas) / Skipped (ideas) / Contradicted (spans).
        No praise, no scores, no grades.
        """
        lines = []
        lines.append(f"# Eleza Session Report: {report.unit_title}")
        lines.append(f"**Coverage:** {report.covered_count} of {report.total_key_ideas} ideas covered\n")

        lines.append("## Covered Ideas")
        if report.covered_ideas:
            for idea in report.covered_ideas:
                lines.append(f"- {idea}")
        else:
            lines.append("*(None recorded in this session)*")
        lines.append("")

        lines.append("## Contradicted")
        if report.contradictions:
            for c in report.contradictions:
                lines.append(f"- **You said:** \"{c.student_said}\"")
                lines.append(f"  **The text says:** \"{c.text_says}\"")
                lines.append(f"  *(Passage: {c.passage_id})*\n")
        else:
            lines.append("*(None)*\n")

        lines.append("## Skipped Ideas")
        if report.skipped_ideas:
            for idea in report.skipped_ideas:
                lines.append(f"- {idea}")
        else:
            lines.append("*(All key ideas covered)*")

        return "\n".join(lines)
