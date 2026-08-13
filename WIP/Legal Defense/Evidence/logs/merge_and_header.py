#!/usr/bin/env python3
"""Merge mlx-whisper clip outputs and prepend DRAFT headers. Local only."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HEADER_TEMPLATE = """\
# DRAFT — not court-ready
# source_filename: {source_filename}
# source_sha256: {source_hash}
# model_id: mlx-community/whisper-large-v3-mlx
# asr_date: {asr_date}
# operator: ib-mac
# pass: 1 local mlx-whisper large-v3
# notes: word timestamps; condition_on_previous_text=False; hallucination_silence_threshold=2; chunked clips merged. Uncertain words marked [INAUDIBLE] where the model emitted empty/garbled loops. Never guess.
"""


def merge_clips(outdir: Path, stem: str) -> dict:
    clips = sorted(
        outdir.glob(f"{stem}_clip_*.json"),
        key=lambda p: int(p.stem.split("_clip_")[1].split("_")[0]),
    )
    if not clips:
        raise SystemExit(f"no clips for {stem}")
    merged: dict = {
        "text": "",
        "segments": [],
        "language": "en",
    }
    texts: list[str] = []
    for clip in clips:
        data = json.loads(clip.read_text(encoding="utf-8"))
        segs = data.get("segments") or []
        merged["segments"].extend(segs)
        t = (data.get("text") or "").strip()
        if t:
            texts.append(t)
        if not merged.get("language"):
            merged["language"] = data.get("language") or "en"
    merged["text"] = "\n".join(texts)
    return merged


def write_outputs(
    outdir: Path,
    stem: str,
    merged: dict,
    source_filename: str,
    source_hash: str,
) -> None:
    asr_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = HEADER_TEMPLATE.format(
        source_filename=source_filename,
        source_hash=source_hash,
        asr_date=asr_date,
    )
    json_path = outdir / f"{stem}.json"
    payload = {
        "source_filename": source_filename,
        "source_hash": source_hash,
        "model_id": "mlx-community/whisper-large-v3-mlx",
        "asr_date": asr_date,
        "operator": "ib-mac",
        "draft": True,
        "court_ready": False,
        "language": merged.get("language") or "en",
        "text": merged.get("text") or "",
        "segments": merged.get("segments") or [],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    txt_path = outdir / f"{stem}.txt"
    lines = [header, "", merged.get("text") or ""]
    for seg in merged.get("segments") or []:
        start = float(seg.get("start") or 0)
        end = float(seg.get("end") or 0)
        text = (seg.get("text") or "").strip()
        if not text:
            text = "[INAUDIBLE]"
        lines.append(f"[{_hms(start)} --> {_hms(end)}]  {text}")
    txt_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    tsv_path = outdir / f"{stem}.tsv"
    tsv = [header.replace("# ", "").strip(), "start\tend\ttext"]
    for seg in merged.get("segments") or []:
        start_ms = int(float(seg.get("start") or 0) * 1000)
        end_ms = int(float(seg.get("end") or 0) * 1000)
        text = (seg.get("text") or "").replace("\t", " ").strip() or "[INAUDIBLE]"
        tsv.append(f"{start_ms}\t{end_ms}\t{text}")
    tsv_path.write_text("\n".join(tsv) + "\n", encoding="utf-8")


def _hms(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}"


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: merge_and_header.py STEM SOURCE_FILENAME SOURCE_HASH")
    stem, source_filename, source_hash = sys.argv[1], sys.argv[2], sys.argv[3]
    outdir = Path(
        "/Users/ib-mac/Cursor-Governance/WIP/Legal Defense/Evidence/derived/transcripts"
    )
    merged = merge_clips(outdir, stem)
    write_outputs(outdir, stem, merged, source_filename, source_hash)
    print(f"merged {stem} segments={len(merged.get('segments') or [])}")


if __name__ == "__main__":
    main()
