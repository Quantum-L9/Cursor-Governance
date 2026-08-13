#!/usr/bin/env python3
"""Harvest interrupted mlx-whisper stdout into DRAFT transcripts and key frames.

Timestamps stay on the original file clock: the log came from --clip-timestamps
0,600 on the full WAV (not a cropped file). Frames use ffmpeg -ss on originals/.
"""
from __future__ import annotations

import csv
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CUSTODY = Path("/Users/ib-mac/Cursor-Governance/WIP/Legal Defense/Evidence")
STEM = "Axon_Body_4_Video_2026-04-30_0153_D01AQ340U"
SRC_FILE = f"{STEM}.mp4"
SRC_HASH = "cacebb5f1f2fc128d2807e3244512da8033a8221c0986b4bf5591bd24e40b30d"
MODEL = "mlx-community/whisper-large-v3-mlx"
OPERATOR = "ib-mac"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
LINE = re.compile(
    r"^\[(\d+):(\d+(?:\.\d+)?)\s+-->\s+(\d+):(\d+(?:\.\d+)?)\]\s*(.*)$"
)

# Skill §8 windows already present in the log (file elapsed seconds).
FRAMES = [
    (36.0, "opening_radio"),
    (82.0, "opening_contact"),
    (94.0, "improper_turn"),
    (114.3, "marijuana_question"),
    (118.4, "odor_statement"),
    (163.1, "firearm_in_vehicle"),
    (187.0, "exit_order"),
    (197.0, "search_pc_marijuana"),
    (306.4, "search_for_marijuana"),
    (313.7, "driver_little_marijuana"),
    (330.96, "cbd_shop_question"),
    (334.4, "cupholder_concentrate"),
]


def to_sec(mm: str, ss: str) -> float:
    return int(mm) * 60 + float(ss)


def hms(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}"


def hms_name(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}-{m:02d}-{sec:02d}"


def parse_log(path: Path) -> list[dict]:
    segs: list[dict] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINE.match(raw.strip())
        if not m:
            continue
        start = to_sec(m.group(1), m.group(2))
        end = to_sec(m.group(3), m.group(4))
        text = (m.group(5) or "").strip() or "[INAUDIBLE]"
        segs.append({"start": start, "end": end, "text": text})
    return segs


