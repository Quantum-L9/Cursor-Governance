#!/usr/bin/env python3
"""Shelf leftover corpus after /ff: untracked and dirty-tracked.

Owns ``TODO.md``, ``WIP/``, ``docs/plans/``, and
``environment/program-execution/campaigns/``. Writes
``$CLONE/.l9/ff-shelf-untracked.txt`` then ``rsync --files-from`` that path
(no process substitution, no ``/tmp`` files-from). Appends an existing
same-author ``feat/ff-shelf-*`` worktree, or cuts one stamp when none is open.
``git add --pathspec-from-file`` is a separate command from commit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

LIST_REL = ".l9/ff-shelf-untracked.txt"
SHELF_EXACT = ("TODO.md",)
SHELF_PREFIXES = (
    "WIP/",
    "docs/plans/",
    "environment/program-execution/campaigns/",
)
SKIP_PREFIXES = ("WIP/Legal Defense/",)
SECRET_NAME_RE = re.compile(r"(oauth|credentials|client_secret)", re.I)
SHA_FIELD_RE = re.compile(r'(body_sha256:\s*["\']?)([^"\'\s]+)(["\']?)')
ZERO_DIGEST = "0" * 64


@dataclass(frozen=True)
class OpenShelfPR:
    head: str
    author: str
    updated_at: str
    number: int = 0


def run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - caller supplies fixed argv
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        env=env,
        check=check,
    )


def is_shelf_path(rel: str) -> bool:
    norm = rel.replace("\\", "/").lstrip("./")
    if any(norm.startswith(prefix) for prefix in SKIP_PREFIXES):
        return False
    if SECRET_NAME_RE.search(Path(norm).name):
        return False
    if norm in SHELF_EXACT:
        return True
    return any(norm.startswith(prefix) for prefix in SHELF_PREFIXES)


def collect_untracked(clone: Path) -> list[str]:
    proc = run(
        ["git", "-C", str(clone), "ls-files", "--others", "--exclude-standard"],
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "git ls-files failed")
    paths = []
    for raw in proc.stdout.splitlines():
        rel = raw.strip().strip('"')
        if rel and is_shelf_path(rel):
            paths.append(rel)
    return paths


def _dirty_names(clone: Path, diff_filter: str) -> list[str]:
    proc = run(
        [
            "git",
            "-C",
            str(clone),
            "diff",
            "--name-only",
            f"--diff-filter={diff_filter}",
            "HEAD",
        ],
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "git diff --name-only failed")
    paths = []
    for raw in proc.stdout.splitlines():
        rel = raw.strip().strip('"')
        if rel and is_shelf_path(rel):
            paths.append(rel)
    return paths


def collect_dirty_tracked(clone: Path) -> list[str]:
    """Copyable dirty-tracked corpus. Deletions are not rsync sources."""
    return [rel for rel in _dirty_names(clone, "ACMRT") if (clone / rel).exists()]


def collect_dirty_deleted(clone: Path) -> list[str]:
    return _dirty_names(clone, "D")


def collect_shelf_paths(clone: Path) -> list[str]:
    return sorted(set(collect_untracked(clone)) | set(collect_dirty_tracked(clone)))


def apply_shelf_deletions(shelf: Path, deleted: list[str]) -> None:
    for rel in deleted:
        target = shelf / rel
        if not target.exists() and not target.is_symlink():
            continue
        proc = run(["git", "-C", str(shelf), "rm", "-f", "--", rel], check=False)
        if proc.returncode != 0 and target.exists():
            target.unlink()


def write_untracked_list(clone: Path, paths: list[str]) -> Path:
    dest = clone / LIST_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("".join(f"{p}\n" for p in paths), encoding="utf-8")
    return dest


def files_from_ok(list_path: Path, clone: Path) -> None:
    resolved = list_path.resolve()
    expected = (clone / LIST_REL).resolve()
    if resolved != expected:
        raise RuntimeError(f"files-from must be {expected}, got {resolved}")
    text = str(resolved)
    if "/tmp/" in text and "/.l9/" not in text:
        raise RuntimeError("files-from must not be a /tmp path")


def build_rsync_argv(clone: Path, shelf: Path, list_path: Path) -> list[str]:
    files_from_ok(list_path, clone)
    return [
        "rsync",
        "-R",
        f"--files-from={list_path}",
        f"{clone}/",
        f"{shelf}/",
    ]


def build_add_argv(shelf: Path, list_path: Path) -> list[str]:
    return [
        "git",
        "-C",
        str(shelf),
        "add",
        f"--pathspec-from-file={list_path}",
    ]


def build_commit_argv(shelf: Path, message: str) -> list[str]:
    return ["git", "-C", str(shelf), "commit", "-m", message]


def load_open_shelf_prs(path: Path | None) -> list[OpenShelfPR]:
    if path is None:
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    rows: list[OpenShelfPR] = []
    for item in raw:
        author = item.get("author")
        login = author.get("login") if isinstance(author, dict) else str(author or "")
        rows.append(
            OpenShelfPR(
                head=str(item.get("headRefName") or item.get("head") or ""),
                author=login,
                updated_at=str(item.get("updatedAt") or item.get("updated_at") or ""),
                number=int(item.get("number") or 0),
            )
        )
    return rows


def gh_login() -> str:
    proc = run(["gh", "api", "user", "--jq", ".login"])
    if proc.returncode != 0:
        return ""
    return proc.stdout.strip()


def github_repo_slug(clone: Path) -> str:
    proc = run(["git", "-C", str(clone), "remote", "get-url", "origin"])
    if proc.returncode != 0:
        return ""
    url = proc.stdout.strip()
    if url.endswith(".git"):
        url = url[: -len(".git")]
    for prefix in ("https://github.com/", "git@github.com:"):
        if url.startswith(prefix):
            return url[len(prefix) :]
    return ""


def gh_open_shelf_prs(clone: Path) -> list[OpenShelfPR]:
    cmd = [
        "gh",
        "pr",
        "list",
        "--state",
        "open",
        "--search",
        "head:feat/ff-shelf-",
        "--json",
        "number,headRefName,author,updatedAt",
    ]
    slug = github_repo_slug(clone)
    if slug:
        cmd.extend(["--repo", slug])
    proc = run(cmd, cwd=clone)
    if proc.returncode != 0:
        return []
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError:
        return []
    rows: list[OpenShelfPR] = []
    for item in data:
        author = item.get("author") or {}
        rows.append(
            OpenShelfPR(
                head=str(item.get("headRefName") or ""),
                author=str(author.get("login") or ""),
                updated_at=str(item.get("updatedAt") or ""),
                number=int(item.get("number") or 0),
            )
        )
    return [row for row in rows if row.head.startswith("feat/ff-shelf-")]


def resolve_shelf_branch(
    prs: list[OpenShelfPR],
    author: str,
    stamp: str,
) -> tuple[str, str]:
    """Return (branch, action) where action is append or stamp."""
    if not author:
        return f"feat/ff-shelf-{stamp}", "stamp"
    mine = [p for p in prs if p.head.startswith("feat/ff-shelf-") and p.author == author]
    if not mine:
        return f"feat/ff-shelf-{stamp}", "stamp"
    mine.sort(key=lambda p: p.updated_at, reverse=True)
    return mine[0].head, "append"


def worktree_for_branch(clone: Path, branch: str) -> Path | None:
    proc = run(["git", "-C", str(clone), "worktree", "list", "--porcelain"])
    current: Path | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            current = Path(line[len("worktree ") :])
        elif line.startswith("branch refs/heads/") and current is not None:
            if line[len("branch refs/heads/") :] == branch:
                return current
            current = None
    return None


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def blob_sha256(repo: Path, rev: str, rel: str) -> str | None:
    show = subprocess.run(  # noqa: S603 - fixed argv
        ["git", "-C", str(repo), "cat-file", "blob", f"{rev}:{rel}"],
        capture_output=True,
        check=False,
    )
    if show.returncode != 0:
        return None
    return hashlib.sha256(show.stdout).hexdigest()


def drop_already_shelved(clone: Path, paths: list[str], branch: str) -> list[str]:
    kept: list[str] = []
    for rel in paths:
        local = sha256_file(clone / rel)
        remote = blob_sha256(clone, branch, rel)
        if local and remote and local == remote:
            continue
        kept.append(rel)
    return kept


def _canonical_sha_field(text: str) -> str:
    return SHA_FIELD_RE.sub(lambda m: f"{m.group(1)}{ZERO_DIGEST}{m.group(3)}", text)


def stamp_kernel_pass(path: Path) -> None:
    if path.suffix != ".md" or not path.name.endswith(".plan.md"):
        return
    raw = path.read_text(encoding="utf-8")
    now = datetime.now(UTC).replace(microsecond=0)
    t1 = now.isoformat().replace("+00:00", "Z")
    t2 = (now + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")
    t3 = (now + timedelta(seconds=2)).isoformat().replace("+00:00", "Z")
    bound = path.name
    block = (
        "kernel_pass:\n"
        f"  bound_path: {bound}\n"
        "  improve:\n"
        "    kernel: kernels/Improve.md\n"
        f"    ran_at: {t1}\n"
        "    deltas:\n"
        "      - ff_shelf corpus pass\n"
        "  recursive_alignment:\n"
        "    kernel: kernels/Recursive Alignment.md\n"
        f"    ran_at: {t2}\n"
        "    deltas:\n"
        "      - ff_shelf corpus pass\n"
        "  validate_repair:\n"
        "    kernel: kernels/Validate & Repair.md\n"
        f"    ran_at: {t3}\n"
        f'    body_sha256: "{ZERO_DIGEST}"\n'
        "    deltas:\n"
        "      - ff_shelf corpus pass\n"
    )
    if raw.startswith("---"):
        end = raw.find("\n---", 3)
        if end != -1:
            fm = raw[4:end]
            body = raw[end + 4 :]
            fm = re.sub(r"(?ms)^kernel_pass:.*?(?=^[a-zA-Z_]|\Z)", "", fm).rstrip() + "\n"
            raw = f"---\n{fm}{block}---{body}"
        else:
            raw = f"---\n{block}---\n{raw}"
    else:
        raw = f"---\n{block}---\n{raw}"
    digest = hashlib.sha256(_canonical_sha_field(raw).encode("utf-8")).hexdigest()
    raw = raw.replace(f'body_sha256: "{ZERO_DIGEST}"', f'body_sha256: "{digest}"', 1)
    path.write_text(raw, encoding="utf-8")


def gov_python(shelf: Path) -> str:
    local = shelf / ".venv" / "bin" / "python"
    if local.is_file():
        return str(local)
    env = os.environ.get("GOV_PY")
    if env:
        return env
    home = Path.home() / ".cursor-governance" / ".venv" / "bin" / "python"
    if home.is_file():
        return str(home)
    return sys.executable


def ensure_shelf_worktree(
    clone: Path,
    shelf: Path,
    branch: str,
    action: str,
    base_ref: str,
) -> None:
    existing = worktree_for_branch(clone, branch)
    if existing is not None:
        return
    if shelf.exists():
        return
    wired = clone / "ops" / "scripts" / "worktree_add_wired.sh"
    if action == "append":
        fetched = run(["git", "-C", str(clone), "fetch", "origin", branch])
        if fetched.returncode != 0:
            raise RuntimeError(fetched.stderr or fetched.stdout or f"fetch {branch} failed")
        argv = (
            ["bash", str(wired), str(shelf), branch]
            if wired.is_file()
            else [
                "git",
                "-C",
                str(clone),
                "worktree",
                "add",
                str(shelf),
                branch,
            ]
        )
    elif wired.is_file():
        argv = ["bash", str(wired), "-b", branch, str(shelf), base_ref]
    else:
        argv = ["git", "-C", str(clone), "worktree", "add", "-b", branch, str(shelf), base_ref]
    proc = run(argv, cwd=clone)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "worktree add failed")


def resolve_base_ref(clone: Path, override: str | None) -> str:
    if override:
        return override
    resolver = clone / "ops" / "scripts" / "resolve_stack_tip.py"
    if resolver.is_file():
        proc = run([gov_python(clone), str(resolver), "--workspace", str(clone)])
        if proc.returncode == 0:
            for line in proc.stdout.splitlines():
                if line.startswith("STACK_TIP="):
                    return line.split("=", 1)[1]
    return "origin/main"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clone", required=True, type=Path)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--author", default="")
    parser.add_argument("--open-shelf-prs", type=Path)
    parser.add_argument("--shelf-worktree", type=Path)
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--stamp", default="")
    args = parser.parse_args(argv)

    clone = args.clone.expanduser().resolve()
    if not (clone / ".git").exists() and not (clone / ".git").is_file():
        # worktree .git is a file; missing entirely is a hard fail
        gitdir = run(["git", "-C", str(clone), "rev-parse", "--show-toplevel"])
        if gitdir.returncode != 0:
            print(f"FAIL: not a git clone: {clone}", file=sys.stderr)
            return 2

    paths = collect_shelf_paths(clone)
    deleted = collect_dirty_deleted(clone)
    stamp = args.stamp or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    author = args.author or ("" if args.open_shelf_prs else gh_login())
    prs = (
        load_open_shelf_prs(args.open_shelf_prs)
        if args.open_shelf_prs
        else gh_open_shelf_prs(clone)
    )
    branch, action = resolve_shelf_branch(prs, author, stamp)
    if action == "append" and paths:
        paths = drop_already_shelved(clone, paths, branch)
    has_work = bool(paths or deleted)
    list_path = write_untracked_list(clone, paths)
    shelf = args.shelf_worktree
    if shelf is None:
        shelf = clone.parent / f"{clone.name}.{branch.replace('/', '-')}"
    else:
        shelf = shelf.expanduser()

    rsync_argv = build_rsync_argv(clone, shelf, list_path) if paths else []
    add_argv = build_add_argv(shelf, list_path) if paths else []
    commit_msg = f"ff-shelf leftover corpus ({stamp})"
    commit_argv = build_commit_argv(shelf, commit_msg) if has_work else []
    report = {
        "clone": str(clone),
        "list_path": str(list_path),
        "paths": paths,
        "deleted": deleted,
        "action": action if has_work else "empty",
        "branch": branch,
        "shelf": str(shelf),
        "rsync": rsync_argv,
        "add": add_argv,
        "commit": commit_argv,
    }
    if args.dry_run or not has_work:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0

    joined_rsync = " ".join(rsync_argv)
    if "<(" in joined_rsync or "/tmp/" in str(list_path) and "/.l9/" not in str(list_path):
        print("FAIL: rsync files-from must be the in-clone list", file=sys.stderr)
        return 2
    if add_argv and ("commit" in add_argv or "status" in add_argv):
        print("FAIL: git add must not also commit or status", file=sys.stderr)
        return 2

    base_ref = resolve_base_ref(clone, args.base_ref or None)
    ensure_shelf_worktree(clone, shelf, branch, action, base_ref)
    if paths:
        proc = run(rsync_argv)
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return 1
        for rel in paths:
            stamp_kernel_pass(shelf / rel)
        add_proc = run(add_argv)
        if add_proc.returncode != 0:
            print(add_proc.stderr or add_proc.stdout, file=sys.stderr)
            return 1
    if deleted:
        apply_shelf_deletions(shelf, deleted)
    commit_proc = run(commit_argv)
    if commit_proc.returncode != 0:
        print(commit_proc.stderr or commit_proc.stdout, file=sys.stderr)
        return 1

    py = gov_python(shelf)
    l4 = shelf / "ops" / "autonomy" / "l4_local.py"
    if l4.is_file():
        begin = run(
            [py, str(l4), "--workspace", str(shelf), "begin", "--contract-id", f"ff-shelf-{stamp}"]
        )
        if begin.returncode != 0:
            print(begin.stderr or begin.stdout, file=sys.stderr)
            return 1
        auth = run([py, str(l4), "--workspace", str(shelf), "authorize-release"])
        if auth.returncode != 0:
            print(auth.stderr or auth.stdout, file=sys.stderr)
            return 1

    if os.environ.get("FF_SHELF_PUBLISH", "1") != "0":
        env = dict(os.environ)
        env["PR_STACK"] = "auto"
        env["PR_REMEDIATE"] = "0"
        published = run(["make", "pr"], cwd=shelf, env=env)
        if published.returncode != 0:
            print(published.stderr or published.stdout, file=sys.stderr)
            return 1
        print(published.stdout)

    post = clone / "ops" / "scripts" / "run_ff_post_shelf.sh"
    if post.is_file():
        post_proc = run(["bash", str(post), str(clone)])
        if post_proc.returncode != 0:
            print(post_proc.stderr or post_proc.stdout, file=sys.stderr)
            return 1
    verify = clone / "ops" / "scripts" / "verify_worktree_clean.py"
    if verify.is_file():
        verify_proc = run([gov_python(clone), str(verify), "--workspace", str(clone)])
        if verify_proc.returncode != 0:
            print(verify_proc.stderr or verify_proc.stdout, file=sys.stderr)
            return 1
    print(json.dumps({**report, "published": os.environ.get("FF_SHELF_PUBLISH", "1") != "0"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
