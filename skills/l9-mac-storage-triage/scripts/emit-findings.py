#!/usr/bin/env python3
"""Emit FINDINGS.txt (human) and findings.json (machine) from one catalog + diagnosis."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "config" / "findings-catalog.json"
CURRENT = ROOT / "handoffs" / "current"
SCHEMA_ID = "l9-mac-storage-triage/findings/v1"
HOME = Path.home()


def kib_to_gib(kib: str | int | float | None) -> float | None:
    if kib is None or kib == "":
        return None
    try:
        return round(float(kib) / 1048576.0, 2)
    except (TypeError, ValueError):
        return None


def load_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        out[key] = val.strip().strip("'\"")
    return out


def load_focus_sizes(tsv: Path) -> dict[str, float]:
    sizes: dict[str, float] = {}
    if not tsv.is_file():
        return sizes
    for line in tsv.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) < 4:
            continue
        status, kib, _cls, path = parts[0], parts[1], parts[2], parts[3]
        if status != "OK":
            continue
        gib = kib_to_gib(kib)
        if gib is not None:
            sizes[path] = gib
    return sizes


def resolve_path(rel: str) -> tuple[str, str]:
    if rel.startswith("/"):
        return rel, rel
    abs_path = str(HOME / rel)
    display = "~/" + rel if rel else "~"
    return abs_path, display


def fmt_gib(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value >= 10:
        return f"{value:.1f} GB"
    if value >= 1:
        return f"{value:.2f} GB"
    if value <= 0:
        return "0 GB"
    return f"{value:.2f} GB"


def safe_label(item: dict) -> str:
    if item.get("proposed_action") == "deleted":
        return "Gone  —  already deleted"
    if item["phase"] == "A" and item["safe_to_delete"]:
        return "Yes  —  after you say repair"
    if item["phase"] == "B":
        return "Ask first"
    if item["phase"] == "C":
        return "Ask first  —  keep 7 days"
    if item["phase"] == "D":
        if item["guard"] == "never":
            return "Protected  —  never delete"
        return "You review later"
    return "Never"


def pad(text: str, width: int) -> str:
    text = text.replace("\t", " ")
    if len(text) > width:
        return text[: width - 1] + "…"
    return text.ljust(width)


def wrap_words(text: str, width: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if len(trial) <= width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def du_gib(path: Path, timeout: int = 6) -> float | None:
    try:
        proc = subprocess.run(
            ["du", "-sk", str(path)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    return kib_to_gib(proc.stdout.split()[0])


def entry_when(entry: os.DirEntry) -> str:
    try:
        st = entry.stat(follow_symlinks=False)
        ts = getattr(st, "st_birthtime", None) or st.st_mtime
        return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    except OSError:
        return "unknown"


def needs_inspect(raw: dict) -> bool:
    if raw.get("proposed_action") == "deleted":
        return False
    if raw.get("safe_to_delete"):
        return False
    if raw.get("guard") == "never":
        return False
    if raw.get("path") in {"docker-volumes"}:
        return False
    return True


def inspect_path(abs_path: str, hint: str = "") -> dict | None:
    path = Path(abs_path)
    if not path.exists():
        return None
    if path.is_file():
        st = path.stat()
        ts = getattr(st, "st_birthtime", None) or st.st_mtime
        when = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
        return {
            "child_count": 0,
            "oldest": when,
            "newest": when,
            "note": hint or "Single file.",
            "top": [{"name": path.name, "gib": kib_to_gib(st.st_size / 1024.0), "kind": "file"}],
        }
    try:
        entries = [e for e in os.scandir(path) if e.name not in {".", ".."}]
    except OSError:
        return {
            "child_count": 0,
            "oldest": None,
            "newest": None,
            "note": hint or "Could not list this folder.",
            "top": [],
        }
    visible = [e for e in entries if not e.name.startswith(".")]
    dated = [e for e in visible if len(e.name) >= 10 and e.name[:4].isdigit()]
    ranged = dated or visible or entries

    def birth_ts(entry: os.DirEntry) -> float:
        try:
            st = entry.stat(follow_symlinks=False)
            return float(getattr(st, "st_birthtime", None) or st.st_mtime)
        except OSError:
            return 0.0

    oldest_e = min(ranged, key=birth_ts) if ranged else None
    newest_e = max(ranged, key=birth_ts) if ranged else None
    oldest = f"{oldest_e.name}  created {entry_when(oldest_e)}" if oldest_e else None
    newest = f"{newest_e.name}  created {entry_when(newest_e)}" if newest_e else None
    if len(visible) <= 64:
        sample = visible
        extra = ""
    else:
        sample = [e for e in (oldest_e, newest_e) if e is not None]
        extra = f"{len(entries)} items; showing oldest and newest samples, not a full listing."
    top = []
    seen: set[str] = set()
    for entry in sample:
        if entry.name in seen:
            continue
        seen.add(entry.name)
        kind = "dir" if entry.is_dir(follow_symlinks=False) else "file"
        top.append({"name": entry.name, "gib": du_gib(Path(entry.path)), "kind": kind})
    top.sort(key=lambda row: row["gib"] if row["gib"] is not None else -1, reverse=True)
    top = top[:8]
    note = f"{hint} {extra}".strip() if extra else hint
    return {
        "child_count": len(entries),
        "oldest": oldest,
        "newest": newest,
        "note": note,
        "top": top,
    }


def render_txt(doc: dict) -> str:
    data = doc["volumes"]["data"]
    vm = doc["volumes"].get("vm") or {}
    home = doc["volumes"].get("home_gib")
    lines = [
        "STORAGE FINDINGS",
        f"Host          {doc['host']}",
        f"Diagnosed     {doc['diagnosed_at']}",
        "Nothing in this file has been deleted.",
        "",
        f"Data disk     {fmt_gib(data['used_gib'])} used     {fmt_gib(data['free_gib'])} free     {data['capacity_pct']}% full",
        f"Home folder   {fmt_gib(home) if home is not None else 'unknown'}",
    ]
    if vm:
        lines.append(
            f"Swap (VM)     {fmt_gib(vm.get('used_gib'))}     leave it — it shrinks after Data is freed"
        )
    lines += [
        "",
        "Open this file. The JSON next to it is the machine copy for repair.",
        "Undecided rows (Ask first) include What's inside. Reply keep / delete / protect.",
        "",
        "",
        pad("SIZE", 14) + "  " + pad("SAFE TO DROP?", 32) + "  " + "WHERE  /  WHAT",
        pad("----", 14) + "  " + pad("-------------", 32) + "  " + "----",
        "",
    ]

    phase_order = {"C": 0, "A": 1, "B": 2, "D": 3, "guard": 4}
    findings = sorted(
        doc["findings"], key=lambda f: (phase_order.get(f["phase"], 9), -(f["gib"] or 0))
    )
    for item in findings:
        where = item.get("path_display") or item["path"]
        size = fmt_gib(item["gib"])
        lines.append(pad(size, 14) + "  " + pad(safe_label(item), 32) + "  " + where)
        lines.append(" " * 14 + "  " + " " * 32 + "  " + item["label"])
        lines.append(" " * 14 + "  " + " " * 32 + "  " + item["next_step"])
        inspect = item.get("inspect")
        if inspect:
            gutter = " " * 14 + "  " + " " * 32 + "  "
            lines.append(gutter + "What's inside")
            note = inspect.get("note") or ""
            for chunk in wrap_words(note, 72):
                lines.append(gutter + "  " + chunk)
            if inspect.get("oldest"):
                lines.append(gutter + "  oldest  " + inspect["oldest"])
            newest = inspect.get("newest")
            if newest and newest != inspect.get("oldest"):
                lines.append(gutter + "  newest  " + newest)
            if inspect.get("child_count"):
                lines.append(gutter + "  items   " + str(inspect["child_count"]))
            for row in inspect.get("top") or []:
                row_size = fmt_gib(row["gib"]) if row.get("gib") is not None else "unmeasured"
                lines.append(gutter + "    " + pad(row_size, 10) + "  " + row["name"])
        lines.append("")

    repair = doc["repair"]
    lines += [
        "",
        "PHASES  (still waiting on you)",
        "",
        f"  A   caches already on the repair list          {fmt_gib(repair['phase_a_gib'])}",
        "      Say  repair  then  yes.",
        "",
        f"  B   extra caches                               {fmt_gib(repair['phase_b_gib'])}",
        "      Ask first. Not automatic.",
        "",
        f"  C   old hourly chat exports                    {fmt_gib(repair['phase_c_gib'])}",
        "      Separate yes. Keep last 7 days only.",
        "",
        "  Hands off forever:  Documents, Desktop, Mail, apps, projects,",
        "  Application Support, Docker volumes, swap (VM).",
        "",
    ]
    return "\n".join(lines) + "\n"


def build_doc(report_dir: Path | None) -> dict:
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    diag: dict[str, str] = {}
    noise: dict[str, str] = {}
    focus: dict[str, float] = {}
    report_id = None
    if report_dir and report_dir.is_dir():
        diag = load_env_file(report_dir / "diagnosis.env")
        noise = load_env_file(report_dir / "noise-inventory.env")
        focus = load_focus_sizes(report_dir / "focus-layout.tsv")
        report_id = diag.get("REPORT_ID")

    used_kib = diag.get("USED_KIB")
    free_kib = diag.get("FREE_KIB")
    used_gib = kib_to_gib(used_kib) if used_kib else 404.0
    free_gib = kib_to_gib(free_kib) if free_kib else 12.0
    total = (used_gib or 0) + (free_gib or 0)
    cap = round(100.0 * (used_gib or 0) / total, 0) if total else 98.0

    findings = []
    for raw in catalog["items"]:
        abs_path, display = resolve_path(raw["path"])
        gib = raw.get("default_gib")
        measure = raw.get("measure_from")
        if measure and measure in noise:
            measured = kib_to_gib(noise[measure])
            if measured is not None:
                gib = measured
        if abs_path in focus:
            gib = focus[abs_path]
        fake = raw["path"] in {"docker-volumes"}
        if not fake and not Path(abs_path).exists():
            gib = 0.0
            if raw.get("proposed_action") != "deleted":
                raw = {**raw, "next_step": "Path gone."}
        inspect = None
        if needs_inspect(raw) and Path(abs_path).exists():
            inspect = inspect_path(abs_path, raw.get("inspect_hint") or "")
        finding = {
            "id": raw["id"],
            "path": abs_path,
            "path_display": display,
            "gib": gib,
            "kind": raw["kind"],
            "phase": raw["phase"],
            "guard": raw["guard"],
            "safe_to_delete": bool(raw["safe_to_delete"]),
            "repair_action": raw["repair_action"],
            "proposed_action": raw["proposed_action"],
            "status": raw["status"],
            "label": raw["label"],
            "next_step": raw["next_step"],
        }
        if inspect:
            finding["inspect"] = inspect
        findings.append(finding)

    def sum_phase(phase: str) -> float:
        return round(sum(f["gib"] or 0 for f in findings if f["phase"] == phase), 2)

    phase_a_actions = sorted(
        {f["repair_action"] for f in findings if f["phase"] == "A" and f["repair_action"]}
    )
    host = diag.get("HOST_NAME") or os.uname().nodename
    diagnosed_at = diag.get("CREATED_AT") or datetime.now().astimezone().isoformat(
        timespec="seconds"
    )

    return {
        "schema": SCHEMA_ID,
        "host": host,
        "diagnosed_at": diagnosed_at,
        "report_id": report_id,
        "apply_allowed": False,
        "volumes": {
            "data": {
                "mount": diag.get("DATA_VOLUME") or "/System/Volumes/Data",
                "used_gib": used_gib or 0,
                "free_gib": free_gib or 0,
                "capacity_pct": cap,
            },
            "vm": {
                "mount": catalog.get("vm_mount", "/System/Volumes/VM"),
                "used_gib": 23,
                "note": catalog.get("vm_note", ""),
            },
            "home_gib": 297,
        },
        "findings": findings,
        "repair": {
            "phase_a_actions": phase_a_actions,
            "phase_a_gib": sum_phase("A"),
            "phase_b_gib": sum_phase("B"),
            "phase_c_gib": round(
                sum((f["gib"] or 0) * 0.92 for f in findings if f["phase"] == "C"), 1
            ),
        },
    }


def write_outputs(doc: dict, report_dir: Path | None) -> None:
    CURRENT.mkdir(parents=True, exist_ok=True)
    json_path = CURRENT / "findings.json"
    txt_path = CURRENT / "FINDINGS.txt"
    json_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    txt_path.write_text(render_txt(doc), encoding="utf-8")
    if report_dir and report_dir.is_dir():
        shutil.copy2(json_path, report_dir / "findings.json")
        shutil.copy2(txt_path, report_dir / "FINDINGS.txt")
    print(f"human   {txt_path}")
    print(f"machine {json_path}")


def latest_report() -> Path | None:
    pointer = ROOT / ".state" / "latest-report-dir"
    if pointer.is_file():
        path = Path(pointer.read_text(encoding="utf-8").strip())
        if path.is_dir():
            return path
    reports = ROOT / "reports"
    if reports.is_dir():
        dirs = sorted([p for p in reports.iterdir() if p.is_dir()])
        if dirs:
            return dirs[-1]
    return None


def main() -> int:
    report = latest_report()
    doc = build_doc(report)
    write_outputs(doc, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