def write_transcripts(segs: list[dict]) -> None:
    outdir = CUSTODY / "derived" / "transcripts"
    outdir.mkdir(parents=True, exist_ok=True)
    asr_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    header = (
        "# DRAFT — not court-ready\n"
        f"# source_filename: {SRC_FILE}\n"
        f"# source_sha256: {SRC_HASH}\n"
        f"# model_id: {MODEL}\n"
        f"# asr_date: {asr_date}\n"
        f"# operator: {OPERATOR}\n"
        "# pass: 1 local mlx-whisper large-v3 (harvested from verbose stdout)\n"
        "# timebase: file_elapsed on full WAV via --clip-timestamps 0,600; file was not cropped\n"
        "# coverage: ~00:00:36–00:08:48 of 02:22:54; job stopped after priority windows (skill §8 1–3)\n"
        "# gap: ~00:06:07–00:08:46 (no segments). Remainder of this file not transcribed.\n"
        "# Uncertain words: [INAUDIBLE] rather than guesses. Never court-ready.\n"
    )
    payload = {
        "source_filename": SRC_FILE,
        "source_hash": SRC_HASH,
        "model_id": MODEL,
        "asr_date": asr_date,
        "operator": OPERATOR,
        "draft": True,
        "court_ready": False,
        "timebase": "file_elapsed",
        "coverage_note": "harvested_priority_window_00_36_to_08_48",
        "language": "en",
        "text": " ".join(s["text"] for s in segs),
        "segments": segs,
    }
    (outdir / f"{STEM}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    txt_lines = [header, ""]
    for s in segs:
        txt_lines.append(f"[{hms(s['start'])} --> {hms(s['end'])}]  {s['text']}")
    (outdir / f"{STEM}.txt").write_text("\n".join(txt_lines) + "\n", encoding="utf-8")
    tsv = [
        header.replace("# ", "").strip(),
        "start_ms\tend_ms\ttext",
    ]
    for s in segs:
        tsv.append(
            f"{int(s['start']*1000)}\t{int(s['end']*1000)}\t{s['text'].replace(chr(9), ' ')}"
        )
    (outdir / f"{STEM}.tsv").write_text("\n".join(tsv) + "\n", encoding="utf-8")
    deriv = CUSTODY / "logs" / "derivation_log.csv"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with deriv.open("a", encoding="utf-8") as fh:
        for ext in ("json", "txt", "tsv"):
            fh.write(
                f"{STEM}.{ext},{SRC_FILE},{SRC_HASH},harvest_mlx_stdout_priority_window,{stamp},{OPERATOR}\n"
            )


def grab_frames() -> None:
    mp4 = CUSTODY / "originals" / SRC_FILE
    frames = CUSTODY / "derived" / "frames"
    frames.mkdir(parents=True, exist_ok=True)
    deriv = CUSTODY / "logs" / "derivation_log.csv"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with deriv.open("a", encoding="utf-8") as log:
        for ts, label in FRAMES:
            tag = f"T{hms_name(ts)}_{label}_{STEM}"
            clean = frames / f"{tag}_clean.png"
            burned = frames / f"{tag}_burned.png"
            ts_s = f"{ts:.3f}"
            base = [
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
            subprocess.run(base + [str(clean)], check=True, capture_output=True)
            log.write(f"{clean.name},{SRC_FILE},{SRC_HASH},frame_clean,{stamp},{OPERATOR}\n")
            vf = (
                f"drawtext=fontfile={FONT}:text='%{{pts\\:hms}}':x=10:y=10:"
                "fontsize=28:fontcolor=yellow:box=1:boxcolor=black@0.6"
            )
            subprocess.run(
                base + ["-vf", vf, str(burned)], check=True, capture_output=True
            )
            log.write(
                f"{burned.name},{SRC_FILE},{SRC_HASH},frame_burned,{stamp},{OPERATOR}\n"
            )
            print(f"frame {label} @{ts:.1f}s")


def rebuild_event_log(segs: list[dict]) -> None:
    # Reuse stills builder then prepend whisper rows from harvested segs.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "build_event_log", CUSTODY / "logs" / "build_event_log.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    def hms_short(seconds: float) -> str:
        s = int(seconds)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{sec:02d}"

    odor_re = re.compile(r"\b(smell|smells|odor|marijuana|cannabis)\b", re.I)
    disp_re = re.compile(r"\b(dispensary|cbd|shop)\b", re.I)
    drink_re = re.compile(r"\b(drink|drinking)\b", re.I)
    exit_re = re.compile(r"\b(step out|get out)\b", re.I)
    search_re = re.compile(r"\b(search|probable cause)\b", re.I)
    gun_re = re.compile(r"\b(gun|handgun|firearm)\b", re.I)

    rows: list[dict] = []
    odor_t = disp_t = drink_t = None
    for s in segs:
        text = s["text"]
        start = s["start"]
        kind = overlay = None
        if odor_re.search(text):
            kind, overlay = "odor_or_cannabis_talk", "F018"
            if odor_t is None:
                odor_t = start
        elif disp_re.search(text):
            kind, overlay = "dispensary_or_cbd_talk", "F005"
            if disp_t is None:
                disp_t = start
        elif drink_re.search(text):
            kind, overlay = "alcohol_talk", "F004"
            if drink_t is None:
                drink_t = start
        elif exit_re.search(text):
            kind, overlay = "exit_or_cuff", "F009"
        elif search_re.search(text):
            kind, overlay = "search_talk", "F019"
        elif gun_re.search(text):
            kind, overlay = "firearm_talk", "UNKNOWN"
        if not kind:
            continue
        rows.append(
            {
                "timestamp": hms_short(start),
                "source_file": SRC_FILE,
                "timebase": "file_elapsed",
                "actor": "Unknown",
                "type": kind,
                "content": "pass-1 mlx-whisper large-v3 draft harvested from 0153 priority window; not court-ready",
                "direct_quote": text[:240],
                "quote_source": "WHISPER_DRAFT",
                "overlay_ref": overlay,
                "confidence": "low",
                "conflict_flag": "",
            }
        )
    if odor_t is not None and disp_t is not None and odor_t < disp_t:
        rows.append(
            {
                "timestamp": hms_short(odor_t),
                "source_file": SRC_FILE,
                "timebase": "file_elapsed",
                "actor": "Unknown",
                "type": "sequence_note",
                "content": "WHISPER_DRAFT places first odor/cannabis-smell talk before first CBD/shop talk on this file elapsed clock; contradicts overlay F005 (dispensary-before-odor). Overlay not edited.",
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
                "timestamp": hms_short(odor_t),
                "source_file": SRC_FILE,
                "timebase": "file_elapsed",
                "actor": "Unknown",
                "type": "sequence_note",
                "content": "WHISPER_DRAFT places first odor talk before drinking talk on this file; overlay F004 (drink then travel then cannabis) flagged. Overlay not edited.",
                "direct_quote": "",
                "quote_source": "WHISPER_DRAFT",
                "overlay_ref": "F004",
                "confidence": "low",
                "conflict_flag": "CONFLICT",
            }
        )
    elif odor_t is not None and drink_t is not None and drink_t < odor_t:
        pass  # sequence matches F004 on this file; no conflict row
    rows.extend(mod.stills_rows())
    out = CUSTODY / "logs" / "EVENT_LOG_20260430.csv"
    with out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=mod.FIELDS)
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in mod.FIELDS})
    print(f"event_log rows={len(rows)}")


def main() -> None:
    segs = parse_log(CUSTODY / "logs" / "asr_0153.log")
    if not segs:
        raise SystemExit("no segments in asr_0153.log")
    write_transcripts(segs)
    print(f"harvested segments={len(segs)} start={segs[0]['start']:.1f} end={segs[-1]['end']:.1f}")
    grab_frames()
    rebuild_event_log(segs)


if __name__ == "__main__":
    main()
