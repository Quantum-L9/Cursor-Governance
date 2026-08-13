#!/usr/bin/env python3
"""Build EVENT_LOG_20260430.csv from this batch only. Local investigation artifact."""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

CUSTODY = Path("/Users/ib-mac/Cursor-Governance/WIP/Legal Defense/Evidence")
OUT = CUSTODY / "logs" / "EVENT_LOG_20260430.csv"
STILLS = CUSTODY / "logs" / "stills_index.csv"
TXDIR = CUSTODY / "derived" / "transcripts"

# Overlay refs that this batch can touch. Do not invent others.
# F004/F005: sequence of drinking/travel/cannabis vs odor — CONFLICT if odor precedes dispensary talk.
ODOR = re.compile(r"\b(smell|smells|odor|marijuana|cannabis|weed)\b", re.I)
DISPENSARY = re.compile(r"\b(dispensary|cbd|shop|legal)\b", re.I)
DRINK = re.compile(r"\b(drink|drinking|alcohol|beer)\b", re.I)
CONSENT = re.compile(r"\b(consent|can i search|mind if i search|permission)\b", re.I)
EXIT = re.compile(r"\b(step out|get out|handcuff|cuffs)\b", re.I)
TRUNK = re.compile(r"\b(trunk|hatch|recovered|I found)\b", re.I)

FIELDS = [
    "timestamp",
    "source_file",
    "timebase",
    "actor",
    "type",
    "content",
    "direct_quote",
    "quote_source",
    "overlay_ref",
    "confidence",
    "conflict_flag",
]


def csv_write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in FIELDS})


def stills_rows() -> list[dict]:
    rows: list[dict] = []
    with STILLS.open(encoding="utf-8") as fh:
        for rec in csv.DictReader(fh):
            desc = rec.get("description") or ""
            overlay = "UNKNOWN"
            conflict = ""
            low = desc.lower()
            if any(
                x in low
                for x in (
                    "tablet",
                    "crystalline",
                    "capsule",
                    "edible",
                    "vaporizer",
                    "mushroom",
                    "plant/",
                    "scale",
                )
            ):
                overlay = "F012"
            if "currency" in low or "$100" in desc or "$20" in desc:
                overlay = "UNKNOWN"
            if "firearm" in low or "rifle" in low or "pistol" in low or "revolver" in low:
                overlay = "UNKNOWN"
            # F011 asserts zero plant material; mason jar / vacuum bag of plant-like material is a possible conflict to flag, not resolve.
            if "plant/mushroom" in low or "mushroom-like" in low:
                overlay = "F011"
                conflict = "CONFLICT"
            rows.append(
                {
                    "timestamp": rec.get("filename_clock") or "Unknown",
                    "source_file": rec.get("filename") or "",
                    "timebase": "filename_clock",
                    "actor": "Unknown",
                    "type": "still_visual",
                    "content": desc,
                    "direct_quote": "",
                    "quote_source": "STILL_VISUAL",
                    "overlay_ref": overlay,
                    "confidence": "med",
                    "conflict_flag": conflict,
                }
            )
    return rows


def hms(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}"


def whisper_rows(stem: str) -> list[dict]:
    path = TXDIR / f"{stem}.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    segs = data.get("segments") or []
    rows: list[dict] = []
    odor_t = None
    disp_t = None
    drink_t = None
    for seg in segs:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = float(seg.get("start") or 0)
        kind = None
        overlay = "UNKNOWN"
        conflict = ""
        if ODOR.search(text):
            kind = "odor_or_cannabis_talk"
            overlay = "F018"
            if odor_t is None:
                odor_t = start
        elif DISPENSARY.search(text):
            kind = "dispensary_or_cbd_talk"
            overlay = "F005"
            if disp_t is None:
                disp_t = start
        elif DRINK.search(text):
            kind = "alcohol_talk"
            overlay = "F004"
            if drink_t is None:
                drink_t = start
        elif CONSENT.search(text):
            kind = "consent_talk"
            overlay = "F008"
        elif EXIT.search(text):
            kind = "exit_or_cuff"
            overlay = "F009"
        elif TRUNK.search(text):
            kind = "trunk_or_recovery"
            overlay = "UNKNOWN"
        else:
            continue
        # Truncate quote; mark draft.
        quote = text[:240]
        rows.append(
            {
                "timestamp": hms(start),
                "source_file": f"{stem}.mp4",
                "timebase": "file_elapsed",
                "actor": "Unknown",
                "type": kind,
                "content": "pass-1 mlx-whisper large-v3 draft; not court-ready",
                "direct_quote": quote,
                "quote_source": "WHISPER_DRAFT",
                "overlay_ref": overlay,
                "confidence": "low",
                "conflict_flag": conflict,
            }
        )
    # Sequence conflicts vs overlay F004/F005: odor before dispensary talk contradicts F005.
    if odor_t is not None and disp_t is not None and odor_t < disp_t:
        rows.append(
            {
                "timestamp": hms(odor_t),
                "source_file": f"{stem}.mp4",
                "timebase": "file_elapsed",
                "actor": "Unknown",
                "type": "sequence_note",
                "content": "WHISPER_DRAFT places first odor/cannabis-smell talk before first dispensary/CBD talk on this file elapsed clock; contradicts overlay F005 (dispensary-before-odor). Overlay not edited.",
                "direct_quote": "",
                "quote_source": "WHISPER_DRAFT",
                "overlay_ref": "F005",
                "confidence": "low",
                "conflict_flag": "CONFLICT",
            }
        )
    if odor_t is not None and drink_t is not None and odor_t < drink_t:
        rows.append(
            {
                "timestamp": hms(odor_t),
                "source_file": f"{stem}.mp4",
                "timebase": "file_elapsed",
                "actor": "Unknown",
                "type": "sequence_note",
                "content": "WHISPER_DRAFT places first odor talk at or before later drinking talk on this file; overlay F004 (drink then travel then cannabis) flagged. Overlay not edited.",
                "direct_quote": "",
                "quote_source": "WHISPER_DRAFT",
                "overlay_ref": "F004",
                "confidence": "low",
                "conflict_flag": "CONFLICT",
            }
        )
    return rows


def main() -> None:
    stems = [
        "Axon_Body_4_Video_2026-04-30_0153_D01AQ340U",
        "Axon_Body_4_Video_2026-04-30_0211_D01AQ223T",
        "Axon_Body_4_Video_2026-04-30_0312_D01AQ223T",
        "Axon_Body_4_Video_2026-04-30_0426_D01AQ340U",
    ]
    rows: list[dict] = []
    for stem in stems:
        rows.extend(whisper_rows(stem))
    rows.extend(stills_rows())
    csv_write(OUT, rows)
    print(f"wrote {OUT} rows={len(rows)}")


if __name__ == "__main__":
    main()
