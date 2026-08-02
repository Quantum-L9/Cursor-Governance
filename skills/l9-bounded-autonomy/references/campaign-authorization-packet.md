# Campaign authorization packet

**Term:** campaign authorization packet (never “envelope”).  
**Not** a TransportPacket / PacketEnvelope wire object — this is campaign authority for Cursor/Claude remediation scope.

## When created

`/autonomy` or an explicit user phrase such as “run bounded autonomy campaign on PR #N” creates the packet and records it in the Phase-0 table.

## Schema

```yaml
packet_id: string          # e.g. autonomy-2026-08-02-1
authority: A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE
profile: pr-convergence
autonomous_merge: false
declared_prs: [number]     # lock keys pr:<n>
declared_branches: [string]
allowed_inside_packet:
  - remediate_until_green   # ≤3 fix-push cycles per PR
  - commit_scoped_on_declared_branch
  - push_non_force_declared_branch
  - inspect_ci_and_comments
forbidden_inside_packet:
  - merge_pull_request
  - force_push
  - admin_merge
  - expand_scope
  - commit_secrets
  - weaken_tests_for_green
created_by: "/autonomy" | "explicit_user_phrase"
```

## Rules

1. Inside the packet, poll/remediation workers **may** commit and push **only** to declared PR branches (ADR-0001 remediation ON).
2. Outside the packet, normal Cursor commit/push approval applies; a poll worker is **watch-only** and escalates fixes to main for approval.
3. The packet **does not** authorize merge, force-push, admin merge, unrelated branches, scope expansion, secrets, or weakening tests for green.
4. State the packet on the first screen of `/autonomy` — not a silent waiver of `99-no-auto-commit`.
5. Main agent opportunistic pushes outside declared Phase-0 actions remain forbidden even when a packet exists.
