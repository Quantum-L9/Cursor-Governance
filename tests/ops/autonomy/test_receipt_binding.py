"""receipt_binding is the one owner of canonicalize-then-digest.

Two things are pinned here. The digest primitives behave as the receipt
planes need (content-sensitive, location-sensitive, HEAD-insensitive), and
the one surviving second copy — the portable fallback in the `l9-plan` skill
pack — produces byte-identical output to the library it falls back from.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from ops.autonomy import receipt_binding  # noqa: E402


def _load_plan_validator():
    """Import the skill pack's validator the way the pack is invoked."""
    script = REPO / "skills" / "l9-plan" / "scripts" / "validate_plan_kernel_receipt.py"
    sys.path.insert(0, str(script.parent))
    try:
        spec = importlib.util.spec_from_file_location("_plan_kernel_receipt", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(script.parent))


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "wt"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "a.py").write_text("print(1)\n", encoding="utf-8")
    _git(root, "add", "a.py")
    _git(root, "commit", "-qm", "init")
    return root


def test_canonicalize_zeroes_the_self_referential_digest() -> None:
    text = 'body_sha256: "abc123"\nrest\n'
    out = receipt_binding.canonicalize(text)
    assert receipt_binding.ZERO_DIGEST in out
    assert "abc123" not in out


def test_recording_a_digest_does_not_change_the_digest() -> None:
    """The property the zeroing exists for: a plan can carry its own hash.

    Recording is a fixed point. Compute against a placeholder, write the
    result back over it, and recomputing yields the same value — which is
    what lets a verifier re-derive rather than trust the recorded field.
    """
    placeholder = f'body_sha256: "{"f" * 64}"\nbody\n'
    first = receipt_binding.canonical_sha256(placeholder)
    recorded = f'body_sha256: "{first}"\nbody\n'
    assert receipt_binding.canonical_sha256(recorded) == first


def test_canonical_sha256_still_tracks_real_edits() -> None:
    a = f'body_sha256: "{"f" * 64}"\nbody\n'
    b = f'body_sha256: "{"f" * 64}"\nbody edited\n'
    assert receipt_binding.canonical_sha256(a) != receipt_binding.canonical_sha256(b)


def test_skill_pack_fallback_matches_the_library() -> None:
    """The pack keeps a local copy for consumer repos. It may not drift."""
    module = _load_plan_validator()
    samples = [
        'body_sha256: "deadbeef"\nbody\n',
        "body_sha256: deadbeef\nbody\n",
        "no digest field here\n",
        'a: 1\nbody_sha256: "x"\nb: 2\nbody_sha256: "y"\n',
    ]
    for text in samples:
        expected = receipt_binding.canonicalize(text, self_fields=("body_sha256",))
        # The library path, as the governance clone runs it.
        assert module.canonicalize(text) == expected
        # The portable path, as a consumer clone without ops/ runs it.
        bare = module.SHA_FIELD_RE.sub(
            lambda m: f"{m.group(1)}{receipt_binding.ZERO_DIGEST}{m.group(3)}", text
        )
        assert bare == expected


def test_sha256_file_is_exact_bytes_not_canonicalized(tmp_path: Path) -> None:
    path = tmp_path / "r.md"
    path.write_text("x\n", encoding="utf-8")
    first = receipt_binding.sha256_file(path)
    path.write_text("x \n", encoding="utf-8")
    assert receipt_binding.sha256_file(path) != first


def test_tree_digest_survives_a_no_op_commit(repo: Path) -> None:
    """The defect the L4 content binding closes: HEAD moved, tree did not."""
    before = receipt_binding.tree_digest(repo)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "no-op")
    assert receipt_binding.tree_digest(repo) == before


def test_tree_digest_moves_on_a_content_change(repo: Path) -> None:
    before = receipt_binding.tree_digest(repo)
    (repo / "a.py").write_text("print(2)\n", encoding="utf-8")
    assert receipt_binding.tree_digest(repo) != before


def test_tree_digest_moves_on_a_rename_that_preserves_content(repo: Path) -> None:
    before = receipt_binding.tree_digest(repo)
    _git(repo, "mv", "a.py", "b.py")
    assert receipt_binding.tree_digest(repo) != before


