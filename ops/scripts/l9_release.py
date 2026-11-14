#!/usr/bin/env python3
"""``make release`` — one release command for every L9 repository.

Used exactly like ``make pr``::

    l9 release [VERSION=X.Y.Z] [DRY_RUN=1]
    make -C "$GOV" release WS="$PWD" [VERSION=X.Y.Z] [DRY_RUN=1]

It releases the workspace repository from a clean ``origin/<default>`` commit,
as declared by ``<repo>/.l9/release.json`` (schema ``l9.release/v1``):

1. declaration — load and validate ``.l9/release.json``; absent → refuse naming it.
2. preflight   — clean tree; HEAD == freshly fetched origin/<default>; zero open
                 PRs into it (REST); version authorities agree, equal VERSION when
                 given, exceed the latest exact ``v*`` tag; the exact tag is absent
                 remotely; a dated CHANGELOG section exists.
3. gate        — ``make setup validate check test`` (+ the declared pre-release
                 argv) in a separate clean checkout of that commit.
4. build       — two independent clean checkouts, ``SOURCE_DATE_EPOCH`` = commit
                 time, per-ecosystem adapter; sdist envelope normalised when (and
                 only when) it is not byte-reproducible; byte-identical or refuse;
                 ``SHA256SUMS``.            ← DRY_RUN=1 stops here.
5. publish     — requires the operator's publish-path breakglass receipt naming the
                 exact tag and commit; annotated (signed when a signing key is
                 configured) tag; plain push of that one ref; major tag created when
                 declared and absent (an existing one is handed to the operator —
                 this command never force-pushes); ``gh release create --verify-tag``
                 with CHANGELOG notes + provenance and the assets.
6. verify      — re-download the assets, ``sha256sum -c``, tag peels to the commit;
                 receipt ``.l9/release/release-receipt.json``.

Exit codes: 0 RELEASED / DRY_RUN_PASS, 1 REFUSED, 2 DECLARATION_INVALID,
3 TRANSPORT_BLOCKED, 4 NOT_REPRODUCIBLE, 5 COMPLETION_REQUIRED (operator step
outstanding), 6 VERIFY_FAILED.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ops" / "scripts"))
sys.path.insert(0, str(ROOT / "ops" / "autonomy"))

import release_declaration as decl  # noqa: E402
import release_reproducible as repro  # noqa: E402

RECEIPT_SCHEMA = "l9.release-receipt/v1"
RECEIPT_REL = Path(".l9/release/release-receipt.json")
ASSETS_REL = Path(".l9/release")
CORE_PHASES = ("setup", "validate", "check", "test")

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_DECLARATION = 2
EXIT_TRANSPORT = 3
EXIT_NOT_REPRODUCIBLE = 4
EXIT_COMPLETION_REQUIRED = 5
EXIT_VERIFY = 6

#: Variables the governance Make invocation carries that must not leak into the
#: released repository's own Make or build (command-line overrides propagate
#: through MAKEFLAGS; Repo.mk exports PYTHON as the governance interpreter).
_ISOLATED_ENV_DROP = frozenset(
    {
        "MAKEFLAGS",
        "MFLAGS",
        "MAKELEVEL",
        "MAKEOVERRIDES",
        "MAKE_TERMOUT",
        "MAKE_TERMERR",
        "PYTHON",
        "VIRTUAL_ENV",
        "WS",
        "VERSION",
        "DRY_RUN",
        "GOV_ROOT",
        "PYTHONPATH",
    }
)


class Stop(Exception):
    """A terminal outcome other than success."""

    def __init__(self, code: int, status: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.status = status
        self.detail = detail


# ---------------------------------------------------------------------------
# Process boundaries
# ---------------------------------------------------------------------------
def isolated_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _ISOLATED_ENV_DROP}
    env.update(extra or {})
    return env


def run(
    argv: list[str],
    cwd: Path,
    *,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(  # noqa: S603 - argv lists only, never a shell
        argv, cwd=cwd, env=env, text=True, capture_output=True, check=False
    )
    if check and proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-15:]
        raise subprocess.CalledProcessError(
            proc.returncode, argv, output=proc.stdout, stderr="\n".join(tail)
        )
    return proc


def git(cwd: Path, *args: str, check: bool = True) -> str:
    return run(["git", *args], cwd, check=check).stdout.strip()


class GitHub:
    """The one GitHub transport boundary: ``gh`` (REST via ``gh api``, plus
    ``gh release create|download``). Tests stub the ``gh`` executable."""

    def __init__(self, repo: str, cwd: Path, gh: str = "gh") -> None:
        self.repo = repo
        self.cwd = cwd
        self.gh = gh

    def _gh(self, *args: str) -> subprocess.CompletedProcess[str]:
        return run([self.gh, *args], self.cwd, check=False)

    def open_prs(self, base: str) -> list[int]:
        proc = self._gh(
            "api",
            "--method",
            "GET",
            f"repos/{self.repo}/pulls",
            "-f",
            "state=open",
            "-f",
            f"base={base}",
            "-f",
            "per_page=100",
            "--paginate",
            "--jq",
            ".[].number",
        )
        if proc.returncode != 0:
            raise Stop(
                EXIT_TRANSPORT,
                "TRANSPORT_BLOCKED",
                f"open-PR query failed: {(proc.stderr or proc.stdout).strip()}",
            )
        return [int(line) for line in proc.stdout.split() if line.strip()]

    def release(self, tag: str) -> dict[str, Any] | None:
        proc = self._gh("api", "--method", "GET", f"repos/{self.repo}/releases/tags/{tag}")
        if proc.returncode != 0:
            if "404" in proc.stderr or "Not Found" in (proc.stderr + proc.stdout):
                return None
            raise Stop(
                EXIT_TRANSPORT,
                "TRANSPORT_BLOCKED",
                f"release query failed: {(proc.stderr or proc.stdout).strip()}",
            )
        record = json.loads(proc.stdout or "{}")
        return record if isinstance(record, dict) else None

    def create_release(self, tag: str, notes: Path, assets: list[Path]) -> None:
        proc = self._gh(
            "release",
            "create",
            tag,
            "--repo",
            self.repo,
            "--verify-tag",
            "--title",
            tag,
            "--notes-file",
            str(notes),
            *[str(asset) for asset in assets],
        )
        if proc.returncode != 0:
            raise Stop(
                EXIT_TRANSPORT,
                "TRANSPORT_BLOCKED",
                f"gh release create failed: {(proc.stderr or proc.stdout).strip()}",
            )

    def download(self, tag: str, dest: Path) -> None:
        proc = self._gh("release", "download", tag, "--repo", self.repo, "--dir", str(dest))
        if proc.returncode != 0:
            raise Stop(
                EXIT_VERIFY,
                "VERIFY_FAILED",
                f"gh release download failed: {(proc.stderr or proc.stdout).strip()}",
            )


# ---------------------------------------------------------------------------
# Context
# ---------------------------------------------------------------------------
@dataclass
class Release:
    workspace: Path
    declaration: decl.Declaration
    commit: str
    version: str
    tag: str
    epoch: int
    dry_run: bool
    notes_body: str
    changelog_date: str
    work: Path
    stages: dict[str, Any] = field(default_factory=dict)
    assets: dict[str, str] = field(default_factory=dict)

    @property
    def assets_dir(self) -> Path:
        return self.workspace / ASSETS_REL / self.tag


_GITHUB_URL = re.compile(
    r"^(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)"
    r"(?P<slug>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)


def origin_slug(workspace: Path) -> str:
    url = git(workspace, "config", "--get", "remote.origin.url", check=False)
    match = _GITHUB_URL.match(url)
    if match is None:
        raise Stop(EXIT_REFUSED, "REFUSED", f"origin {url!r} is not a GitHub repository URL")
    return match.group("slug")


def remote_tags(workspace: Path) -> dict[str, str]:
    """Map remote tag name → the commit it peels to."""
    out = run(["git", "ls-remote", "--tags", "origin"], workspace, check=False)
    if out.returncode != 0:
        raise Stop(EXIT_TRANSPORT, "TRANSPORT_BLOCKED", f"git ls-remote failed: {out.stderr}")
    direct: dict[str, str] = {}
    peeled: dict[str, str] = {}
    for line in out.stdout.splitlines():
        sha, _, ref = line.partition("\t")
        if not ref.startswith("refs/tags/"):
            continue
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            peeled[name.removesuffix("^{}")] = sha
        else:
            direct[name] = sha
    return {name: peeled.get(name, sha) for name, sha in direct.items()}


# ---------------------------------------------------------------------------
# Stages
# ---------------------------------------------------------------------------
def stage_preflight(
    workspace: Path, declaration: decl.Declaration, github: GitHub, requested: str | None
) -> tuple[str, str, int, str, str]:
    """Return (commit, version, epoch, changelog_date, notes_body)."""
    slug = origin_slug(workspace)
    if slug.lower() != declaration.repository.lower():
        raise Stop(
            EXIT_REFUSED,
            "REFUSED",
            f"origin is {slug} but .l9/release.json declares {declaration.repository}",
        )
    dirty = git(
        workspace,
        "status",
        "--porcelain",
        "--untracked-files=all",
        "--",
        ".",
        f":(exclude){ASSETS_REL.as_posix()}",
    )
    if dirty:
        raise Stop(EXIT_REFUSED, "REFUSED", f"worktree is not clean:\n{dirty}")
    branch = declaration.default_branch
    fetched = run(
        [
            "git",
            "fetch",
            "--quiet",
            "--no-tags",
            "origin",
            f"+refs/heads/{branch}:refs/remotes/origin/{branch}",
        ],
        workspace,
        check=False,
    )
    if fetched.returncode != 0:
        raise Stop(EXIT_TRANSPORT, "TRANSPORT_BLOCKED", f"git fetch failed: {fetched.stderr}")
    head = git(workspace, "rev-parse", "HEAD")
    tip = git(workspace, "rev-parse", f"refs/remotes/origin/{branch}")
    if head != tip:
        raise Stop(
            EXIT_REFUSED, "REFUSED", f"HEAD {head} is not freshly fetched origin/{branch} {tip}"
        )
    open_prs = github.open_prs(branch)
    if open_prs:
        raise Stop(
            EXIT_REFUSED,
            "REFUSED",
            f"{len(open_prs)} open PR(s) target {branch}: {sorted(open_prs)}",
        )

    def at_head(relpath: str) -> str:
        return git(workspace, "show", f"{head}:{relpath}")

    try:
        version = decl.declared_version(declaration, at_head)
        changelog_date, notes_body = decl.changelog_section(at_head(declaration.changelog), version)
    except (decl.DeclarationError, subprocess.CalledProcessError) as exc:
        raise Stop(EXIT_REFUSED, "REFUSED", str(exc)) from exc
    if requested is not None and requested != version:
        raise Stop(
            EXIT_REFUSED,
            "REFUSED",
            f"VERSION={requested} but the version authority says {version}",
        )
    tags = remote_tags(workspace)
    tag = f"v{version}"
    if tag in tags:
        raise Stop(EXIT_REFUSED, "REFUSED", f"tag {tag} already exists remotely at {tags[tag]}")
    released = [v for v in (decl.exact_tag_version(name) for name in tags) if v is not None]
    latest = max(released, default=None)
    if latest is not None and decl.parse_semver(version) <= latest:
        raise Stop(
            EXIT_REFUSED,
            "REFUSED",
            f"version {version} is not greater than the latest tag v{'.'.join(map(str, latest))}",
        )
    epoch = int(git(workspace, "show", "-s", "--format=%ct", head))
    return head, version, epoch, changelog_date, notes_body


def checkout(workspace: Path, commit: str, dest: Path) -> Path:
    run(["git", "clone", "--quiet", "--no-hardlinks", str(workspace), str(dest)], workspace)
    git(dest, "checkout", "--quiet", "--detach", commit)
    if git(dest, "rev-parse", "HEAD") != commit:
        raise Stop(EXIT_REFUSED, "REFUSED", f"clean checkout {dest} is not at {commit}")
    return dest


def stage_gate(rel: Release) -> None:
    gate_dir = checkout(rel.workspace, rel.commit, rel.work / "gate")
    env = isolated_env()
    steps: list[dict[str, Any]] = []
    commands = [["make", *CORE_PHASES]]
    if rel.declaration.pre_release_argv:
        commands.append(list(rel.declaration.pre_release_argv))
    for argv in commands:
        proc = run(argv, gate_dir, env=env, check=False)
        log = rel.work / f"gate-{len(steps)}.log"
        log.write_text(proc.stdout + proc.stderr, encoding="utf-8")
        steps.append({"argv": argv, "exit": proc.returncode})
        if proc.returncode != 0:
            tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-20:])
            rel.stages["gate"] = {"status": "FAIL", "steps": steps}
            raise Stop(
                EXIT_REFUSED,
                "REFUSED",
                f"gate {' '.join(argv)} failed at {rel.commit} (exit {proc.returncode}):\n{tail}",
            )
    rel.stages["gate"] = {"status": "PASS", "steps": steps}


def _build_once(rel: Release, label: str) -> dict[str, tuple[str, Path]]:
    """Build every ecosystem in a fresh checkout. Return name → (ecosystem, path)."""
    source = checkout(rel.workspace, rel.commit, rel.work / f"build-{label}")
    produced: dict[str, tuple[str, Path]] = {}
    env = isolated_env({"SOURCE_DATE_EPOCH": str(rel.epoch)})
    for eco in rel.declaration.ecosystems:
        out = rel.work / f"out-{label}" / eco.kind
        out.mkdir(parents=True)
        if eco.kind == "python-uv":
            argv = ["uv", "build", "--out-dir", str(out)]
        elif eco.kind == "node-npm":
            argv = ["npm", "pack", "--pack-destination", str(out)]
        else:  # pragma: no cover - schema enum
            raise Stop(EXIT_DECLARATION, "DECLARATION_INVALID", f"unknown ecosystem {eco.kind}")
        proc = run(argv, source, env=env, check=False)
        if proc.returncode != 0:
            tail = "\n".join((proc.stdout + proc.stderr).strip().splitlines()[-20:])
            raise Stop(EXIT_REFUSED, "REFUSED", f"{' '.join(argv)} failed:\n{tail}")
        for path in sorted(out.iterdir()):
            if _is_uv_out_dir_sentinel(eco.kind, path):
                continue
            if path.name in produced:
                raise Stop(EXIT_REFUSED, "REFUSED", f"two ecosystems produced {path.name}")
            produced[path.name] = (eco.kind, path)
    return produced


def _is_uv_out_dir_sentinel(kind: str, path: Path) -> bool:
    """``uv build --out-dir`` writes a ``.gitignore`` containing exactly ``*`` so the
    output directory ignores itself. It is build plumbing, not an artifact; any
    other stray file still fails the exact-artifact-set check."""
    return (
        kind == "python-uv"
        and path.name == ".gitignore"
        and path.read_text(encoding="utf-8", errors="replace").strip() == "*"
    )


def stage_build(rel: Release) -> None:
    first = _build_once(rel, "a")
    second = _build_once(rel, "b")
    expected = set(rel.declaration.artifact_names(rel.version))
    for label, built in (("a", first), ("b", second)):
        if set(built) != expected:
            raise Stop(
                EXIT_REFUSED,
                "REFUSED",
                f"build {label} produced {sorted(built)}, declared {sorted(expected)}",
            )
    normalised: list[str] = []
    evidence: dict[str, Any] = {}
    for name in sorted(expected):
        kind, path_a = first[name]
        _, path_b = second[name]
        raw_a, raw_b = repro.sha256_file(path_a), repro.sha256_file(path_b)
        entry: dict[str, Any] = {"ecosystem": kind, "raw": [raw_a, raw_b]}
        if raw_a != raw_b:
            if not (kind == "python-uv" and name.endswith(".tar.gz")):
                raise Stop(
                    EXIT_NOT_REPRODUCIBLE,
                    "NOT_REPRODUCIBLE",
                    f"{name} differs across two clean builds ({raw_a} vs {raw_b})",
                )
            try:
                digests_a = repro.normalise_sdist(path_a, rel.epoch)
                digests_b = repro.normalise_sdist(path_b, rel.epoch)
            except repro.ReproducibilityError as exc:
                raise Stop(EXIT_NOT_REPRODUCIBLE, "NOT_REPRODUCIBLE", str(exc)) from exc
            if digests_a != digests_b:
                raise Stop(
                    EXIT_NOT_REPRODUCIBLE,
                    "NOT_REPRODUCIBLE",
                    f"{name}: member contents differ across builds",
                )
            normalised.append(name)
            entry["normalised"] = [repro.sha256_file(path_a), repro.sha256_file(path_b)]
            entry["members"] = len(digests_a)
            entry["member_contents_unchanged"] = True
        final_a, final_b = repro.sha256_file(path_a), repro.sha256_file(path_b)
        if final_a != final_b:
            raise Stop(
                EXIT_NOT_REPRODUCIBLE,
                "NOT_REPRODUCIBLE",
                f"{name} is not byte-identical after normalisation ({final_a} vs {final_b})",
            )
        entry["sha256"] = final_a
        evidence[name] = entry
        rel.assets[name] = final_a
    if rel.assets_dir.exists():
        shutil.rmtree(rel.assets_dir)
    rel.assets_dir.mkdir(parents=True)
    for name in sorted(expected):
        shutil.copy2(first[name][1], rel.assets_dir / name)
    repro.write_sha256sums(rel.assets_dir, sorted(expected))
    rel.stages["build"] = {
        "status": "PASS",
        "source_date_epoch": rel.epoch,
        "builds": 2,
        "normalised": normalised,
        "artifacts": evidence,
        "assets_dir": str(rel.assets_dir),
    }


def build_environment() -> dict[str, str]:
    def version_of(argv: list[str]) -> str:
        try:
            proc = subprocess.run(argv, text=True, capture_output=True, check=False)  # noqa: S603
        except OSError:
            return "absent"
        return (
            (proc.stdout or proc.stderr).strip().splitlines()[0]
            if proc.returncode == 0
            else "absent"
        )

    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "uv": version_of(["uv", "--version"]),
        "node": version_of(["node", "--version"]),
        "npm": version_of(["npm", "--version"]),
        "git": version_of(["git", "--version"]),
    }


def authorization(rel: Release) -> dict[str, Any]:
    """The publish authority: the operator's publish-path breakglass receipt.

    ``make release`` pushes a tag ref, which is a first publication outside
    ``make pr`` (CANONICAL_LAW §6.2.8). The existing operator authority for that
    push is the publish-path breakglass receipt (``ops/autonomy/breakglass_receipt.py``,
    skills/l9-release-publication/references/publication-plane.md). It must be in
    force and its reason must name this exact tag and commit (≥12 hex)."""
    import breakglass_receipt as breakglass

    verdict = breakglass.evaluate(breakglass.load_receipt())
    reason = str(verdict.get("reason") or "")
    bound = rel.tag in reason.split() and any(
        token in reason for token in (rel.commit, rel.commit[:12])
    )
    record = {
        "authority": "publish-path breakglass receipt",
        "status": verdict.get("status"),
        "issuer": verdict.get("issuer"),
        "expires_at": verdict.get("expires_at"),
        "reason": reason,
        "binds_tag_and_commit": bound,
    }
    if not verdict.get("in_force") or not bound:
        raise Stop(
            EXIT_REFUSED,
            "UNAUTHORIZED",
            "publication needs the operator's publish-path breakglass receipt naming "
            f"{rel.tag} and {rel.commit[:12]}: "
            f"{breakglass.__file__} --write --issuer ops --hours 1 "
            f"--reason 'make release {rel.tag} {rel.commit}' "
            f"(status: {verdict.get('status')}; {verdict.get('detail')})",
        )
    return record


def _operator_handoff(rel: Release, what: str) -> str:
    return (
        f"{what}. From an operator clone at {rel.commit}:\n"
        f"  git tag -s {rel.tag} {rel.commit} -m {rel.tag}   # -a when no signing key\n"
        f"  git push origin refs/tags/{rel.tag}\n"
        f"then attach {rel.assets_dir}/* to the Release and rerun verification."
    )


def stage_tag(rel: Release) -> None:
    signing_key = git(rel.workspace, "config", "--get", "user.signingkey", check=False)
    local = git(
        rel.workspace, "rev-parse", "--verify", "--quiet", f"refs/tags/{rel.tag}", check=False
    )
    if local:
        peeled = git(rel.workspace, "rev-parse", f"{rel.tag}^{{commit}}")
        if peeled != rel.commit:
            raise Stop(
                EXIT_REFUSED, "REFUSED", f"local tag {rel.tag} exists at {peeled}, not {rel.commit}"
            )
        kind = git(rel.workspace, "cat-file", "-t", f"refs/tags/{rel.tag}")
        if kind != "tag":
            raise Stop(EXIT_REFUSED, "REFUSED", f"local tag {rel.tag} exists but is not annotated")
        signed = "-----BEGIN" in git(rel.workspace, "cat-file", "tag", f"refs/tags/{rel.tag}")
    else:
        flag = "-s" if signing_key else "-a"
        git(rel.workspace, "tag", flag, rel.tag, "-m", rel.tag, rel.commit)
        signed = bool(signing_key)
    tag_object = git(rel.workspace, "rev-parse", f"refs/tags/{rel.tag}")
    rel.stages["tag"] = {
        "tag": rel.tag,
        "tag_object": tag_object,
        "signed": signed,
        "note": "signed (user.signingkey)"
        if signed
        else "annotated, unsigned: no signing key configured",
    }
    push = run(["git", "push", "origin", f"refs/tags/{rel.tag}"], rel.workspace, check=False)
    if push.returncode != 0:
        rel.stages["tag"]["push"] = "FAILED"
        raise Stop(
            EXIT_TRANSPORT,
            "TRANSPORT_BLOCKED",
            _operator_handoff(rel, f"tag push refused: {push.stderr.strip()}"),
        )
    rel.stages["tag"]["push"] = "PUSHED"


def stage_major(rel: Release) -> bool:
    """Return True when an operator step is outstanding."""
    if rel.declaration.major_tag == "none":
        rel.stages["major_tag"] = {"policy": "none"}
        return False
    major = f"v{decl.parse_semver(rel.version)[0]}"
    tags = remote_tags(rel.workspace)
    current = tags.get(major)
    record: dict[str, Any] = {"policy": "advance", "tag": major, "before": current}
    rel.stages["major_tag"] = record
    if current == rel.commit:
        record["outcome"] = "ALREADY_AT_RELEASE"
        return False
    if current is None:
        push = run(
            ["git", "push", "origin", f"{rel.commit}:refs/tags/{major}"],
            rel.workspace,
            check=False,
        )
        if push.returncode != 0:
            record["outcome"] = "CREATE_FAILED"
            record["detail"] = push.stderr.strip()
            return True
        record["outcome"] = "CREATED"
        return False
    behind = (
        run(
            ["git", "merge-base", "--is-ancestor", current, rel.commit],
            rel.workspace,
            check=False,
        ).returncode
        == 0
    )
    if not behind:
        record["outcome"] = "NOT_ADVANCED_NOT_BEHIND"
        record["detail"] = (
            f"{major} at {current} is not an ancestor of {rel.commit}; never backwards"
        )
        return False
    record["outcome"] = "OPERATOR_REQUIRED"
    record["operator_command"] = (
        f"git push --force-with-lease=refs/tags/{major}:{current} origin "
        f"{rel.commit}:refs/tags/{major}"
    )
    return True


def render_notes(rel: Release) -> Path:
    lines = [
        rel.notes_body,
        "",
        "---",
        "",
        "### Provenance",
        "",
        f"- Repository: `{rel.declaration.repository}`",
        f"- Commit: `{rel.commit}`",
        f"- Tag: `{rel.tag}` ({rel.stages.get('tag', {}).get('note', 'annotated')})",
        f"- CHANGELOG: {rel.declaration.changelog} section {rel.version} ({rel.changelog_date})",
        f"- SOURCE_DATE_EPOCH: `{rel.epoch}` (commit time); two independent clean builds, "
        "byte-identical",
    ]
    normalised = rel.stages.get("build", {}).get("normalised", [])
    if normalised:
        lines.append(
            "- sdist archive envelope normalised (member order, mtime, owner, gzip header); "
            "member contents proven unchanged: " + ", ".join(f"`{n}`" for n in normalised)
        )
    env = rel.stages.get("build_environment", {})
    lines.append("- Build environment: " + ", ".join(f"{k} `{v}`" for k, v in env.items()))
    lines += ["", "| Asset | SHA-256 |", "|---|---|"]
    lines += [f"| `{name}` | `{digest}` |" for name, digest in sorted(rel.assets.items())]
    lines += ["", "Verify: `sha256sum -c SHA256SUMS`. Published by `make release`."]
    path = rel.work / "release-notes.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def stage_release(rel: Release, github: GitHub) -> None:
    notes = render_notes(rel)
    names = sorted(rel.assets)
    assets = [rel.assets_dir / name for name in names] + [rel.assets_dir / "SHA256SUMS"]
    github.create_release(rel.tag, notes, assets)
    rel.stages["release"] = {"created": True, "assets": [*names, "SHA256SUMS"]}


def stage_verify(rel: Release, github: GitHub) -> None:
    failures: list[str] = []
    record = github.release(rel.tag)
    if record is None:
        raise Stop(EXIT_VERIFY, "VERIFY_FAILED", f"no Release for {rel.tag} on the host")
    if record.get("draft"):
        failures.append("release is a draft")
    if record.get("tag_name") != rel.tag:
        failures.append(f"release tag_name {record.get('tag_name')!r} != {rel.tag}")
    hosted = sorted(str(a.get("name")) for a in record.get("assets", []) if isinstance(a, dict))
    wanted = sorted([*rel.assets, "SHA256SUMS"])
    if hosted != wanted:
        failures.append(f"release assets {hosted} != {wanted}")
    dest = rel.work / "verify"
    dest.mkdir()
    github.download(rel.tag, dest)
    check = run(["sha256sum", "-c", "SHA256SUMS"], dest, check=False)
    if check.returncode != 0:
        failures.append(f"sha256sum -c failed: {(check.stdout + check.stderr).strip()}")
    if (dest / "SHA256SUMS").read_bytes() != (rel.assets_dir / "SHA256SUMS").read_bytes():
        failures.append("downloaded SHA256SUMS differs from the built one")
    peeled = remote_tags(rel.workspace).get(rel.tag)
    if peeled != rel.commit:
        failures.append(f"remote {rel.tag} peels to {peeled}, not {rel.commit}")
    rel.stages["verify"] = {
        "status": "FAIL" if failures else "PASS",
        "sha256sum_check": check.stdout.strip().splitlines(),
        "tag_peels_to": peeled,
        "release_url": record.get("html_url"),
        "failures": failures,
    }
    if failures:
        raise Stop(EXIT_VERIFY, "VERIFY_FAILED", "; ".join(failures))


# ---------------------------------------------------------------------------
# Receipt + driver
# ---------------------------------------------------------------------------
def write_receipt(workspace: Path, payload: dict[str, Any]) -> Path:
    target = workspace / RECEIPT_REL
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def governance_revision() -> str:
    return git(ROOT, "rev-parse", "HEAD", check=False) or "unknown"


def execute(
    workspace: Path, *, requested: str | None, dry_run: bool, keep_work: bool = False
) -> tuple[int, dict[str, Any]]:
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "workspace": str(workspace),
        "dry_run": dry_run,
        "governance_revision": governance_revision(),
    }
    work = Path(tempfile.mkdtemp(prefix="l9-release-"))
    rel: Release | None = None
    code, status, detail = EXIT_OK, "", ""
    try:
        try:
            declaration = decl.load(workspace)
        except decl.DeclarationError as exc:
            raise Stop(EXIT_DECLARATION, "DECLARATION_INVALID", str(exc)) from exc
        receipt["repository"] = declaration.repository
        github = GitHub(declaration.repository, workspace)
        commit, version, epoch, date, body = stage_preflight(
            workspace, declaration, github, requested
        )
        rel = Release(
            workspace=workspace,
            declaration=declaration,
            commit=commit,
            version=version,
            tag=f"v{version}",
            epoch=epoch,
            dry_run=dry_run,
            notes_body=body,
            changelog_date=date,
            work=work,
        )
        rel.stages["preflight"] = {"status": "PASS", "commit": commit, "version": version}
        stage_gate(rel)
        rel.stages["build_environment"] = build_environment()
        stage_build(rel)
        if dry_run:
            status, detail = "DRY_RUN_PASS", "stopped before publication (DRY_RUN=1)"
        else:
            rel.stages["authorization"] = authorization(rel)
            stage_tag(rel)
            outstanding = stage_major(rel)
            stage_release(rel, github)
            stage_verify(rel, github)
            if outstanding:
                code = EXIT_COMPLETION_REQUIRED
                status = "COMPLETION_REQUIRED"
                detail = (
                    f"released {rel.tag}; major tag needs the operator: {rel.stages['major_tag']}"
                )
            else:
                status, detail = "RELEASED", f"released {rel.tag} at {rel.commit}"
    except Stop as stop:
        code, status, detail = stop.code, stop.status, stop.detail
    finally:
        if rel is not None:
            receipt.update(
                {
                    "version": rel.version,
                    "tag": rel.tag,
                    "commit": rel.commit,
                    "source_date_epoch": rel.epoch,
                    "assets": rel.assets,
                    "stages": rel.stages,
                }
            )
        receipt.update({"status": status, "exit_code": code, "detail": detail})
        if keep_work:
            receipt["work_dir"] = str(work)
        else:
            shutil.rmtree(work, ignore_errors=True)
        receipt["receipt"] = str(write_receipt(workspace, receipt))
    return code, receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Release an L9 repository (make release).")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--version", default="", help="expected X.Y.Z (optional)")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--keep-work", action="store_true", help="keep the build directory")
    args = parser.parse_args(argv)
    workspace = Path(args.workspace).resolve()
    requested = args.version.strip().removeprefix("v") or None
    code, receipt = execute(
        workspace, requested=requested, dry_run=args.dry_run, keep_work=args.keep_work
    )
    print(f"{receipt['status']}: {receipt['detail']}")
    print(f"receipt: {receipt['receipt']}")
    return code


if __name__ == "__main__":
    sys.exit(main())
