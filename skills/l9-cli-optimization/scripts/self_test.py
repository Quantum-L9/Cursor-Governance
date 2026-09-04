#!/usr/bin/env python3
"""Run end-to-end, deterministic, anti-drift, and negative tests."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(
    command: list[str],
    cwd: Path | None = None,
    *,
    env: dict[str, str] | None = None,
    expected_codes: set[int] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=cwd, text=True, capture_output=True, check=False, env=env)
    if result.returncode not in (expected_codes or {0}):
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def build_spec() -> dict[str, object]:
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "assets" / "pack-spec.example.json").read_text(encoding="utf-8"))


def main() -> int:
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"  # keep the run cache-free (M6 guard)
    sys.dont_write_bytecode = True
    for cache in Path(__file__).resolve().parents[1].rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)  # robust to prior direct-invocation caches
    scripts = Path(__file__).resolve().parent
    # Canonical validator set. self_test IS the aggregate gate; SKILL.md's
    # "## Validation" block must list exactly these (parity checked below).
    standalone = [
        "validate_identity_lock.py",
        "validate_activation_model.py",
        "validate_latent_capability_integration.py",
        "validate_revision_synthesis.py",
        "validate_decision_ledger.py",
        "validate_adaptive_reasoning.py",
        "validate_exemplary_skill.py",
    ]
    for name in standalone:
        args = [sys.executable, str(scripts / name)]
        if name == "validate_exemplary_skill.py":
            args.append(str(scripts.parent))
        run(args)

    # Defect D: SKILL.md's documented validation list must match what runs here
    # (the standalone validators plus the pack build/validate exercised below).
    import re as _re

    skill_text = (scripts.parent / "SKILL.md").read_text(encoding="utf-8")
    if "## Validation" not in skill_text:
        raise RuntimeError("SKILL.md is missing the ## Validation heading")
    gate_section = skill_text.split("## Validation", 1)[-1].split(chr(10) + "## ", 1)[
        0
    ]  # stop before next H2 (excludes Resource Map)
    fenced = chr(10).join(_re.findall(r"```bash\n(.*?)```", gate_section, _re.DOTALL))
    listed = set(_re.findall(r"scripts/(\w+\.py)", fenced))
    invoked = set(standalone) | {
        "build_commit_pack.py",
        "validate_commit_pack.py",
        "scan_capabilities.py",
        "measure.py",
        "self_test.py",
        "flag_inventory.py",
        "full_throttle.py",
        "build_flag_activation_pack.py",
    }
    if listed != invoked:
        raise RuntimeError(
            "SKILL.md ## Validation script list is not in parity with self_test; "
            "only_listed="
            + str(sorted(listed - invoked))
            + ", only_invoked="
            + str(sorted(invoked - listed))
        )

    # Defect A: the README/checklist/manifest render must tolerate present-null
    # wiring (JSON null decodes to None; `.get(...)` used to crash). Exercise the
    # two render sites directly with wiring == None.
    import importlib.util

    bcp_spec = importlib.util.spec_from_file_location("bcp", str(scripts / "build_commit_pack.py"))
    bcp = importlib.util.module_from_spec(bcp_spec)
    bcp_spec.loader.exec_module(bcp)
    null_probe = {
        "pack_name": "probe",
        "status": "PR_READY",
        "repository": "r",
        "base_ref": "b",
        "branch": "br",
        "summary": "s",
        "optimization": {"utilization_gap_class": "artificial_delay"},
        "performance": {"improvement_percent": 10.0},
        "wiring": None,
    }
    bcp.render_readme(null_probe)
    bcp.render_pr_checklist(null_probe)
    with tempfile.TemporaryDirectory(prefix="optimize-cli-pack-test-") as raw:
        temp = Path(raw)
        repo = temp / "repo"
        out = temp / "out"
        repo.mkdir()
        run(["git", "init", "-q"], repo)
        run(["git", "config", "user.name", "Skill Test"], repo)
        run(["git", "config", "user.email", "skill-test@example.invalid"], repo)
        (repo / "README.md").write_text("# Fixture\n", encoding="utf-8")
        (repo / "runner.py").write_text(
            "#!/usr/bin/env python3\nimport argparse\nfrom concurrent.futures import ThreadPoolExecutor\n"
            "def serial_count(tasks): return sum(1 for _ in range(tasks))\n"
            "def parallel_count(tasks, workers):\n"
            "    with ThreadPoolExecutor(max_workers=workers) as pool:\n"
            "        return sum(pool.map(lambda _: 1, range(tasks)))\n"
            "p=argparse.ArgumentParser()\np.add_argument('--tasks', type=int, required=True)\n"
            "p.add_argument('--workers', type=int, default=1)\na=p.parse_args()\n"
            "if a.tasks < 0 or not 1 <= a.workers <= 4: raise SystemExit(2)\n"
            "print(serial_count(a.tasks))\n",
            encoding="utf-8",
        )
        run(["git", "add", "README.md", "runner.py"], repo)
        run(["git", "commit", "-q", "-m", "Initialize serial fixture"], repo)
        run(["git", "branch", "-M", "main"], repo)

        (repo / "README.md").write_text(
            "# Fixture\n\nBounded parallel workers are supported.\n", encoding="utf-8"
        )
        (repo / "runner.py").write_text(
            "#!/usr/bin/env python3\nimport argparse\nfrom concurrent.futures import ThreadPoolExecutor\n"
            "def serial_count(tasks): return sum(1 for _ in range(tasks))\n"
            "def parallel_count(tasks, workers):\n"
            "    with ThreadPoolExecutor(max_workers=workers) as pool:\n"
            "        return sum(pool.map(lambda _: 1, range(tasks)))\n"
            "p=argparse.ArgumentParser()\np.add_argument('--tasks', type=int, required=True)\n"
            "p.add_argument('--workers', type=int, default=1)\na=p.parse_args()\n"
            "if a.tasks < 0 or not 1 <= a.workers <= 4: raise SystemExit(2)\n"
            "print(parallel_count(a.tasks, a.workers) if a.workers > 1 else serial_count(a.tasks))\n",
            encoding="utf-8",
        )

        spec = build_spec()
        spec_path = temp / "spec.json"
        spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
        command = [
            sys.executable,
            str(scripts / "build_commit_pack.py"),
            "--spec",
            str(spec_path),
            "--repo-root",
            str(repo),
            "--output",
            str(out),
        ]
        env = dict(os.environ, SOURCE_DATE_EPOCH="1785283200")
        run(command, env=env)
        pack_root = out / str(spec["pack_name"])
        run([sys.executable, str(scripts / "validate_commit_pack.py"), str(pack_root)])

        # K4: give the pack validator teeth — mutate a VALID pack and assert the
        # validator (not the builder) rejects it (regression net for K2/H1/H2/M1).
        def expect_pack_rejected(label, mutate):
            m = temp / ("mutant-" + label)
            if m.exists():
                shutil.rmtree(m)
            shutil.copytree(pack_root, m)
            mutate(m)
            r = subprocess.run(
                [sys.executable, str(scripts / "validate_commit_pack.py"), str(m)],
                text=True,
                capture_output=True,
            )
            if r.returncode == 0:
                raise RuntimeError(
                    "validate_commit_pack accepted a corrupted pack: " + label + " :: " + r.stdout
                )

        def _mut_checksum(m):
            readme = m / "README.md"
            readme.write_text(readme.read_text() + " tampered ", encoding="utf-8")

        def _mut_drop_file(m):
            (m / "pr" / "PR_BODY.md").unlink()

        def _mut_garble_patch(m):
            (m / "change" / "commit.patch").write_bytes(b"not a real patch")

        def _mut_candidate_worse(m):
            man = json.loads((m / "MANIFEST.json").read_text())
            man["performance"]["candidate_value"] = 1
            (m / "MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")

        def _mut_patch_wrong_content(m):
            import hashlib as _h

            fake = b"diff --git a/nonexistent.txt b/nonexistent.txt"
            (m / "change" / "commit.patch").write_bytes(fake)
            man = json.loads((m / "MANIFEST.json").read_text())
            man["patch_sha256"] = _h.sha256(
                fake
            ).hexdigest()  # sha now matches -> H1 path check must catch it
            (m / "MANIFEST.json").write_text(json.dumps(man, indent=2), encoding="utf-8")

        def _mut_failed_command(m):
            cf = m / "evidence" / "commands.jsonl"
            recs = [json.loads(line) for line in cf.read_text().splitlines() if line.strip()]
            recs[0]["status"] = "failed"
            cf.write_text("".join(json.dumps(r) + chr(10) for r in recs), encoding="utf-8")

        def _mut_unknown_owner(m):
            # P0-2: an unresolved divergence with owner "unknown" must be
            # rejected by the standalone validator, matching the builder.
            p = m / "evidence" / "CLI_REVISION_SYNTHESIS.json"
            obj = json.loads(p.read_text())
            changed = False
            for f in obj["findings"]:
                if f.get("kind") == "docs_code_divergence":
                    f["owner"] = "unknown"
                    changed = True
            if not changed:
                raise RuntimeError("fixture has no divergence finding to mutate")
            p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

        def _mut_underdeclared_route(m):
            # Remove PO-REACHABILITY from BOTH route and ledger (keeps them matched
            # to each other) — M1 must still catch it via content binding (the
            # example is a latent-capability pack that requires reachability).
            for rel in ("evidence/EXECUTION_ROUTE.json", "evidence/DECISION_LEDGER.json"):
                obj = json.loads((m / rel).read_text())
                obj["proof_obligations"] = [
                    o for o in obj["proof_obligations"] if o.get("id") != "PO-REACHABILITY"
                ]
                if "required_adapters" in obj:
                    obj["required_adapters"] = [
                        a for a in obj["required_adapters"] if a != "latent_capability_reachability"
                    ]
                (m / rel).write_text(json.dumps(obj, indent=2), encoding="utf-8")

        for label, mut in [
            ("underdeclared-route", _mut_underdeclared_route),
            ("unknown-divergence-owner", _mut_unknown_owner),
            ("checksum-tamper", _mut_checksum),
            ("dropped-file", _mut_drop_file),
            ("garbled-patch", _mut_garble_patch),
            ("candidate-worse", _mut_candidate_worse),
            ("patch-wrong-content", _mut_patch_wrong_content),
            ("failed-command", _mut_failed_command),
        ]:
            expect_pack_rejected(label, mut)
        archive = out / f"{spec['pack_name']}.tar.gz"
        first = hashlib.sha256(archive.read_bytes()).hexdigest()
        run(command, env=env)
        second = hashlib.sha256(archive.read_bytes()).hexdigest()
        if first != second:
            raise RuntimeError("archive is not deterministic for identical inputs")

        blocked = build_spec()
        blocked["status"] = "BLOCKED"
        blocked["issues"] = []
        blocked_path = temp / "blocked.json"
        blocked_path.write_text(json.dumps(blocked), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(blocked_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        external = build_spec()
        external["optimization"]["ownership"] = "external"  # type: ignore[index]
        external_path = temp / "external.json"
        external_path.write_text(json.dumps(external), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(external_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        unsafe = build_spec()
        unsafe["changed_files"] = ["../outside"]
        unsafe_path = temp / "unsafe.json"
        unsafe_path.write_text(json.dumps(unsafe), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(unsafe_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        missing_wiring = build_spec()
        missing_wiring.pop("wiring", None)
        missing_wiring_path = temp / "missing-wiring.json"
        missing_wiring_path.write_text(json.dumps(missing_wiring), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(missing_wiring_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        unknown_wiring = build_spec()
        unknown_wiring["wiring"]["findings"][0]["consumer_evidence"] = "UNKNOWN"  # type: ignore[index]
        unknown_wiring_path = temp / "unknown-wiring.json"
        unknown_wiring_path.write_text(json.dumps(unknown_wiring), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(unknown_wiring_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        staged_rollout = build_spec()
        staged_rollout["wiring"]["findings"][0]["dormant_by_design"] = True  # type: ignore[index]
        staged_rollout_path = temp / "staged-rollout.json"
        staged_rollout_path.write_text(json.dumps(staged_rollout), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(staged_rollout_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        missing_synthesis = build_spec()
        missing_synthesis.pop("revision_synthesis", None)
        missing_synthesis_path = temp / "missing-synthesis.json"
        missing_synthesis_path.write_text(json.dumps(missing_synthesis), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(missing_synthesis_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        bad_score = build_spec()
        bad_score["revision_synthesis"]["options"][0]["leverage_score"] = 1.0  # type: ignore[index]
        bad_score_path = temp / "bad-leverage-score.json"
        bad_score_path.write_text(json.dumps(bad_score), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(bad_score_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        omitted_divergence = build_spec()
        omitted_divergence["revision_synthesis"]["unresolved_divergence_ids"] = []  # type: ignore[index]
        omitted_divergence_path = temp / "omitted-divergence.json"
        omitted_divergence_path.write_text(json.dumps(omitted_divergence), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(omitted_divergence_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        blocking_divergence = build_spec()
        divergence = blocking_divergence["revision_synthesis"]["findings"][1]  # type: ignore[index]
        divergence["blocks_release"] = True
        divergence["status"] = "open"
        blocking_divergence_path = temp / "blocking-divergence.json"
        blocking_divergence_path.write_text(json.dumps(blocking_divergence), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(blocking_divergence_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        missing_route = build_spec()
        missing_route.pop("execution_route", None)
        missing_route_path = temp / "missing-route.json"
        missing_route_path.write_text(json.dumps(missing_route), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(missing_route_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        pending_proof = build_spec()
        pending_proof["decision_ledger"]["proof_obligations"][0]["status"] = "pending"  # type: ignore[index]
        pending_proof["decision_ledger"]["proof_obligations"][0]["evidence"] = []  # type: ignore[index]
        pending_proof_path = temp / "pending-proof.json"
        pending_proof_path.write_text(json.dumps(pending_proof), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(pending_proof_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        selection_mismatch = build_spec()
        selection_mismatch["decision_ledger"]["selected_option_ids"] = ["CLI-OPT-002"]  # type: ignore[index]
        selection_mismatch["decision_ledger"]["options"][0]["disposition"] = "deferred"  # type: ignore[index]
        selection_mismatch["decision_ledger"]["options"][1]["disposition"] = "selected"  # type: ignore[index]
        selection_mismatch_path = temp / "selection-mismatch.json"
        selection_mismatch_path.write_text(json.dumps(selection_mismatch), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(selection_mismatch_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        material_unknown = build_spec()
        material_unknown["decision_ledger"]["unknowns"].append(
            {  # type: ignore[index]
                "id": "UNK-002",
                "description": "Unresolved release safety",
                "material": True,
                "disposition": "block",
                "evidence": [],
            }
        )
        material_unknown["decision_ledger"]["convergence"]["remaining_material_unknown_ids"] = [
            "UNK-002"
        ]  # type: ignore[index]
        material_unknown_path = temp / "material-unknown.json"
        material_unknown_path.write_text(json.dumps(material_unknown), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(material_unknown_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        # Diagnosis tooling smoke (defect E): scanner emits JSON candidates +
        # entrypoints for a real repo; measure emits a proof block.
        scan_out = run([sys.executable, str(scripts / "scan_capabilities.py"), str(repo)])
        scan = json.loads(scan_out.stdout)
        if "candidates" not in scan or "entrypoints" not in scan:
            raise RuntimeError("scan_capabilities did not emit candidates/entrypoints")
        # L5: a real precision check — a dead symbol is flagged, a referenced one is not.
        mini = temp / "miniscan"
        mini.mkdir()
        (mini / "a.py").write_text(
            "def dead_symbol():\n    return 1\ndef used_symbol():\n    return 2\n", encoding="utf-8"
        )
        (mini / "b.py").write_text(
            "from a import used_symbol\nprint(used_symbol())\n", encoding="utf-8"
        )
        mini_out = run([sys.executable, str(scripts / "scan_capabilities.py"), str(mini)])
        mini_scan = json.loads(mini_out.stdout)
        flagged = {c["symbol"] for c in mini_scan["candidates"]}
        if "dead_symbol" not in flagged or "used_symbol" in flagged:
            raise RuntimeError(f"scanner precision regressed: flagged={flagged}")
        # P2-2: every candidate is ranked (numeric score, non-increasing order).
        scores = [c.get("score") for c in mini_scan["candidates"]]
        if not all(isinstance(s, (int, float)) for s in scores) or scores != sorted(
            scores, reverse=True
        ):
            raise RuntimeError(f"scanner candidates are not ranked by score: {scores}")

        # P2-1/P2-3: framework suppression (entry_points, Alembic) + twin visibility.
        mini2 = temp / "miniscan2"
        (mini2 / "versions").mkdir(parents=True)
        (mini2 / "a.py").write_text(
            "def dead_symbol():\n    return 1\n"
            "def cli_entry():\n    return 2\n"
            "def twinned():\n    return 3\n",
            encoding="utf-8",
        )
        (mini2 / "b.py").write_text("def twinned():\n    return 9\n", encoding="utf-8")
        (mini2 / "versions" / "0001_m.py").write_text(
            "def upgrade():\n    pass\ndef downgrade():\n    pass\n", encoding="utf-8"
        )
        (mini2 / "pyproject.toml").write_text(
            '[project.scripts]\nmytool = "a:cli_entry"\n', encoding="utf-8"
        )
        # OBS-002: staged-rollout intent. kge_enabled is named beside a staged
        # marker in system-state.md -> do_not_activate; debug_enabled is a plain
        # off-by-default flag with no intent signal.
        (mini2 / "config.py").write_text(
            "kge_enabled = False\ndebug_enabled = False\n", encoding="utf-8"
        )
        (mini2 / "system-state.md").write_text(
            "| System | Flag | Activation |\n| KGE | kge_enabled=False | Wave 6 merge |\n",
            encoding="utf-8",
        )
        mini2_scan = json.loads(
            run([sys.executable, str(scripts / "scan_capabilities.py"), str(mini2)]).stdout
        )
        by_symbol = {c["symbol"]: c for c in mini2_scan["candidates"]}
        if by_symbol.get("kge_enabled", {}).get("recommended_verdict") != "do_not_activate":
            raise RuntimeError("scanner did not flag staged-rollout flag as do_not_activate")
        if by_symbol.get("debug_enabled", {}).get("recommended_verdict") == "do_not_activate":
            raise RuntimeError(
                "scanner over-flagged a plain off-by-default flag as do_not_activate"
            )
        flagged2 = {c["symbol"] for c in mini2_scan["candidates"]}
        if "cli_entry" in flagged2:
            raise RuntimeError("scanner did not suppress a setuptools entry_point target")
        if {"upgrade", "downgrade"} & flagged2:
            raise RuntimeError("scanner did not suppress Alembic upgrade/downgrade")
        if "dead_symbol" not in flagged2:
            raise RuntimeError("scanner over-suppressed a genuinely dead symbol")
        if "twinned" not in {t["symbol"] for t in mini2_scan["duplicate_twins"]}:
            raise RuntimeError("scanner did not surface a same-name twin in duplicate_twins")
        twin_cands = [c for c in mini2_scan["candidates"] if c["symbol"] == "twinned"]
        if not twin_cands or not all(c.get("twin_definitions") for c in twin_cands):
            raise RuntimeError("twin candidates lack twin_definitions annotation")

        # OBS-third-run: comprehensive-sweep detectors — unwired executables
        # (incl. the `python -m pkg.mod` guard), phantom/archived imports, scratch
        # exclusion, and syntax-broken files. Regression net for the deep scan.
        mini3 = temp / "miniscan3"
        (mini3 / "pkg").mkdir(parents=True)
        (mini3 / "wip").mkdir()
        (mini3 / "_archived").mkdir()
        (mini3 / "tool_unwired.py").write_text(
            "def main():\n    return 1\nif __name__ == '__main__':\n    main()\n", encoding="utf-8"
        )
        (mini3 / "tool_wired.py").write_text(
            "def main():\n    return 2\nif __name__ == '__main__':\n    main()\n", encoding="utf-8"
        )
        (mini3 / "pkg" / "__init__.py").write_text("", encoding="utf-8")
        (mini3 / "pkg" / "runner.py").write_text(
            "def main():\n    return 3\nif __name__ == '__main__':\n    main()\n", encoding="utf-8"
        )
        # tool_wired invoked by filename; pkg.runner invoked via `python -m` dotted path.
        (mini3 / "Makefile").write_text(
            "wired:\n\tpython3 tool_wired.py\nrun:\n\tpython3 -m pkg.runner\n", encoding="utf-8"
        )
        (mini3 / "_archived" / "legacy_mod.py").write_text(
            "def legacy():\n    return 0\n", encoding="utf-8"
        )
        (mini3 / "user.py").write_text(
            "import json\nimport totally_phantom_xyz\nimport legacy_mod\n", encoding="utf-8"
        )
        (mini3 / "wip" / "dead.py").write_text(
            "def wip_only_dead_symbol():\n    return 1\n", encoding="utf-8"
        )
        (mini3 / "broken.py").write_text("def broken(:\n    pass\n", encoding="utf-8")
        m3 = json.loads(
            run([sys.executable, str(scripts / "scan_capabilities.py"), str(mini3)]).stdout
        )
        unwired = {u["path"] for u in m3["unwired_executables"]}
        if "tool_unwired.py" not in unwired:
            raise RuntimeError("scanner missed an unwired executable")
        if "tool_wired.py" in unwired:
            raise RuntimeError("scanner flagged a Makefile-invoked script as unwired")
        if "pkg/runner.py" in unwired:
            raise RuntimeError(
                "scanner flagged a `python -m pkg.runner` script as unwired (F2 regression)"
            )
        if not all(u.get("suggested_wiring") for u in m3["unwired_executables"]):
            raise RuntimeError("unwired executable lacks suggested_wiring")
        dang = {(r["module"], r["reason"]) for r in m3["dangling_references"]}
        if ("totally_phantom_xyz", "unresolved_phantom") not in dang:
            raise RuntimeError("scanner missed a phantom import")
        if ("legacy_mod", "archived_only") not in dang:
            raise RuntimeError("scanner missed an archived-only import")
        if any(r["module"] == "json" for r in m3["dangling_references"]):
            raise RuntimeError("scanner flagged a stdlib import as dangling")
        keys = [(r["path"], r["module"], r["reason"]) for r in m3["dangling_references"]]
        if len(keys) != len(set(keys)):
            raise RuntimeError("dangling_references are not deduplicated")
        if not any(se["path"].endswith("broken.py") for se in m3["syntax_errors"]):
            raise RuntimeError("scanner missed a syntax-broken file")
        if "wip_only_dead_symbol" in {c["symbol"] for c in m3["candidates"]}:
            raise RuntimeError("scanner flagged a candidate inside a scratch (wip/) dir")
        if "candidate_counts_by_class" not in m3:
            raise RuntimeError("scan missing candidate_counts_by_class summary")
        measure_out = run(
            [
                sys.executable,
                str(scripts / "measure.py"),
                "--before",
                f'{sys.executable} -c "pass"',
                "--after",
                f'{sys.executable} -c "pass"',
                "--samples",
                "1",
            ]
        )
        proof = json.loads(measure_out.stdout)
        if "baseline" not in proof or "candidate" not in proof:
            raise RuntimeError("measure did not emit a proof block")

        null_wiring = build_spec()
        null_wiring["wiring"] = None
        null_wiring_path = temp / "null-wiring.json"
        null_wiring_path.write_text(json.dumps(null_wiring), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(null_wiring_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        fourth_cycle = build_spec()
        fourth_cycle["decision_ledger"]["cycle"] = 4  # type: ignore[index]
        fourth_cycle_path = temp / "fourth-cycle.json"
        fourth_cycle_path.write_text(json.dumps(fourth_cycle), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(fourth_cycle_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        # P0-1: a 0->N capability activation (baseline 0, present-null
        # improvement, candidate > 0, higher_is_better) must BUILD — proving the
        # spec schema, validate_spec, and improvement_from_measurements agree.
        activation = build_spec()
        activation["performance"]["baseline"]["value"] = 0  # type: ignore[index]
        activation["performance"]["improvement_percent"] = None  # type: ignore[index]
        activation_path = temp / "activation.json"
        activation_path.write_text(json.dumps(activation), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(activation_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            env=env,
        )

        # OBS-003 / OBS-006: the shipped minimal (throughput, non-latent)
        # template must build+validate and must NOT carry a wiring block.
        minimal_spec = json.loads(
            (scripts.parent / "assets" / "pack-spec.minimal.json").read_text(encoding="utf-8")
        )
        if "wiring" in minimal_spec:
            raise RuntimeError(
                "pack-spec.minimal.json must not include a wiring block (throughput template)"
            )
        minimal_path = temp / "minimal.json"
        minimal_path.write_text(json.dumps(minimal_spec), encoding="utf-8")
        run(
            command[:2]
            + ["--spec", str(minimal_path), "--repo-root", str(repo), "--output", str(out)],
            env=env,
        )
        run(
            [
                sys.executable,
                str(scripts / "validate_commit_pack.py"),
                str(out / str(minimal_spec["pack_name"])),
            ]
        )

        # P0-3: execution_route keeps additionalProperties:false after the
        # classifier-field widening — a genuinely-foreign key is rejected.
        foreign_route = build_spec()
        foreign_route["execution_route"]["not_a_route_field"] = True  # type: ignore[index]
        foreign_route_path = temp / "foreign-route.json"
        foreign_route_path.write_text(json.dumps(foreign_route), encoding="utf-8")
        run(
            [
                sys.executable,
                str(scripts / "build_commit_pack.py"),
                "--spec",
                str(foreign_route_path),
                "--repo-root",
                str(repo),
                "--output",
                str(out),
            ],
            expected_codes={2},
        )

        # ---- Full-throttle activation mode (flag_inventory / full_throttle /
        # build_flag_activation_pack). Separate self-contained mode; the core
        # dormant_by_design rejection above (staged-rollout spec -> exit 2) is
        # UNCHANGED and still green, proving the core is untouched.
        ft = temp / "ftrepo"
        ft.mkdir()
        run(["git", "init", "-q"], ft)
        run(["git", "config", "user.name", "Skill Test"], ft)
        run(["git", "config", "user.email", "skill-test@example.invalid"], ft)
        (ft / "config.py").write_text(
            "benign_enabled = False\n"  # safe -> flip, stays green
            "breaker_enabled = False\n"  # safe -> flip, but regresses tests -> backed out
            "disable_auth = False\n"  # danger (disables a control) -> never flipped
            "allow_delete = False\n"  # danger (destructive action) -> never flipped
            "use_live_api = False\n"  # danger (live/external) -> never flipped
            "kge_enabled = False\n",  # staged (Wave 6) -> dormant_by_design, held
            encoding="utf-8",
        )
        (ft / "system-state.md").write_text(
            "| KGE | kge_enabled=False | Wave 6 merge |\n", encoding="utf-8"
        )
        # check.py reads BOTH flip flags (attribute access) so the consumer-
        # reachability signal marks them consumer_evidence=found (not needs_wiring)
        # while still failing when breaker is on.
        (ft / "check.py").write_text(
            "import config\n"
            "assert not config.breaker_enabled, 'breaker must stay off'\n"
            "if config.benign_enabled:\n    pass\n"
            "print('ok')\n",
            encoding="utf-8",
        )
        run(["git", "add", "-A"], ft)
        run(["git", "commit", "-q", "-m", "ft fixture"], ft)

        # (a) flag_inventory: polarity-aware classifier is correct on all five cases.
        inv = json.loads(run([sys.executable, str(scripts / "flag_inventory.py"), str(ft)]).stdout)
        cls = {f["flag"]: f["classification"] for f in inv["flags"]}
        expected_cls = {
            "enable_cache": None,
            "benign_enabled": "safe",
            "disable_auth": "danger",
            "allow_delete": "danger",
            "use_live_api": "danger",
            "kge_enabled": "staged",
        }
        for name, want in expected_cls.items():
            if want is None:
                continue
            if cls.get(name) != want:
                raise RuntimeError(
                    f"flag_inventory misclassified {name}: got {cls.get(name)}, want {want}"
                )
        if inv["summary"]["held_danger"] != ["allow_delete", "disable_auth", "use_live_api"]:
            raise RuntimeError(f"danger block-list wrong: {inv['summary']['held_danger']}")

        # (a2) flag_inventory: consumer-reachability + non-runtime/infra precision.
        # Isolated inventory-only fixture (NOT driven by full_throttle apply, so it
        # cannot perturb the activated-set assertions below).
        ftinv = temp / "ftinv"
        (ftinv / "docs").mkdir(parents=True)
        (ftinv / "infra").mkdir()
        (ftinv / "defs.py").write_text(
            "orphan_feature_enabled = False\nused_feature_enabled = False\n", encoding="utf-8"
        )
        (ftinv / "main.py").write_text(
            "from defs import used_feature_enabled\nif used_feature_enabled:\n    print(1)\n",
            encoding="utf-8",
        )
        (ftinv / "consumer.py").write_text("reader = spec.decay_thing_enabled\n", encoding="utf-8")
        (ftinv / "config.yaml").write_text(
            "myblock:\n  decay_thing_enabled: false\n  orphan_thing_enabled: false\n",
            encoding="utf-8",
        )
        (ftinv / "docs" / "dep.yaml").write_text("dep:\n  enabled: false\n", encoding="utf-8")
        (ftinv / "infra" / "values.yaml").write_text(
            "ingress:\n  enabled: false\n", encoding="utf-8"
        )
        (ftinv / "app_config.yaml").write_text("autoscaling:\n  enabled: false\n", encoding="utf-8")
        invx = json.loads(
            run([sys.executable, str(scripts / "flag_inventory.py"), str(ftinv)]).stdout
        )
        by_key = {(f["flag"], f["file"]): f for f in invx["flags"]}

        def _row(flag, file):
            r = by_key.get((flag, file))
            if r is None:
                raise RuntimeError(f"flag_inventory missing {flag} in {file}: {sorted(by_key)}")
            return r

        # consumer found -> stays flip; consumer none -> hold + needs_wiring.
        if _row("used_feature_enabled", "defs.py")["consumer_evidence"] != "found":
            raise RuntimeError("read python flag should be consumer_evidence=found")
        if _row("used_feature_enabled", "defs.py")["decision"] != "flip":
            raise RuntimeError("consumed python flag should stay flip")
        orphan_py = _row("orphan_feature_enabled", "defs.py")
        if (
            orphan_py["consumer_evidence"] != "none"
            or not orphan_py["needs_wiring"]
            or orphan_py["decision"] != "hold"
        ):
            raise RuntimeError(f"unread python flag should be none/needs_wiring/hold: {orphan_py}")
        if _row("decay_thing_enabled", "config.yaml")["consumer_evidence"] != "found":
            raise RuntimeError("config flag read via attribute should be consumer_evidence=found")
        orphan_cfg = _row("orphan_thing_enabled", "config.yaml")
        if orphan_cfg["consumer_evidence"] != "none" or not orphan_cfg["needs_wiring"]:
            raise RuntimeError(
                f"unread distinctive config flag should be none/needs_wiring: {orphan_cfg}"
            )
        if set(invx["summary"]["needs_wiring"]) != {
            "orphan_feature_enabled",
            "orphan_thing_enabled",
        }:
            raise RuntimeError(f"needs_wiring summary wrong: {invx['summary']['needs_wiring']}")
        # non-runtime (docs/ + values.yaml) and infra-block (autoscaling) are held.
        if (
            _row("enabled", "docs/dep.yaml")["scope"] != "non_runtime"
            or _row("enabled", "docs/dep.yaml")["decision"] != "hold"
        ):
            raise RuntimeError("docs/ config flag must be held as non_runtime")
        if _row("enabled", "infra/values.yaml")["scope"] != "non_runtime":
            raise RuntimeError("infra values.yaml flag must be held as non_runtime")
        if (
            _row("enabled", "app_config.yaml")["scope"] != "infra"
            or _row("enabled", "app_config.yaml")["decision"] != "hold"
        ):
            raise RuntimeError("generic enabled under an infra block must be held as infra")

        # (b) full_throttle PLAN: would_flip has the safe flags, never a danger flag.
        plan = json.loads(
            run(
                [sys.executable, str(scripts / "full_throttle.py"), str(ft), "--mode", "plan"]
            ).stdout
        )
        if "benign_enabled" not in plan["would_flip"]:
            raise RuntimeError("full_throttle plan dropped a safe flip candidate")
        if {"disable_auth", "allow_delete", "use_live_api", "kge_enabled"} & set(
            plan["would_flip"]
        ):
            raise RuntimeError(
                f"full_throttle plan would flip an excluded flag: {plan['would_flip']}"
            )

        # (c) full_throttle APPLY: empirical back-out keeps only the proven-safe
        # flag, reverts the breaker, and cleans up its worktree.
        ft_report = temp / "ft-report.json"
        run(
            [
                sys.executable,
                str(scripts / "full_throttle.py"),
                str(ft),
                "--mode",
                "apply",
                "--test-cmd",
                f"{sys.executable} check.py",
                "--output",
                str(ft_report),
            ]
        )
        report = json.loads(ft_report.read_text())
        if report.get("activated_flags") != ["benign_enabled"]:
            raise RuntimeError(
                f"full_throttle activated the wrong set: {report.get('activated_flags')}"
            )
        if "breaker_enabled" not in [b["flag"] for b in report.get("backed_out_flags", [])]:
            raise RuntimeError("full_throttle did not back out the test-breaking flag")
        if not report.get("baseline_test", {}).get("passed"):
            raise RuntimeError("full_throttle baseline should pass with flags off")
        ft_worktrees = ft / ".git" / "worktrees"
        if ft_worktrees.exists() and any(ft_worktrees.iterdir()):
            raise RuntimeError("full_throttle left a git worktree behind")
        if any(run(["git", "status", "--porcelain"], ft).stdout.strip()):
            raise RuntimeError("full_throttle mutated the real working tree")

        # (d) build_flag_activation_pack: review-required pack with a real test
        # delta; patch applies; deterministic; never auto-merge.
        ft_out = temp / "ft-out"
        run(
            [
                sys.executable,
                str(scripts / "build_flag_activation_pack.py"),
                "--report",
                str(ft_report),
                "--repo-root",
                str(ft),
                "--output",
                str(ft_out),
            ],
            env=env,
        )
        ft_pack = ft_out / "full-throttle-ftrepo"
        manifest = json.loads((ft_pack / "MANIFEST.json").read_text())
        if manifest["strategy"] != "full_throttle_flag_activation":
            raise RuntimeError("flag activation pack has the wrong strategy")
        if manifest["status"] != "PR_READY" or manifest["auto_merge"] is not False:
            raise RuntimeError("flag activation pack must be PR_READY and never auto-merge")
        if manifest["activated_flags"] != ["benign_enabled"]:
            raise RuntimeError("flag activation pack activated the wrong flags")
        if not (ft_pack / "evidence" / "FULL_THROTTLE_REPORT.md").is_file():
            raise RuntimeError("flag activation pack missing FULL_THROTTLE_REPORT.md")
        patch = (ft_pack / "change" / "commit.patch").read_text()
        if "benign_enabled = True" not in patch or "breaker_enabled = True" in patch:
            raise RuntimeError("flag activation patch content is wrong")
        run(["git", "apply", "--check", str(ft_pack / "change" / "commit.patch")], ft)
        first_sums = (ft_pack / "SHA256SUMS").read_text()
        run(
            [
                sys.executable,
                str(scripts / "build_flag_activation_pack.py"),
                "--report",
                str(ft_report),
                "--repo-root",
                str(ft),
                "--output",
                str(ft_out),
            ],
            env=env,
        )
        if (ft_pack / "SHA256SUMS").read_text() != first_sums:
            raise RuntimeError("flag activation pack is not deterministic")

    print(
        "PASS: identity, adaptive routing, decision ledger, latent wiring, divergence, leverage synthesis, deterministic packaging, full-throttle activation, and negative self-tests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
