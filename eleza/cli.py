"""
Eleza Top-Level Command-Line Interface (ELZ-101, ELZ-102, ELZ-503)
Provides CLI entry points for live streaming, sync processing, review server, and evaluation.
"""

from __future__ import annotations
import argparse
import asyncio
import sys
import uvicorn

def main():
    parser = argparse.ArgumentParser(prog="eleza", description="Eleza Wearable AI Platform")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Command: server
    server_parser = subparsers.add_parser("server", help="Start the student review web server")
    server_parser.add_argument("--port", type=int, default=8000, help="Port to listen on")
    server_parser.add_argument("--host", default="0.0.0.0", help="Host interface")

    # Command: stream
    stream_parser = subparsers.add_parser("stream", help="Start the live Bee wearable event stream listener")

    # Command: eval
    eval_parser = subparsers.add_parser("eval", help="Run the eleza-session Agent Skill evaluation")
    eval_parser.add_argument("--unit", default="glycolysis", help="Unit to evaluate")
    eval_parser.add_argument("--json", action="store_true", help="Output JSON")

    # Command: sync
    sync_parser = subparsers.add_parser("sync", help="Sync conversations from Bee device and process")

    args = parser.parse_args()

    if args.command == "server":
        uvicorn.run("eleza.server:app", host=args.host, port=args.port, reload=True)
    elif args.command == "stream":
        from eleza.stream_listener import StreamListener
        listener = StreamListener()
        asyncio.run(listener.listen())
    elif args.command == "eval":
        from eleza.agent_skill import run_skill
        res = run_skill(unit_id=args.unit)
        if args.json:
            import json
            print(json.dumps(res, indent=2))
        else:
            print(res["text_report"])
    elif args.command == "sync":
        from eleza.bee_service import BeeSessionService
        bee = BeeSessionService()
        status = bee.check_connection()
        print(f"Bee Status: {status}")
        from eleza.agent_skill import run_skill
        res = run_skill()
        print(f"Processed sync session. Coverage: {res['covered_count']}/{res['total_key_ideas']}")
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
