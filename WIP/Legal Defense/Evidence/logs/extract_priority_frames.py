#!/usr/bin/env python3
"""Extract clean+burned priority frames from a draft transcript. Local only."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CUSTODY = Path("/Users/ib-mac/Cursor-Governance/WIP/Legal Defense/Evidence")
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FALLBACK_FONT = "/Library/Fonts/Arial.ttf"

ODOR = re.compile(
    r"\b(smell|smells|odor|marijuana|cannabis|weed|dope|pot)\b", re.I
)
EXIT = re.compile(
    r"\b(step out|get out|handcuff|cuffs|cuffed|turn around|put your hands)\b", re.I
)
SEARCH = re.compile(
    r"\b(search|probable cause|I'm going to search|going to search)\b", re.I
)
TRUNK = re.compile(
    r"\b(trunk|hatch|rear|open it|pop the|recovered|I found|found this|bag)\b", re.I
)


def hms_name(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}-{m:02d}-{sec:02d}"


def locate(segments: list[dict]) -> list[tuple[float, str]]:
    hits: list[tuple[float, str]] = []
    seen: set[tuple[str, int]] = set()

    def add(ts: float, label: str) -> None:
        key = (label, int(ts))
        if key in seen:
            return
        seen.add(key)
        hits.append((max(0.0, ts), label))

    # Opening 120s: 0, 30, 60, 90, 119
    for ts in (0.5, 30.0, 60.0, 90.0, 119.0):
        add(ts, "opening")

    first_odor = None
    for seg in segments:
        text = (seg.get("text") or "")
        start = float(seg.get("start") or 0)
        if first_odor is None and ODOR.search(text):
            first_odor = start
            add(max(0.0, start - 45), "odor_pre")
            add(start, "odor")
            add(start + 45, "odor_post")
        if EXIT.search(text):
            add(start, "exit_order")
        if SEARCH.search(text) and start < 600:
            add(start, "search_pc")
        if TRUNK.search(text):
            add(start, "trunk_or_recovery")

    return hits[:18]  # cap per file so total stays dozens


def grab(mp4: Path, ts: float, label: str, stem: str, font: str | None, log) -> None:
    frames = CUSTODY / "derived" / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    tag = f"T{hms_name(ts)}_{label}_{stem}"
    clean = frames / f"{tag}_clean.png"
    burned = frames / f"{tag}_burned.png"
    ts_s = f"{ts:.3f}"
    common = [
        "ffmpeg",
        "-nostdin",
        "-hide_banner",
        "-y",
        "-ss",
        ts_s,
        "-i",
        str(mp4),
        "-frames:v",
        "1",
        "-q:v",
        "2",
    ]
    subprocess.run(common + [str(clean)], check=True, capture_output=True)
    log.write(
        f"{clean.name},{mp4.name},frame_clean,{datetime.now(timezone.utc).isoformat()}\n"
    )
    if font:
        vf = (
            f"drawtext=fontfile={font}:text='%{{pts\\:hms}}':x=10:y=10:"
            "fontsize=28:fontcolor=yellow:box=1:boxcolor=black@0.6"
        )
        subprocess.run(common + ["-vf", vf, str(burned)], check=True, capture_output=True)
        log.write(
            f"{burned.name},{mp4.name},frame_burned,{datetime.now(timezone.utc).isoformat()}\n"
        )


def main() -> None:
    stem = sys.argv[1]
    json_path = CUSTODY / "derived" / "transcripts" / f"{stem}.json"
    mp4 = CUSTODY / "originals" / f"{stem}.mp4"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    segs = data.get("segments") or []
    hits = locate(segs)
    font = FONT if Path(FONT).exists() else (
        FALLBACK_FONT if Path(FALLBACK_FONT).exists() else None
    )
    deriv = CUSTODY / "logs" / "derivation_log.csv"
    with deriv.open("a", encoding="utf-8") as log:
        for ts, label in hits:
            try:
                grab(mp4, ts, label, stem, font, log)
                print(f"frame {label} @{ts:.1f}s")
            except subprocess.CalledProcessError as exc:
                print(f"FAILED frame {label} @{ts:.1f}s: {exc}")
    print(f"frames attempted={len(hits)} font={'yes' if font else 'no'}")


if __name__ == "__main__":
    main()
