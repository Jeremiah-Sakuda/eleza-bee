"""
Bee Wearable Runtime Integration Service (ELZ-101, ELZ-102, ELZ-103, ELZ-104)
Directly interfaces with the Bee CLI (@beeai/cli) stream, sync, and facts interfaces.
Maintains session boundary state machines, wearer isolation, and normalization.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncGenerator, Callable, Optional

from eleza_align.models import TranscriptUtterance, CoverageReport, UnitMap
from eleza_align.segmenter import ClaimSegmenter
from eleza_align.retriever import HybridRetriever
from eleza_align.labeler import PairLabeler
from eleza_align.coverage import CoverageEngine
from eleza.normalizer import TermNormalizer

logger = logging.getLogger("eleza.bee_service")

@dataclass
class SessionState:
    session_id: str
    unit_id: str
    start_time_ms: int
    is_active: bool = True
    utterances: list[TranscriptUtterance] = field(default_factory=list)
    last_utterance_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    normalizations_count: int = 0

class BeeSessionService:
    def __init__(
        self,
        course_map_path: str | Path = "data/course_map_bi107.yaml",
        openstax_data_path: str | Path = "data/openstax_bio2e_ch7.json",
        bee_bin_path: Optional[str] = None,
        silence_timeout_sec: int = 240, # 4 minutes silence per ELZ-103
    ):
        self.bee_bin = bee_bin_path or shutil.which("bee") or "/opt/homebrew/bin/bee"
        self.course_map_path = Path(course_map_path)
        self.openstax_data_path = Path(openstax_data_path)
        self.silence_timeout_sec = silence_timeout_sec
        self.normalizer = TermNormalizer.from_json(self.openstax_data_path)
        self.active_session: Optional[SessionState] = None

    def check_connection(self) -> dict:
        """Check Bee CLI ping and status."""
        try:
            res = subprocess.run([self.bee_bin, "ping"], capture_output=True, text=True, check=True)
            status_res = subprocess.run([self.bee_bin, "status"], capture_output=True, text=True)
            return {
                "installed": True,
                "ping": res.stdout.strip(),
                "status": status_res.stdout.strip(),
                "authenticated": "not logged in" not in status_res.stdout.lower()
            }
        except Exception as e:
            return {"installed": False, "error": str(e), "authenticated": False}

    def fetch_daily_context(self) -> dict:
        """Fetch Bee daily summary or facts via CLI (ELZ-502)."""
        try:
            res = subprocess.run(
                [self.bee_bin, "today", "--context", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.returncode == 0:
                return json.loads(res.stdout)
        except Exception:
            pass
        return {}

    def fetch_recent_facts(self) -> list[dict]:
        """Fetch user facts from Bee memory (ELZ-502)."""
        try:
            res = subprocess.run(
                [self.bee_bin, "facts", "--json"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.returncode == 0:
                return json.loads(res.stdout)
        except Exception:
            pass
        return []

    def is_start_marker(self, text: str) -> Optional[str]:
        """Check for vocal start marker: 'Eleza, <unit_name>' (ELZ-103)."""
        match = re.search(r'\beleza\b[,\s]+(?:start|begin|unit\s+)?([a-zA-Z0-9\-_]+)', text, re.IGNORECASE)
        if match:
            unit_candidate = match.group(1).lower()
            if "glycolysis" in unit_candidate:
                return "glycolysis"
            return unit_candidate
        return None

    def is_stop_marker(self, text: str) -> bool:
        """Check for vocal stop marker: 'Eleza, done' or 'Eleza, stop' (ELZ-103)."""
        return bool(re.search(r'\beleza\b[,\s]+(?:done|stop|finish|end)', text, re.IGNORECASE))

    def process_incoming_utterance(
        self,
        utterance_id: str,
        raw_text: str,
        speaker: str = "wearer",
        timestamp_ms: Optional[int] = None
    ) -> Optional[dict]:
        """
        Process a single spoken utterance from Bee stream or sync.
        Handles session start, normalization, buffering, and session stop.
        """
        now_ms = timestamp_ms or int(time.time() * 1000)

        # Discard non-wearer speakers per INV-1 (passersby, friends)
        # Note: on solo walks, 'unknown' speaker is treated as wearer per ELZ-104
        if speaker.lower() not in ["wearer", "user", "self", "unknown"]:
            return {"action": "discarded_non_wearer", "speaker": speaker}

        # Check for start marker if no session is currently active
        start_unit = self.is_start_marker(raw_text)
        if start_unit and (not self.active_session or not self.active_session.is_active):
            session_id = f"sess-{int(time.time())}"
            self.active_session = SessionState(
                session_id=session_id,
                unit_id=start_unit,
                start_time_ms=now_ms,
                last_utterance_ms=now_ms
            )
            logger.info(f"Opened session {session_id} for unit {start_unit}")
            return {
                "action": "session_started",
                "session_id": session_id,
                "unit_id": start_unit
            }

        # If no active session, ignore casual speech
        if not self.active_session or not self.active_session.is_active:
            return {"action": "no_active_session"}

        # Check silence timeout
        silence_sec = (now_ms - self.active_session.last_utterance_ms) / 1000.0
        if silence_sec > self.silence_timeout_sec:
            logger.info("Session closed due to silence timeout")
            self.active_session.is_active = False
            return {"action": "session_closed_timeout"}

        # Check for explicit stop marker
        if self.is_stop_marker(raw_text):
            logger.info("Session closed via vocal stop marker")
            self.active_session.is_active = False
            return {"action": "session_closed_marker", "session_id": self.active_session.session_id}

        # Apply term normalization (ELZ-105)
        norm_result = self.normalizer.normalize(raw_text)
        self.active_session.normalizations_count += norm_result.replacement_count
        self.active_session.last_utterance_ms = now_ms

        utterance = TranscriptUtterance(
            utterance_id=utterance_id,
            text=norm_result.normalized_text,
            speaker="wearer",
            timestamp_ms=now_ms
        )
        self.active_session.utterances.append(utterance)

        return {
            "action": "utterance_buffered",
            "session_id": self.active_session.session_id,
            "normalized_text": norm_result.normalized_text,
            "replacements": norm_result.replacements
        }

    def close_and_evaluate_session(
        self,
        unit_map: UnitMap,
        llm_api_key: Optional[str] = None
    ) -> Optional[CoverageReport]:
        """
        Closes current active session and runs eleza-align coverage engine.
        Returns the finalized CoverageReport.
        """
        if not self.active_session or not self.active_session.utterances:
            return None

        self.active_session.is_active = False

        # 1. Segment claims
        segmenter = ClaimSegmenter()
        claims = segmenter.segment_utterances(self.active_session.utterances)

        # 2. Hybrid retrieval
        retriever = HybridRetriever(unit_map.passages, threshold=0.20)
        labeler = PairLabeler(api_key=llm_api_key)

        alignments = []
        for claim in claims:
            candidates = retriever.retrieve(claim, top_k=2)
            if candidates:
                best_passage, score = candidates[0]
                align = labeler.label_pair(claim, best_passage, score=score)
                alignments.append(align)

        # 3. Compute coverage
        coverage_engine = CoverageEngine(unit_map)
        report = coverage_engine.evaluate(alignments)
        return report