def test_tree_digest_sees_an_untracked_file(repo: Path) -> None:
    before = receipt_binding.tree_digest(repo)
    (repo / "new.py").write_text("print(3)\n", encoding="utf-8")
    assert receipt_binding.tree_digest(repo) != before


def test_tree_digest_ignores_the_receipt_directory(repo: Path) -> None:
    """Recording a receipt must not perturb the digest the receipt contains.

    This fixture has no `.gitignore` on purpose: the exclusion has to hold on
    its own, or an attestation is stale the instant it is written in any
    workspace whose ignore rules are not wired yet.
    """
    before = receipt_binding.tree_digest(repo)
    receipts = repo / ".l9" / "autonomy"
    receipts.mkdir(parents=True)
    (receipts / "l4-release-receipt.json").write_text("{}", encoding="utf-8")
    assert receipt_binding.tree_digest(repo) == before


def test_tree_digest_notices_a_deletion(repo: Path) -> None:
    before = receipt_binding.tree_digest(repo)
    (repo / "a.py").unlink()
    assert receipt_binding.tree_digest(repo) != before


def test_tree_digest_refuses_a_non_repository(tmp_path: Path) -> None:
    """No constant fallback: one receipt must not authorize every unreadable tree."""
    with pytest.raises(RuntimeError):
        receipt_binding.tree_digest(tmp_path / "nope")


def test_module_writes_no_receipt_and_decides_no_policy() -> None:
    """Library only (CANONICAL_LAW §6.2.9 item 1): no writer, no verdict."""
    source = (REPO / "ops" / "autonomy" / "receipt_binding.py").read_text(encoding="utf-8")
    for forbidden in ("write_text", "write_bytes", "json.dump", "receipt_path", "RECEIPT_REL"):
        assert forbidden not in source, f"receipt_binding must not reference {forbidden}"


def test_callers_prefer_in_repo_receipt_binding() -> None:
    """Bare `receipt_binding` on sys.path is a third-party module, not ours."""
    for rel in ("ops/autonomy/l4_local.py", "ops/autonomy/kernel_predicates.py"):
        src = (REPO / rel).read_text(encoding="utf-8")
        in_repo = src.index("from ops.autonomy.receipt_binding import")
        local = src.index("from receipt_binding import")
        assert in_repo < local, rel


def test_skill_pack_loads_binding_by_file_location() -> None:
    src = (REPO / "skills" / "l9-plan" / "scripts" / "validate_plan_kernel_receipt.py").read_text(
        encoding="utf-8"
    )
    assert "spec_from_file_location" in src
    assert "from ops.autonomy import receipt_binding" not in src


def test_skill_pack_ignores_a_sys_path_ops_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fake_root = tmp_path / "site"
    fake_ops = fake_root / "ops" / "autonomy"
    fake_ops.mkdir(parents=True)
    (fake_root / "ops" / "__init__.py").write_text("", encoding="utf-8")
    (fake_ops / "__init__.py").write_text("", encoding="utf-8")
    (fake_ops / "receipt_binding.py").write_text(
        "def canonicalize(text, self_fields=None):\n    return 'FAKE'\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(fake_root))
    module = _load_plan_validator()
    text = 'body_sha256: "deadbeef"\nbody\n'
    expected = receipt_binding.canonicalize(text, self_fields=("body_sha256",))
    assert module.canonicalize(text) == expected
    assert module.canonicalize(text) != "FAKE"


def test_tree_digest_moves_when_tracked_file_becomes_untracked(repo: Path) -> None:
    """git rm --cached leaves the bytes; membership must still move the digest."""
    before = receipt_binding.tree_digest(repo)
    _git(repo, "rm", "--cached", "-q", "a.py")
    assert (repo / "a.py").is_file()
    assert receipt_binding.tree_digest(repo) != before


def test_tree_digest_moves_on_executable_bit(repo: Path) -> None:
    before = receipt_binding.tree_digest(repo)
    path = repo / "a.py"
    path.chmod(path.stat().st_mode | 0o111)
    assert receipt_binding.tree_digest(repo) != before


def test_tree_digest_includes_gitlink_mode(repo: Path) -> None:
    before = receipt_binding.tree_digest(repo)
    sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    _git(repo, "update-index", "--add", "--cacheinfo", f"160000,{sha},vendor/lib")
    assert receipt_binding.tree_digest(repo) != before
