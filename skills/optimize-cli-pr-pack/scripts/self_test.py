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
        flagged = {c["symbol"] for c in json.loads(mini_out.stdout)["candidates"]}
        if "dead_symbol" not in flagged or "used_symbol" in flagged:
            raise RuntimeError(f"scanner precision regressed: flagged={flagged}")
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

    print(
        "PASS: identity, adaptive routing, decision ledger, latent wiring, divergence, leverage synthesis, deterministic packaging, and negative self-tests"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
