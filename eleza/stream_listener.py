"""
Live Bee Stream Listener Daemon (ELZ-101, ELZ-102, ELZ-103)
Subscribes to live @beeai/cli stream events over subprocess stdout.
Feeds utterances into BeeSessionService and finalizes reports upon session close.
"""

from __future__ import annotations
import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

from eleza.bee_service import BeeSessionService
from eleza.ledger import MemoryLedger

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("eleza.stream_listener")

class StreamListener:
    def __init__(self, course_map: str = "data/course_map_bi107.yaml"):
        self.service = BeeSessionService(course_map_path=course_map)
        self.ledger = MemoryLedger("data/ledger.jsonl")
        self.running = False

    async def listen(self):
        """Asynchronously stream from `bee stream --json --types new-utterance`."""
        logger.info("Starting live Bee stream listener...")
        cmd = [self.service.bee_bin, "stream", "--json", "--types", "new-utterance,update-conversation"]
        
        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
        except Exception as e:
            logger.error(f"Failed to start bee stream process: {e}")
            return

        self.running = True
        logger.info("Connected to Bee wearable event stream. Listening for vocal start markers ('Eleza, glycolysis')...")

        while self.running and process.returncode is None:
            line = await process.stdout.readline()
            if not line:
                break

            raw_str = line.decode().strip()
            if not raw_str:
                continue

            try:
                event = json.loads(raw_str)
                event_type = event.get("type") or event.get("event")
                payload = event.get("data") or event

                if event_type in ["new-utterance", "utterance"]:
                    text = payload.get("text") or payload.get("transcript", "")
                    speaker = payload.get("speaker", "wearer")
                    u_id = payload.get("id") or f"u-{int(asyncio.get_event_loop().time() * 1000)}"

                    result = self.service.process_incoming_utterance(
                        utterance_id=u_id,
                        raw_text=text,
                        speaker=speaker
                    )
                    logger.info(f"Utterance received [{speaker}]: '{text}' -> {result}")

                    if result and result.get("action") == "session_closed_marker":
                        logger.info("Session closed by marker. Evaluating coverage...")
                        from eleza.agent_skill import load_unit
                        unit = load_unit()
                        report = self.service.close_and_evaluate_session(unit)
                        if report:
                            self.ledger.record_session(self.service.active_session.session_id, report)
                            logger.info(f"Report finalized: {report.covered_count} covered, {report.contradicted_count} contradictions")

            except json.JSONDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error handling stream event: {e}")

    def stop(self):
        self.running = False
