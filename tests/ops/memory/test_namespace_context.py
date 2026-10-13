"""Namespace identity is Cursor's; namespace authorization is not (INV-07/08)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ops.memory import namespace_context as nc

ROOT = Path(__file__).resolve().parents[3]


def test_locate_clone_for_namespace_finds_a_sibling_when_present() -> None:
    found = nc.locate_clone_for_namespace("cursor-governance", from_workspace=ROOT)
    assert found == ROOT
    ceg = nc.locate_clone_for_namespace("cognitive-engine-graphs", from_workspace=ROOT)
    if ceg is not None:
        assert "Cognitive.Engine.Graphs" in ceg.parts or "cognitive-engine-graphs" in ceg.parts


def test_this_checkout_yields_one_write_hint_and_a_read_fan_in() -> None:
    context = nc.resolve_namespace_context(ROOT)
    assert context.write_namespace_hint == "cursor-governance"
    assert context.read_namespace_hints[0] == "cursor-governance"
    assert len(context.read_namespace_hints) >= 1
    assert context.repository_identity == "Quantum-L9/Cursor-Governance"
    assert context.git_root == str(ROOT)
    assert context.as_dict()["authorization"] == "not_decided_here"


def test_explicit_override_is_a_request_not_a_grant(tmp_path: Path) -> None:
    context = nc.resolve_namespace_context(tmp_path, explicit="some-namespace")
    assert context.write_namespace_hint == "some-namespace"
    assert context.method == "explicit_request"
    assert context.explicit_request == "some-namespace"


def test_forbidden_override_yields_no_write_hint() -> None:
    context = nc.resolve_namespace_context(ROOT, explicit="main")
    assert context.write_namespace_hint is None
    assert any("forbidden" in warning for warning in context.warnings)


def test_contradicting_override_yields_no_write_hint() -> None:
    context = nc.resolve_namespace_context(ROOT, explicit="website-bot")
    assert context.write_namespace_hint is None
    assert any("contradicts" in warning for warning in context.warnings)


def test_unknown_repository_has_no_write_hint_but_may_read_workspace(tmp_path: Path) -> None:
    context = nc.resolve_namespace_context(tmp_path)
    assert context.write_namespace_hint is None
    assert context.has_write_hint is False
    assert context.warnings
    # Exactly one write namespace per mutation: none here, never a guess.
    assert "cursor-governance" not in context.read_namespace_hints


def test_repository_identity_comes_from_the_origin_remote(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(tmp_path),
            "remote",
            "add",
            "origin",
            "git@github.com:Quantum-L9/Website-Bot.git",
        ],
        check=True,
    )
    root, identity = nc.repository_identity_for(tmp_path)
    assert root == str(tmp_path.resolve())
    assert identity == "Quantum-L9/Website-Bot"
    context = nc.resolve_namespace_context(tmp_path)
    assert context.write_namespace_hint == "website-bot"


def test_repository_state_digest_is_head(tmp_path: Path) -> None:
    assert nc.repository_state_digest(tmp_path) is None
    head = nc.repository_state_digest(ROOT)
    assert head and len(head) == 40


# ---------------------------------------------------------------------------
# Stage C2 — namespace ownership split (plan §17, §34 "Namespace tests")
# ---------------------------------------------------------------------------


def _registry() -> dict:
    return {
        "schema_version": 3,
        "classification": "namespace_request_hints",
        "shared_read_namespaces": ["l9-workspace"],
        "workspace_group": "igor-workspace",
        "forbidden_groups": ["main", "default", "", "test"],
        "repos": {
            "cursor-governance": {
                "github": "Quantum-L9/Cursor-Governance",
                "remote_patterns": ["*/Cursor-Governance*"],
                "path_hints": ["Cursor-Governance"],
            },
            "pr-repair": {
                "github": "Quantum-L9/l9-pr-repair",
                "github_aliases": ["Quantum-L9/PR_Repair"],
                "remote_patterns": ["*/PR_Repair*", "*/l9-pr-repair*"],
                "path_hints": ["PR_Repair", "l9-pr-repair"],
            },
            "child-repo": {
                "github": "Quantum-L9/child-repo",
                "remote_patterns": ["*/child-repo*"],
                "path_hints": ["child-repo"],
            },
        },
    }


def _git_repo(path: Path, remote: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "remote", "add", "origin", remote], check=True)
    return path


def test_registry_is_classified_as_request_hints_not_grants() -> None:
    registry = nc.load_registry()
    assert registry["classification"] == "namespace_request_hints"
    assert nc.shared_read_namespaces(registry) == ("l9-workspace",)
    # The legacy provider group is never a canonical read request.
    assert "igor-workspace" not in nc.shared_read_namespaces(registry)


def test_single_repository_requests_its_own_namespace_plus_shared_read(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "PR_Repair", "git@github.com:Quantum-L9/PR_Repair.git")
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert context.method == nc.METHOD_REGISTRY
    assert context.write_namespace_hint == "pr-repair"
    assert context.read_namespace_hints == ("pr-repair", "l9-workspace")
    assert context.repository_identity == "Quantum-L9/PR_Repair"
    assert context.parent_git_root is None


def test_repository_alias_resolves_to_the_same_slug(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "renamed", "https://github.com/Quantum-L9/l9-pr-repair.git")
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert context.write_namespace_hint == "pr-repair"
    assert context.aliases == ("Quantum-L9/l9-pr-repair", "Quantum-L9/PR_Repair")


def test_nested_child_repository_is_its_own_identity(tmp_path: Path) -> None:
    parent = _git_repo(
        tmp_path / "Cursor-Governance", "git@github.com:Quantum-L9/Cursor-Governance.git"
    )
    child = _git_repo(parent / "vendor" / "child-repo", "git@github.com:Quantum-L9/child-repo.git")
    context = nc.resolve_namespace_context(child, registry=_registry(), env={})
    assert context.write_namespace_hint == "child-repo"
    assert context.git_root == str(child.resolve())
    assert context.parent_git_root == str(parent.resolve())
    assert "cursor-governance" not in context.read_namespace_hints


def test_write_namespace_is_exactly_one_while_read_may_fan_in(tmp_path: Path) -> None:
    repo = _git_repo(
        tmp_path / "Cursor-Governance", "git@github.com:Quantum-L9/Cursor-Governance.git"
    )
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert context.write_namespace_hint == "cursor-governance"
    assert len(context.read_namespace_hints) == 2
    assert set(context.read_namespace_hints) > {context.write_namespace_hint}


def test_explicit_request_is_recorded_and_forwarded_without_a_grant(tmp_path: Path) -> None:
    context = nc.resolve_namespace_context(
        tmp_path, registry=_registry(), env={nc.ENV_NAMESPACE_REQUEST: "some-namespace"}
    )
    assert context.method == nc.METHOD_EXPLICIT
    assert context.explicit_request == "some-namespace"
    assert context.write_namespace_hint == "some-namespace"
    assert context.as_dict()["authorization"] == "not_decided_here"


def test_explicit_request_contradicting_identity_is_not_forwarded_as_write(tmp_path: Path) -> None:
    repo = _git_repo(
        tmp_path / "Cursor-Governance", "git@github.com:Quantum-L9/Cursor-Governance.git"
    )
    context = nc.resolve_namespace_context(repo, explicit="pr-repair", registry=_registry(), env={})
    assert context.method == nc.METHOD_EXPLICIT
    assert context.write_namespace_hint is None
    assert context.explicit_request == "pr-repair"
    assert context.read_namespace_hints == ("cursor-governance", "l9-workspace")
    assert any("contradicts" in warning for warning in context.warnings)


def test_ambiguous_container_has_no_write_hint_and_names_the_candidates(tmp_path: Path) -> None:
    _git_repo(tmp_path / "Cursor-Governance", "git@github.com:Quantum-L9/Cursor-Governance.git")
    _git_repo(tmp_path / "PR_Repair", "git@github.com:Quantum-L9/PR_Repair.git")
    context = nc.resolve_namespace_context(tmp_path, registry=_registry(), env={})
    assert context.method == nc.METHOD_AMBIGUOUS
    assert context.write_namespace_hint is None
    assert context.candidates == ("cursor-governance", "pr-repair")
    # An ambiguous container requests no repository namespace, only the shared read.
    assert context.read_namespace_hints == ("l9-workspace",)


def test_unknown_repository_requests_only_the_shared_read(tmp_path: Path) -> None:
    repo = _git_repo(tmp_path / "mystery", "git@github.com:Someone/mystery.git")
    context = nc.resolve_namespace_context(repo, registry=_registry(), env={})
    assert context.method == nc.METHOD_UNRESOLVED
    assert context.write_namespace_hint is None
    assert context.read_namespace_hints == ("l9-workspace",)
    assert context.repository_identity == "Someone/mystery"


def test_locate_clone_survives_an_unresolvable_start_path(tmp_path: Path) -> None:
    """Path resolution here is best-effort; a bad start must not crash routing.

    The roots loop already skipped a hint whose ``resolve()`` failed, but the
    starting workspace was resolved outside that guard, so a broken link or an
    unreadable parent raised out of write routing instead of degrading to "no
    clone located" — which the caller already handles by staying put.

    A symlink loop is the canonical case and is *not* an OSError on CPython
    3.12; it surfaces as RuntimeError, which is why the guard covers both.
    """
    loop_a = tmp_path / "loop-a"
    loop_b = tmp_path / "loop-b"
    loop_a.symlink_to(loop_b)
    loop_b.symlink_to(loop_a)

    assert nc.locate_clone_for_namespace("cursor-governance", from_workspace=loop_a) is None

    # A path whose components simply do not exist resolves without raising, and
    # must also come back as "not located" rather than a false positive.
    missing = tmp_path / "absent" / "deeper"
    assert nc.locate_clone_for_namespace("cursor-governance", from_workspace=missing) is None


# --- RECON-0 allowlist (2026-10-12): the same 31 slugs Memory registers --------

RECON_0_NAMESPACES = {
    "Quantum-L9/.github": "quantum-l9-github",
    "Quantum-L9/Cognitive.Engine.Graphs": "cognitive-engine-graphs",
    "Quantum-L9/Constellation.Gate": "constellation-gate",
    "Quantum-L9/Cursor-Governance": "cursor-governance",
    "Quantum-L9/Enrichment.Inference.Engine": "enrichment-inference-engine",
    "Quantum-L9/Gate_SDK": "gate-sdk",
    "Quantum-L9/IdeaOS": "ideaos",
    "Quantum-L9/SEO-Bot": "seo-bot",
    "Quantum-L9/SplitWisely.ai": "splitwisely-ai",
    "Quantum-L9/Website-Bot": "website-bot",
    "Quantum-L9/l9-assurance": "l9-assurance",
    "Quantum-L9/l9-campaign-execution": "l9-campaign-execution",
    "Quantum-L9/l9-ci-core": "l9-ci-core",
    "Quantum-L9/l9-ci-debt-intelligence": "l9-ci-debt-intelligence",
    "Quantum-L9/l9-ci-debt-lsp": "l9-ci-debt-lsp",
    "Quantum-L9/l9-ci-debt-resolver": "l9-ci-debt-resolver",
    "Quantum-L9/l9-ci-sdk": "l9-ci-sdk",
    "Quantum-L9/l9-cognitive-runtime": "l9-cognitive-runtime",
    "Quantum-L9/l9-constellation-topology": "l9-constellation-topology",
    "Quantum-L9/l9-graphiti-memory": "l9-graphiti-memory",
    "Quantum-L9/l9-harness": "l9-harness",
    "Quantum-L9/l9-learning-foundry": "l9-learning-foundry",
    "Quantum-L9/l9-meta-injector": "l9-meta-injector",
    "Quantum-L9/l9-observability-core": "l9-observability-core",
    "Quantum-L9/l9-pr-repair": "pr-repair",
    "Quantum-L9/l9-repo-template": "l9-repo-template",
    "Quantum-L9/l9-revops": "l9-revops",
    "Quantum-L9/l9-semantic-compiler-engine": "l9-semantic-compiler-engine",
    "Quantum-L9/l9-state": "l9-state",
    "Quantum-L9/l9-wip": "l9-wip",
    "cryptoxdog/IB-Odoo_19": "ib-odoo-19",
}


def _remote_forms(owner_repo: str) -> list[str]:
    return [
        f"https://github.com/{owner_repo}",
        f"https://github.com/{owner_repo}.git",
        f"git@github.com:{owner_repo}.git",
        f"ssh://git@github.com/{owner_repo}.git",
        f"http://local_proxy@127.0.0.1:8080/git/{owner_repo}",
    ]


def test_recon_allowlist_maps_one_to_one_onto_the_hint_registry() -> None:
    repos = nc.load_registry()["repos"]
    by_github: dict[str, list[str]] = {}
    for slug, entry in repos.items():
        by_github.setdefault(entry["github"], []).append(slug)
    for owner_repo, slug in RECON_0_NAMESPACES.items():
        assert by_github.get(owner_repo) == [slug], owner_repo


def test_every_recon_remote_form_hints_its_own_slug(tmp_path: Path) -> None:
    registry = nc.load_registry()
    for index, (owner_repo, slug) in enumerate(sorted(RECON_0_NAMESPACES.items())):
        name = owner_repo.split("/", 1)[1]
        for form, remote in enumerate(_remote_forms(owner_repo)):
            repo = _git_repo(tmp_path / f"r{index:02d}f{form}" / name, remote)
            context = nc.resolve_namespace_context(repo, registry=registry, env={})
            assert context.write_namespace_hint == slug, (remote, context.candidates)
            assert context.as_dict()["authorization"] == "not_decided_here"


def test_a_nested_dot_github_directory_is_not_the_dot_github_repository(tmp_path: Path) -> None:
    registry = nc.load_registry()
    seo = _git_repo(tmp_path / "SEO-Bot", "https://github.com/Quantum-L9/SEO-Bot.git")
    nested = seo / ".github" / "workflows"
    nested.mkdir(parents=True)
    assert nc.match_registry_slugs(registry, remote=None, path_parts=set(nested.parts)) != [
        "quantum-l9-github"
    ]
    assert nc.resolve_namespace_context(nested, registry=registry, env={}).write_namespace_hint == (
        "seo-bot"
    )
    orphan = tmp_path / "plain" / ".github" / "workflows"
    orphan.mkdir(parents=True)
    unresolved = nc.resolve_namespace_context(orphan, registry=registry, env={})
    assert unresolved.write_namespace_hint is None
    real = _git_repo(tmp_path / ".github", "https://github.com/Quantum-L9/.github")
    assert nc.resolve_namespace_context(real, registry=registry, env={}).write_namespace_hint == (
        "quantum-l9-github"
    )


def test_lookalike_remotes_do_not_borrow_a_new_recon_slug(tmp_path: Path) -> None:
    registry = nc.load_registry()
    new_slugs = {
        "quantum-l9-github",
        "ideaos",
        "l9-campaign-execution",
        "l9-learning-foundry",
        "l9-observability-core",
        "l9-revops",
        "l9-semantic-compiler-engine",
        "l9-state",
        "l9-wip",
    }
    for index, remote in enumerate(
        (
            "https://github.com/someone-else/.github",
            "https://github.com/Quantum-L9/.github-mirror",
            "https://github.com/Quantum-L9/l9-state-machine",
            "https://github.com/Quantum-L9/IdeaOS-2.git",
            "git@github.com:not-Quantum-L9/l9-revops.git",
            "https://github.com/Quantum-L9/l9-wip2",
        )
    ):
        repo = _git_repo(tmp_path / f"neutral{index}", remote)
        matches = nc.match_registry_slugs(
            registry, remote=nc.git_remote_url(repo), path_parts=set(repo.parts)
        )
        assert not set(matches) & new_slugs, (remote, matches)
