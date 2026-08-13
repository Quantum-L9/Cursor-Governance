#!/usr/bin/env python3
"""Clean frames from original MP4 via -ss seek (no crop). Burn file-elapsed clock with Pillow."""
from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

CUSTODY = Path("/Users/ib-mac/Cursor-Governance/WIP/Legal Defense/Evidence")
STEM = "Axon_Body_4_Video_2026-04-30_0153_D01AQ340U"
SRC_FILE = f"{STEM}.mp4"
SRC_HASH = "cacebb5f1f2fc128d2807e3244512da8033a8221c0986b4bf5591bd24e40b30d"
MP4 = CUSTODY / "originals" / SRC_FILE
FRAMES_DIR = CUSTODY / "derived" / "frames"
FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
OPERATOR = "ib-mac"

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


def hms_name(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}-{m:02d}-{sec:02d}"


def hms_label(seconds: float) -> str:
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    frac = seconds - int(seconds)
    return f"{h:02d}:{m:02d}:{sec:02d}.{int(frac*1000):03d} file_elapsed"


def main() -> None:
    FRAMES_DIR.mkdir(parents=True, exist_ok=True)
    font = ImageFont.truetype(FONT, 28)
    deriv = CUSTODY / "logs" / "derivation_log.csv"
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with deriv.open("a", encoding="utf-8") as log:
        for ts, label in FRAMES:
            tag = f"T{hms_name(ts)}_{label}_{STEM}"
            clean = FRAMES_DIR / f"{tag}_clean.png"
            burned = FRAMES_DIR / f"{tag}_burned.png"
            if not clean.exists():
                subprocess.run(
                    [
                        "ffmpeg",
                        "-nostdin",
                        "-hide_banner",
                        "-y",
                        "-ss",
                        f"{ts:.3f}",
                        "-i",
                        str(MP4),
                        "-frames:v",
                        "1",
                        "-q:v",
                        "2",
                        str(clean),
                    ],
                    check=True,
                    capture_output=True,
                )
                log.write(
                    f"{clean.name},{SRC_FILE},{SRC_HASH},frame_clean,{stamp},{OPERATOR}\n"
                )
            img = Image.open(clean).convert("RGB")
            draw = ImageDraw.Draw(img, "RGBA")
            text = hms_label(ts)
            bbox = draw.textbbox((10, 10), text, font=font)
            pad = 6
            draw.rectangle(
                [bbox[0] - pad, bbox[1] - pad, bbox[2] + pad, bbox[3] + pad],
                fill=(0, 0, 0, 153),
            )
            draw.text((10, 10), text, font=font, fill=(255, 255, 0, 255))
            img.convert("RGB").save(burned)
            log.write(
                f"{burned.name},{SRC_FILE},{SRC_HASH},frame_burned_pillow_file_elapsed,{stamp},{OPERATOR}\n"
            )
            print(f"ok {clean.name}")
    print("frames done", len(FRAMES) * 2)


if __name__ == "__main__":
    main()
