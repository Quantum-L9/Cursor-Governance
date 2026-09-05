#!/usr/bin/env python3
"""Ship leftover git work to scoped PRs in the owning repo, then prime main.

Fail-closed: ambiguous or unmatched-untracked paths block apply.
Never broad-add, never force-push, never switch a dirty shared clone.
Concurrent worktrees are left untouched.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SCHEMA = "l9.workspace_clean.plan/v1"
ROUTING_REL = Path("ops/config/workspace-clean-routing.yaml")


def _state_home() -> Path:
    override = os.environ.get("L9_WORKSPACE_CLEAN_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".l9"


def _run(repo: Path, *args: str, check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=check,
    )


def _utc_stamp() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def normalize(path: str) -> str:
    normalized = path.replace("\\", "/").strip()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def porcelain_path(line: str) -> str:
    raw = line[3:] if len(line) >= 3 else line
    raw = raw.strip().strip('"')
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1]
    return normalize(raw)


def glob_match(path: str, pattern: str) -> bool:
    path = normalize(path)
    pattern = pattern.replace("\\", "/")
    if pattern.endswith("/"):
        prefix = pattern.rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    if pattern.endswith("/**"):
        prefix = pattern[:-3].rstrip("/")
        return path == prefix or path.startswith(prefix + "/")
    if fnmatch.fnmatch(path, pattern):
        return True
    if "*" not in pattern and "?" not in pattern and "[" not in pattern:
        return path == pattern or path.startswith(pattern + "/")
    return False


def load_routing(gov_root: Path) -> dict[str, Any]:
    path = gov_root / ROUTING_REL
    if yaml is None:
        raise SystemExit("PyYAML required to load workspace-clean routing")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "l9.workspace_clean.routing/v1":
        raise SystemExit(f"invalid routing schema: {path}")
    return data


def github_from_remote(url: str) -> str | None:
    url = url.strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/.]+?)(?:\.git)?$", url)
    return match.group(1) if match else None


def current_destination(repo: Path, routing: dict[str, Any]) -> str | None:
    proc = _run(repo, "remote", "get-url", "origin")
    if proc.returncode != 0:
        return None
    github = github_from_remote(proc.stdout)
    if not github:
        return None
    for dest_id, dest in (routing.get("destinations") or {}).items():
        if str(dest.get("github") or "") == github:
            return str(dest_id)
    return None


def classify_path(
    rel: str,
    *,
    routing: dict[str, Any],
    current_dest: str | None,
    tracked: bool,
) -> dict[str, str]:
    rel = normalize(rel)
    for pattern in routing.get("never_commit") or []:
        if glob_match(rel, pattern):
            return {"action": "skip", "dest": "", "reason": "never_commit"}

    hits = [
        dest_id
        for dest_id, dest in (routing.get("destinations") or {}).items()
        if any(glob_match(rel, pattern) for pattern in dest.get("globs") or [])
    ]
    if len(hits) > 1:
        return {"action": "ambiguous", "dest": ",".join(hits), "reason": "multiple_globs"}
    if len(hits) == 1:
        return {"action": "ship", "dest": hits[0], "reason": "glob"}

    # Tracked is the ownership signal, the same rule the Claude adapter's
    # installer uses to decide what to exclude: a tracked file is repo content,
    # an untracked one is an activation artifact this machine produced. Testing
    # the pattern before tracked-ness contradicted that — `.claude/` and
    # `.mcp.json` are listed below, and `.mcp.json` is TRACKED in
    # Cursor-Governance itself, so an edit to it classified `machine_local` and
    # never shipped. `never_commit` stays unconditional above: a tracked secret
    # is still a secret.
    if not tracked:
        for pattern in routing.get("skip_machine_local") or []:
            if glob_match(rel, pattern):
                return {"action": "skip", "dest": "", "reason": "machine_local"}
    if tracked and current_dest:
        return {"action": "ship", "dest": current_dest, "reason": "tracked_current_remote"}
    if tracked:
        return {"action": "ambiguous", "dest": "", "reason": "tracked_unknown_remote"}
    return {"action": "ambiguous", "dest": "", "reason": "untracked_unmatched"}


def _worktree_checkouts(repo: Path) -> dict[str, str]:
    """branch name -> worktree path."""
    proc = _run(repo, "worktree", "list", "--porcelain")
    mapping: dict[str, str] = {}
    path = ""
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            path = line.split(" ", 1)[1]
        elif line.startswith("branch refs/heads/"):
            mapping[line.split("refs/heads/", 1)[1]] = path
    return mapping


def _is_ancestor(repo: Path, ancestor: str, tip: str) -> bool:
    proc = _run(repo, "merge-base", "--is-ancestor", ancestor, tip)
    return proc.returncode == 0


def resolve_clone(dest: dict[str, Any]) -> Path | None:
    for hint in dest.get("clone_paths") or []:
        path = Path(os.path.expandvars(os.path.expanduser(str(hint)))).resolve()
        if (path / ".git").exists():
            return path
    return None


def build_plan(
    ws: Path,
    gov_root: Path,
    baseline: str,
    routing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    routing = routing if routing is not None else load_routing(gov_root)
    current_dest = current_destination(ws, routing)
    porcelain = [
        line for line in _run(ws, "status", "--porcelain").stdout.splitlines() if line.strip()
    ]
    tracked_names = set(_run(ws, "ls-files").stdout.splitlines())

    skipped: list[dict[str, str]] = []
    ambiguous: list[dict[str, str]] = []
    by_dest: dict[str, list[str]] = {}

    def _expand(rel: str) -> list[str]:
        path = ws / rel
        if path.is_symlink() or not path.is_dir():
            return [rel.rstrip("/")]
        found: list[str] = []
        for child in path.rglob("*"):
            if child.is_symlink() or child.is_file():
                found.append(normalize(str(child.relative_to(ws))))
        return sorted(found) or [rel.rstrip("/")]

    for line in porcelain:
        rel = porcelain_path(line)
        tracked_parent = rel in tracked_names or line[:2] not in {"??", "!!"}
        for child in _expand(rel):
            tracked = child in tracked_names or tracked_parent
            verdict = classify_path(
                child, routing=routing, current_dest=current_dest, tracked=tracked
            )
            row = {"path": child, **verdict, "porcelain": line[:2].strip()}
            if verdict["action"] == "skip":
                skipped.append(row)
            elif verdict["action"] == "ambiguous":
                ambiguous.append(row)
            else:
                by_dest.setdefault(verdict["dest"], []).append(child)

    checkouts = _worktree_checkouts(ws)
    push_existing: list[dict[str, Any]] = []
    prune: list[dict[str, Any]] = []
    ref_fmt = "%(refname:short)|%(objectname)|%(upstream:short)|%(upstream:track)"
    for line in _run(ws, "for-each-ref", f"--format={ref_fmt}", "refs/heads").stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 4:
            continue
        name, sha, upstream, track = parts[0], parts[1], parts[2], parts[3]
        if name in {"main", "master"}:
            ahead = _run(ws, "rev-list", "--count", f"{baseline}..{name}")
            count = int(ahead.stdout.strip() or "0") if ahead.returncode == 0 else 0
            if count > 0:
                push_existing.append(
                    {
                        "branch": name,
                        "kind": "protected_main_ahead",
                        "ahead_of_baseline": count,
                        "action": "extract_to_feature",
                        "checked_out_at": checkouts.get(name),
                    }
                )
            continue
        if name in checkouts and Path(checkouts[name]).resolve() != ws.resolve():
            continue
        if _is_ancestor(ws, sha, baseline):
            prune.append(
                {
                    "branch": name,
                    "tip": sha[:12],
                    "reason": "ancestor_of_baseline",
                    "checked_out_at": checkouts.get(name),
                }
            )
            continue
        ahead = _run(ws, "rev-list", "--count", f"{baseline}..{name}")
        count = int(ahead.stdout.strip() or "0") if ahead.returncode == 0 else 0
        if count > 0 and (
            not upstream or "ahead" in (track or "").lower() or "gone" in (track or "").lower()
        ):
            push_existing.append(
                {
                    "branch": name,
                    "kind": "unpushed_feature",
                    "ahead_of_baseline": count,
                    "upstream": upstream or None,
                    "track": track or None,
                    "checked_out_at": checkouts.get(name),
                }
            )

    destinations: dict[str, Any] = {}
    for dest_id, dest in (routing.get("destinations") or {}).items():
        paths = by_dest.get(dest_id) or []
        if not paths and dest_id != current_dest:
            continue
        if not paths and not push_existing:
            continue
        clone = resolve_clone(dest)
        destinations[dest_id] = {
            "github": dest.get("github"),
            "clone": str(clone) if clone else None,
            "paths": paths,
            "push_existing": push_existing if dest_id == current_dest else [],
        }

    return {
        "schema": SCHEMA,
        "workspace": str(ws.resolve()),
        "gov_root": str(gov_root.resolve()),
        "baseline": baseline,
        "current_dest": current_dest,
        "branch": _run(ws, "branch", "--show-current").stdout.strip() or None,
        "skipped": skipped,
        "ambiguous": ambiguous,
        "destinations": destinations,
        "prune_candidates": prune,
        "blocked": bool(ambiguous)
        or any(not row.get("clone") and row.get("paths") for row in destinations.values()),
    }


def _copy_into(worktree: Path, src_root: Path, rel: str) -> None:
    src = src_root / rel
    dst = worktree / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst, dirs_exist_ok=True)
    elif src.is_file() or src.is_symlink():
        shutil.copy2(src, dst, follow_symlinks=True)


def _extract_paths(
    *,
    clone: Path,
    dest_id: str,
    src_root: Path,
    rels: list[str],
    baseline: str,
) -> dict[str, str]:
    if not rels:
        raise RuntimeError("extract requested with no paths")
    branch = f"tmp/clean-{dest_id}-{_utc_stamp()}"
    parent = _state_home() / "workspace-clean" / dest_id
    parent.mkdir(parents=True, exist_ok=True)
    worktree = parent / branch
    if worktree.exists():
        raise RuntimeError(f"worktree path already exists: {worktree}")
    base = baseline if _run(clone, "rev-parse", "--verify", baseline).returncode == 0 else "HEAD"
    added = _run(clone, "worktree", "add", "-b", branch, str(worktree), base)
    if added.returncode != 0:
        raise RuntimeError(added.stderr.strip() or "git worktree add failed")
    for rel in rels:
        _copy_into(worktree, src_root, rel)
    staged = _run(worktree, "add", "--", *rels)
    if staged.returncode != 0:
        raise RuntimeError(staged.stderr.strip() or "git add failed")
    committed = _run(
        worktree,
        "commit",
        "-m",
        f"chore(clean): ship routed work for {dest_id}",
    )
    if committed.returncode != 0:
        raise RuntimeError(committed.stderr.strip() or "git commit failed")
    return {
        "branch": branch,
        "worktree": str(worktree),
        "head": _run(worktree, "rev-parse", "HEAD").stdout.strip(),
    }


def _sweep_source(src_root: Path, rels: list[str]) -> None:
    tracked = set(_run(src_root, "ls-files").stdout.splitlines())
    for rel in rels:
        path = src_root / rel
        if rel in tracked:
            restored = _run(src_root, "checkout", "HEAD", "--", rel)
            if restored.returncode != 0:
                raise RuntimeError(restored.stderr.strip() or f"restore failed: {rel}")
            continue
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()


def _prime_main(clone: Path, dest_id: str, baseline: str) -> str | None:
    primed = _state_home() / "primed" / dest_id
    if primed.exists():
        _run(primed, "fetch", "origin", "main")
        _run(primed, "merge", "--ff-only", baseline)
        return str(primed)
    base = baseline if _run(clone, "rev-parse", "--verify", baseline).returncode == 0 else "HEAD"
    added = _run(clone, "worktree", "add", str(primed), base)
    if added.returncode != 0:
        return None
    return str(primed)


def _push_and_pr(worktree: Path, branch: str, github: str, baseline: str) -> dict[str, str]:
    pushed = _run(worktree, "push", "-u", "origin", f"HEAD:refs/heads/{branch}")
    if pushed.returncode != 0:
        raise RuntimeError(pushed.stderr.strip() or "git push failed")
    base_ref = baseline.split("/", 1)[-1] if baseline.startswith("origin/") else baseline
    title = _run(worktree, "log", "-1", "--format=%s").stdout.strip() or branch
    created = subprocess.run(
        [
            "gh",
            "pr",
            "create",
            "--repo",
            github,
            "--base",
            base_ref,
            "--head",
            branch,
            "--title",
            title,
            "--body",
            f"Scoped `make clean` ship for `{github}`.\n\nBranch `{branch}`.",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if created.returncode != 0:
        viewed = subprocess.run(
            ["gh", "pr", "view", "--repo", github, branch, "--json", "url", "-q", ".url"],
            text=True,
            capture_output=True,
            check=False,
        )
        if viewed.returncode == 0 and viewed.stdout.strip():
            return {"pr": viewed.stdout.strip(), "push": "ok"}
        raise RuntimeError(created.stderr.strip() or "gh pr create failed")
    return {"pr": created.stdout.strip(), "push": "ok"}


def apply_plan(
    plan: dict[str, Any],
    *,
    remote: bool,
    sweep: bool,
) -> dict[str, Any]:
    if plan.get("blocked"):
        raise SystemExit("apply blocked: resolve ambiguous paths or missing clones first")
    ws = Path(plan["workspace"])
    baseline = str(plan["baseline"])
    results: dict[str, Any] = {"shipped": {}, "pruned": [], "primed": {}, "errors": []}

    for dest_id, dest in (plan.get("destinations") or {}).items():
        clone_s = dest.get("clone")
        if not clone_s:
            if dest.get("paths"):
                results["errors"].append(f"{dest_id}: clone not found")
            continue
        clone = Path(clone_s)
        rels = list(dest.get("paths") or [])
        if rels:
            try:
                extract = _extract_paths(
                    clone=clone,
                    dest_id=dest_id,
                    src_root=ws,
                    rels=rels,
                    baseline=baseline,
                )
                if remote:
                    extract.update(
                        _push_and_pr(
                            Path(extract["worktree"]),
                            extract["branch"],
                            str(dest["github"]),
                            baseline,
                        )
                    )
                if sweep:
                    _sweep_source(ws, rels)
                results["shipped"][dest_id] = extract
            except Exception as exc:  # noqa: BLE001 — report, do not clobber others
                results["errors"].append(f"{dest_id}: {exc}")
                continue

        if remote:
            for row in dest.get("push_existing") or []:
                if row.get("kind") == "protected_main_ahead":
                    branch = f"tmp/clean-{dest_id}-main-ahead-{_utc_stamp()}"
                    parent = _state_home() / "workspace-clean" / dest_id
                    parent.mkdir(parents=True, exist_ok=True)
                    worktree = parent / branch
                    added = _run(clone, "worktree", "add", "-b", branch, str(worktree), "HEAD")
                    if added.returncode != 0:
                        results["errors"].append(f"{dest_id} main-ahead: {added.stderr.strip()}")
                        continue
                    try:
                        results["shipped"].setdefault(dest_id, {})["main_ahead"] = _push_and_pr(
                            worktree, branch, str(dest["github"]), baseline
                        )
                    except Exception as exc:  # noqa: BLE001
                        results["errors"].append(f"{dest_id} main-ahead: {exc}")
                    continue
                name = row["branch"]
                other = row.get("checked_out_at")
                if other and Path(other).resolve() != ws.resolve():
                    results["errors"].append(f"skip {name}: checked out in another worktree")
                    continue
                pushed = _run(ws, "push", "-u", "origin", name)
                if pushed.returncode != 0:
                    results["errors"].append(f"push {name}: {pushed.stderr.strip()}")
                    continue
                try:
                    results["shipped"].setdefault(dest_id, {}).setdefault("existing", []).append(
                        _push_and_pr(ws, name, str(dest["github"]), baseline)
                    )
                except Exception as exc:  # noqa: BLE001
                    results["errors"].append(f"pr {name}: {exc}")

        primed = _prime_main(clone, dest_id, baseline)
        if primed:
            results["primed"][dest_id] = primed

    for row in plan.get("prune_candidates") or []:
        if row.get("checked_out_at"):
            continue
        deleted = _run(ws, "branch", "-d", row["branch"])
        if deleted.returncode == 0:
            results["pruned"].append(row["branch"])
        else:
            results["errors"].append(f"prune {row['branch']}: {deleted.stderr.strip()}")

    results["ok"] = not results["errors"]
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", default=".", help="Consumer or SSOT work tree")
    parser.add_argument("--gov-root", default="", help="Cursor-Governance clone")
    parser.add_argument("--baseline", default="origin/main")
    parser.add_argument("--mode", choices=("plan", "apply"), default="plan")
    parser.add_argument("--remote", action="store_true", help="Push and open scoped PRs")
    parser.add_argument(
        "--no-sweep",
        action="store_true",
        help="Leave shipped files in the source tree",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    ws = Path(args.workspace).expanduser().resolve()
    if args.gov_root:
        gov_root = Path(args.gov_root).expanduser().resolve()
    else:
        gov_root = Path(__file__).resolve().parents[2]
    plan = build_plan(ws, gov_root, args.baseline)
    result: dict[str, Any] = {"plan": plan}
    if args.mode == "apply":
        result["apply"] = apply_plan(plan, remote=args.remote, sweep=not args.no_sweep)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        _print_human(result)
    if plan.get("blocked") and args.mode == "apply":
        return 2
    if result.get("apply") and not result["apply"].get("ok"):
        return 1
    return 0


def _print_human(result: dict[str, Any]) -> None:
    plan = result["plan"]
    print(f"workspace: {plan['workspace']}")
    print(f"current_dest: {plan.get('current_dest') or 'unknown'}")
    print(f"branch: {plan.get('branch')}")
    if plan["skipped"]:
        reasons: dict[str, int] = {}
        for row in plan["skipped"]:
            reasons[row["reason"]] = reasons.get(row["reason"], 0) + 1
        print(f"skip {len(plan['skipped'])} machine-local/secret path(s): {reasons}")
    if plan["ambiguous"]:
        print(f"BLOCKED ambiguous ({len(plan['ambiguous'])}):")
        for row in plan["ambiguous"][:40]:
            print(f"  {row['path']}  ({row['reason']})")
        if len(plan["ambiguous"]) > 40:
            print(f"  … {len(plan['ambiguous']) - 40} more")
    for dest_id, dest in plan["destinations"].items():
        print(f"dest {dest_id} -> {dest.get('github')} clone={dest.get('clone')}")
        for rel in dest.get("paths") or []:
            print(f"  ship {rel}")
        for row in dest.get("push_existing") or []:
            print(f"  existing {row['kind']} {row['branch']} ahead={row.get('ahead_of_baseline')}")
    if plan["prune_candidates"]:
        print("prune (merged local):")
        for row in plan["prune_candidates"]:
            extra = ""
            if row.get("checked_out_at"):
                extra = f" (checked out at {row['checked_out_at']})"
            print(f"  {row['branch']}{extra}")
    if plan["blocked"]:
        print("RESULT: BLOCKED — fix ambiguous paths or missing clones")
    elif "apply" in result:
        apply = result["apply"]
        print(f"RESULT: {'PASS' if apply.get('ok') else 'FAIL'}")
        for dest_id, payload in (apply.get("shipped") or {}).items():
            print(f"  shipped {dest_id}: {payload}")
        if apply.get("pruned"):
            print(f"  pruned: {apply['pruned']}")
        if apply.get("primed"):
            print(f"  primed: {apply['primed']}")
        for err in apply.get("errors") or []:
            print(f"  error: {err}")
    else:
        print("RESULT: PLAN (re-run --mode apply to ship)")


if __name__ == "__main__":
    raise SystemExit(main())
