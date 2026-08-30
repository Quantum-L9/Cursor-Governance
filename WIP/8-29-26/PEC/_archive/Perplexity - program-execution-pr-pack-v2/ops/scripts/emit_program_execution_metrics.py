#!/usr/bin/env python3
"""ops/scripts/emit_program_execution_metrics.py"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
try: import jsonschema
except ImportError: jsonschema = None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--reports-dir", required=True); p.add_argument("--event-type", required=True, dest="event_type")
    p.add_argument("--node-id", required=True, dest="node_id"); p.add_argument("--agent-id", dest="agent_id")
    p.add_argument("--detail-json", default="{}", dest="detail_json")
    p.add_argument("--schema", default="ops/schemas/program_execution_event.schema.json")
    args = p.parse_args()
    event = {"event_type": args.event_type, "node_id": args.node_id, "timestamp": time.time(),
             "agent_id": args.agent_id, "detail": json.loads(args.detail_json)}
    if jsonschema is not None:
        jsonschema.validate(event, json.loads(Path(args.schema).read_text()))
    out_dir = Path(args.reports_dir) / "telemetry"; out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "program_execution_events.jsonl", "a") as f: f.write(json.dumps(event) + "\n")
    print(f"PASS: recorded {args.event_type} for {args.node_id}")

if __name__ == "__main__":
    main()
