#!/usr/bin/env python3
"""Move remaining built Cursor plans into this BUILT folder."""
from pathlib import Path

SRC = Path("/Users/macm2/.cursor/plans")
DST = SRC / "BUILT"
NAMES = [
    "repair_pr-check_make_pr_gate_aa65140f.plan.md",
    "shared_infisical_llm_fix_b854c4a8.plan.md",
    "redesign_campaign_7_closeout_71746783.plan.md",
    "phase_1_remaining_fixes_164204aa.plan.md",
    "worktree_pr_wiring_354a8940.plan.md",
    "campaign_7_redesign_convergence_0228de4e.plan.md",
    "canonical_toolchain_lock_13ecbe54.plan.md",
    "shared_infisical_llm_fix_09be6003.plan.md",
    "isolate_git_test_fixture_49f9abbb.plan.md",
    "pe_kernel_bind_564db18b.plan.md",
    "pr_remediation_v4_6bfe2a59.plan.md",
    "wire_worktree_on_create_26ad2747.plan.md",
    "pe_campaign_diagnose_8c9b39b5.plan.md",
    "isolate_wiring_campaign_publish_055d9eb3.plan.md",
    "pe_context7_stack_proof_168778d9.plan.md",
    "campaign_brief_ir_ebea99a7.plan.md",
    "make_campaign_front_door_9bf2e436.plan.md",
    "align_checker_pins_a469bf92.plan.md",
    "website-bot-source-first-reconstruction_53b6c5ed.plan.md",
    "rb-hk-001_housekeeping_d6503dcc.plan.md",
    "absorb_key_components_d8a563fe.plan.md",
    "ruff_config_and_plugin_60792a13.plan.md",
    "semgrep_identity_+_global_ruleset_760c8e0b.plan.md",
    "makefile_pre-commit_push_8c8760a9.plan.md",
    "cursor-governance_plugin_unification_bf304b05.plan.md",
    "yaml_governance_port_16b5b746.plan.md",
    "fleet_manifest_auto-fix_4460c795.plan.md",
    "fix_uv.lock_conflict_+_drift-proof_backup_script_6740e79c.plan.md",
    "hetzner_restore_plan_refinement_f1b17d17.plan.md",
    "prelaunch_pr_consolidation_c9c4f347.plan.md",
    "geolocalize_nominatim_throttle_fcbe3b1b.plan.md",
    "semgrep_odoo_rules_overhaul_72eaab2f.plan.md",
    "wire_kernel_and_prompt_packs_96851c28.plan.md",
    "crm_lead_form_overhaul_93e0de5e.plan.md",
    "v5.0.0_drift_cleanup_5aa65d68.plan.md",
    "pe_kernel_bind.plan.json",
    "pe-kernel-bind.activate.yaml",
    "website_bot_source_first_reconstruction.plan.json",
]


def main() -> None:
    DST.mkdir(exist_ok=True)
    moved, skipped, missing = [], [], []
    for name in NAMES:
        src = SRC / name
        dst = DST / name
        if dst.exists() and not src.exists():
            skipped.append(name)
            continue
        if not src.exists():
            missing.append(name)
            continue
        if dst.exists():
            dst.unlink()
        src.rename(dst)
        moved.append(name)
    print(f"moved={len(moved)} already={len(skipped)} missing={len(missing)}")
    for row in missing:
        print(f"missing {row}")


if __name__ == "__main__":
    main()
