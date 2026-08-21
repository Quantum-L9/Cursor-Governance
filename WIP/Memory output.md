GOV="${HOME}/.cursor-governance"
GRAPHITI_PY="${GOV}/.venv/bin/python"
CLIENT="${GOV}/ops/graphiti/graphiti_memory_client.py"
echo "======= bounded-replanning ======="
"$GRAPHITI_PY" "$CLIENT" search "bounded-replanning-v1 campaign status blocked next" --limit 8
echo "======= pe-crack ======="
"$GRAPHITI_PY" "$CLIENT" search "pe-crack-remediation campaign Claude Code finishing" --limit 8
echo "======= PICKUP latest ======="
"$GRAPHITI_PY" "$CLIENT" search "PICKUP|date=2026-08-14 campaign" --limit 8
echo "======= pec status ======="
PEC="/Users/ib-mac/Cursor-Governance/environment/program-execution/core/program-execution-controller-template/scripts/pec.py"
if [ -f "$PEC" ]; then
  python3 "$PEC" status --workspace /Users/ib-mac/.l9/programs/bounded-replanning-v1 2>&1 | head -80
  echo "======= pec next ======="
  python3 "$PEC" next --workspace /Users/ib-mac/.l9/programs/bounded-replanning-v1 2>&1 | head -80
fi
echo "======= pe-crack dirty summary ======="
git -C /Users/ib-mac/.l9/program-worktrees/pe-crack-remediation-v1 status --porcelain | head -40
echo "======= bounded dirty ======="
git -C /Users/ib-mac/.l9/program-worktrees/bounded-replanning-v1 status --porcelain
echo "======= open PRs via gh ======="
gh pr list --repo Quantum-L9/Cursor-Governance --state open --limit 40 --json number,title,headRefName,createdAt,updatedAt,mergeable,url
======= bounded-replanning =======
{
  "group_id": "cursor-governance",
  "read_groups": [
    "cursor-governance",
    "igor-workspace"
  ],
  "budget_tokens": 400,
  "results": [
    {
      "uuid": "7aabb8c3-c3a2-4600-9cd0-79e2afe12068",
      "group_id": "cursor-governance",
      "source_node_uuid": "6c539830-9155-4a66-b12e-b06549fe27ef",
      "target_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "created_at": "2026-08-14T20:56:26.493800Z",
      "name": "IS_PART_OF",
      "fact": "The bounded-replanning-v1 campaign is part of Cursor-Governance.",
      "episodes": [
        "25995bf8-63ed-438d-a04b-778b81d28d53"
      ],
      "expired_at": "2026-08-14T22:48:15.011577Z",
      "valid_at": "2026-08-14T20:54:00Z",
      "invalid_at": "2026-08-14T22:47:54.450816Z",
      "attributes": {}
    },
    {
      "uuid": "0cb56a73-1c6f-4d56-816c-e73e29d0819d",
      "group_id": "cursor-governance",
      "source_node_uuid": "6c539830-9155-4a66-b12e-b06549fe27ef",
      "target_node_uuid": "0053d697-3322-4cc9-8423-5636fc4da56c",
      "created_at": "2026-08-14T20:56:51.963288Z",
      "name": "IS_LINKED_TO",
      "fact": "The bounded-replanning-v1 campaign is linked to the l9-devpack-program-execution-hardening campaign.",
      "episodes": [
        "4e7e1c63-379b-4e41-b7c5-7efd10aa936e"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T20:54:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "0c927bad-e17f-4ef2-b2f7-3a2d9ff2e9ae",
      "group_id": "cursor-governance",
      "source_node_uuid": "6c539830-9155-4a66-b12e-b06549fe27ef",
      "target_node_uuid": "9666f20f-ac51-44d5-8e44-d8c646e4160e",
      "created_at": "2026-08-14T20:56:51.963306Z",
      "name": "IS_LINKED_TO",
      "fact": "The bounded-replanning-v1 campaign is associated with the cc-pe-intent-compiler-v1 campaign.",
      "episodes": [
        "4e7e1c63-379b-4e41-b7c5-7efd10aa936e"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T20:54:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "084c852b-16aa-4773-a9cc-84358a4c54fb",
      "group_id": "cursor-governance",
      "source_node_uuid": "4958ec0f-ea32-4b3f-9376-f4162dbe7311",
      "target_node_uuid": "6c539830-9155-4a66-b12e-b06549fe27ef",
      "created_at": "2026-08-14T20:56:51.963172Z",
      "name": "IS_LINKED_TO",
      "fact": "The campaign plan for l9-ecosystem-fix-plan is related to the bounded-replanning-v1 campaign.",
      "episodes": [
        "4e7e1c63-379b-4e41-b7c5-7efd10aa936e"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T20:54:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "8d169707-bc28-4404-bfa5-b0626626cf62",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "b123a667-3720-4a18-a2a3-809388ee75eb",
      "created_at": "2026-08-14T22:30:23.250999Z",
      "name": "USES",
      "fact": "Cursor-Governance is utilizing the bounded-replanning-v1 worktree.",
      "episodes": [
        "1423256c-c852-4437-ab9e-f6b172128a70"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T22:30:06.670723Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "62b7f504-c8a1-4f04-b77a-819cc4527ee4",
      "group_id": "cursor-governance",
      "source_node_uuid": "f3f6030e-19ec-45e2-bdae-555fa53c6eb0",
      "target_node_uuid": "6c539830-9155-4a66-b12e-b06549fe27ef",
      "created_at": "2026-08-14T21:38:20.212331Z",
      "name": "IS_PART_OF",
      "fact": "The replan.py script is part of the bounded-replanning-v1 environment.",
      "episodes": [
        "4f02564f-101c-43dd-a9a5-0b0fd7c2d1ea"
      ],
      "expired_at": "2026-08-14T21:38:35.603660Z",
      "valid_at": "2026-08-14T21:38:06.303851Z",
      "invalid_at": "2026-08-14T21:38:25.345365Z",
      "attributes": {}
    },
    {
      "uuid": "0744f2db-fbf3-4bda-bfde-b5476dc1c057",
      "group_id": "cursor-governance",
      "source_node_uuid": "74e80ce6-c11e-444d-9ad4-cd7a86d2c20d",
      "target_node_uuid": "6c539830-9155-4a66-b12e-b06549fe27ef",
      "created_at": "2026-08-14T21:38:20.212311Z",
      "name": "IS_PART_OF",
      "fact": "The replan-revision.schema.json file is part of the bounded-replanning-v1 environment.",
      "episodes": [
        "4f02564f-101c-43dd-a9a5-0b0fd7c2d1ea"
      ],
      "expired_at": "2026-08-14T21:38:35.654404Z",
      "valid_at": "2026-08-14T21:38:06.303851Z",
      "invalid_at": "2026-08-14T21:38:25.345365Z",
      "attributes": {}
    },
    {
      "uuid": "260730e3-8b24-48de-9201-4dc63baf0571",
      "group_id": "cursor-governance",
      "source_node_uuid": "4958ec0f-ea32-4b3f-9376-f4162dbe7311",
      "target_node_uuid": "9666f20f-ac51-44d5-8e44-d8c646e4160e",
      "created_at": "2026-08-14T20:56:51.963238Z",
      "name": "IS_LINKED_TO",
      "fact": "The campaign plan for l9-ecosystem-fix-plan is associated with the cc-pe-intent-compiler-v1 campaign.",
      "episodes": [
        "4e7e1c63-379b-4e41-b7c5-7efd10aa936e"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T20:54:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "55646bd7-2aec-44dc-807c-cbe366c408fe",
      "group_id": "igor-workspace",
      "source_node_uuid": "c3cbbc9d-affd-49db-ae63-ec913a217f6d",
      "target_node_uuid": "6e79a297-f706-4d79-ba8a-9ab1934cc525",
      "created_at": "2026-08-07T17:55:57.036360Z",
      "name": "CHECKS_HEALTH",
      "fact": "GET /api/v1/web-lead/health returns an ok status for the web-lead API.",
      "episodes": [
        "2b352c37-e166-4409-b22d-38f75f7aadd5"
      ],
      "expired_at": null,
      "valid_at": "2026-08-07T17:55:43Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "f809e66f-4f69-4fd4-bb56-134208ae3c62",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "ae285148-915a-4bec-ad0f-d9f45f347b6c",
      "created_at": "2026-08-02T20:26:36.442732Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 requires milestones.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "3b95c4d0-05a1-4cba-b967-c570c0097f4c",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "5a65de82-cb44-44ed-8038-c3e9b9b1d218",
      "created_at": "2026-08-02T20:26:36.442752Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 requires checkpoints.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "f50351a7-55a3-4c2e-84f0-133504257ee2",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "9f291f86-8919-4b21-a438-83be41cb2f0e",
      "created_at": "2026-08-02T20:26:36.442789Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 requires a pr-check when code is in scope.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "9525a8c4-9ecb-4792-bafc-4f3345795987",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "0a452f7f-9c61-4e03-9349-dc1f97daefac",
      "created_at": "2026-08-02T20:26:36.442825Z",
      "name": "RELATED_TO",
      "fact": "The documents related to the hardened skill l9-plan v2.1.0 include references/plan-workflow.md.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "24a3a382-b7a3-4821-b3ea-5bba5a536996",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "60239ab1-3fb6-4f30-a570-b339df323d80",
      "created_at": "2026-08-02T20:26:36.442681Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 requires Pre-Validation.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "dba64ba2-2f39-4b36-90d0-600d77dc69f7",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "af81aaa0-9d39-4eb3-b7e5-9bfcdd4fb1d0",
      "created_at": "2026-08-02T20:26:36.442862Z",
      "name": "RELATED_TO",
      "fact": "The documents related to the hardened skill l9-plan v2.1.0 include commands/plan.md.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "8a465fe9-30f4-46ed-a952-bc8ae7e7d8fc",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "e85c259e-3220-4e39-9dd5-8fe760f2619b",
      "created_at": "2026-08-02T20:26:36.442771Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 requires a checklist.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    }
  ]
}
======= pe-crack =======
{
  "group_id": "cursor-governance",
  "read_groups": [
    "cursor-governance",
    "igor-workspace"
  ],
  "budget_tokens": 400,
  "results": [
    {
      "uuid": "b198ba05-ae37-4cc4-91d0-0a9732ca7ffc",
      "group_id": "cursor-governance",
      "source_node_uuid": "79dfbc0d-ed6c-4799-8be8-04bb74d6045d",
      "target_node_uuid": "8c97d904-949a-4e99-a30c-966019cb4258",
      "created_at": "2026-08-11T18:32:37.104600Z",
      "name": "FEATURES",
      "fact": "The Claude Code session includes a feature related to finishing the PE campaign stack remainder.",
      "episodes": [
        "2fb3647a-da3a-4eb5-83ea-9a25eb29145e"
      ],
      "expired_at": "2026-08-11T18:37:06.123254Z",
      "valid_at": "2026-08-11T18:32:26.936329Z",
      "invalid_at": "2026-08-11T18:36:49.601806Z",
      "attributes": {}
    },
    {
      "uuid": "c82a263f-4183-4523-b749-d666e350692b",
      "group_id": "cursor-governance",
      "source_node_uuid": "79dfbc0d-ed6c-4799-8be8-04bb74d6045d",
      "target_node_uuid": "0053d697-3322-4cc9-8423-5636fc4da56c",
      "created_at": "2026-08-11T18:32:37.104673Z",
      "name": "FEATURES",
      "fact": "The Claude Code session features a registration of the l9-devpack-program-execution-hardening campaign.",
      "episodes": [
        "2fb3647a-da3a-4eb5-83ea-9a25eb29145e",
        "c5d2615a-d20e-43bd-a3ac-5aff8c030504"
      ],
      "expired_at": "2026-08-11T18:49:08.390865Z",
      "valid_at": "2026-08-11T18:32:26.936329Z",
      "invalid_at": "2026-08-11T18:48:56.506075Z",
      "attributes": {}
    },
    {
      "uuid": "3f7bcfb4-7841-47cf-832d-8483e69f4f16",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "8c97d904-949a-4e99-a30c-966019cb4258",
      "created_at": "2026-08-11T20:41:34.192575Z",
      "name": "FINISHES",
      "fact": "Cursor-Governance involves finishing the PE campaign stack remainder.",
      "episodes": [
        "55627a1e-a7a3-4c47-8e23-8cd04483c9a0"
      ],
      "expired_at": "2026-08-11T20:59:29.265065Z",
      "valid_at": "2026-08-11T20:41:27.714517Z",
      "invalid_at": "2026-08-11T20:59:17.703386Z",
      "attributes": {}
    },
    {
      "uuid": "cb26fa39-8fae-4c90-91aa-9694752e2bb6",
      "group_id": "cursor-governance",
      "source_node_uuid": "79dfbc0d-ed6c-4799-8be8-04bb74d6045d",
      "target_node_uuid": "8c97d904-949a-4e99-a30c-966019cb4258",
      "created_at": "2026-08-11T18:37:03.598532Z",
      "name": "FEATURES",
      "fact": "The Claude Code session features the PE campaign stack.",
      "episodes": [
        "c5d2615a-d20e-43bd-a3ac-5aff8c030504"
      ],
      "expired_at": null,
      "valid_at": "2026-08-11T18:36:49.601806Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "7f37196a-6095-485b-a79b-17821ccb8e34",
      "group_id": "cursor-governance",
      "source_node_uuid": "2977bcce-7f81-4b96-b771-444bbd013fc8",
      "target_node_uuid": "8c97d904-949a-4e99-a30c-966019cb4258",
      "created_at": "2026-08-11T18:29:38.600739Z",
      "name": "INCLUDES",
      "fact": "The program-execution involves finishing the PE campaign stack remainder.",
      "episodes": [
        "86c5243b-3eaf-4c34-a5c9-7348a3286ca7",
        "e67097af-5983-4718-934f-c0de166390d8",
        "1696f50b-ee54-4f2d-9bcd-cea7a0d65379"
      ],
      "expired_at": "2026-08-11T18:32:38.621617Z",
      "valid_at": "2026-08-11T18:29:28Z",
      "invalid_at": "2026-08-11T18:32:26.936329Z",
      "attributes": {}
    },
    {
      "uuid": "49801c80-3c59-44bd-831c-6661797faabf",
      "group_id": "cursor-governance",
      "source_node_uuid": "8c97d904-949a-4e99-a30c-966019cb4258",
      "target_node_uuid": "79dfbc0d-ed6c-4799-8be8-04bb74d6045d",
      "created_at": "2026-08-11T19:54:29.641104Z",
      "name": "FEATURED_IN",
      "fact": "The PE campaign stack remainder is featured in the Claude Code session.",
      "episodes": [
        "5f16aae2-f0da-4d75-a14f-25f3dd97cc6b"
      ],
      "expired_at": null,
      "valid_at": "2026-08-11T19:54:22.458120Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "9192a7c8-2ddd-4f7d-83df-966ebd474eaa",
      "group_id": "cursor-governance",
      "source_node_uuid": "0053d697-3322-4cc9-8423-5636fc4da56c",
      "target_node_uuid": "79dfbc0d-ed6c-4799-8be8-04bb74d6045d",
      "created_at": "2026-08-11T18:49:06.725256Z",
      "name": "REGISTERED_BY",
      "fact": "l9-devpack-program-execution-hardening campaign is registered by Claude Code.",
      "episodes": [
        "accca6a9-5163-4b0e-ab60-1911aff4ff63"
      ],
      "expired_at": "2026-08-11T19:54:31.653526Z",
      "valid_at": "2026-08-11T18:48:56.506075Z",
      "invalid_at": "2026-08-11T19:54:22.458120Z",
      "attributes": {}
    },
    {
      "uuid": "d59ac82a-4e1f-4c26-a16f-961a0773c018",
      "group_id": "cursor-governance",
      "source_node_uuid": "8c97d904-949a-4e99-a30c-966019cb4258",
      "target_node_uuid": "79dfbc0d-ed6c-4799-8be8-04bb74d6045d",
      "created_at": "2026-08-11T20:12:08.656595Z",
      "name": "PART_OF",
      "fact": "The PE campaign stack remainder is discussed in the Claude Code session on Cursor-Governance.",
      "episodes": [
        "9be3586e-8513-4230-b35e-68aa30452b88"
      ],
      "expired_at": "2026-08-11T20:36:02.755386Z",
      "valid_at": "2026-08-11T20:12:01.551429Z",
      "invalid_at": "2026-08-11T20:35:54.845770Z",
      "attributes": {}
    },
    {
      "uuid": "1ff2c5e0-39e0-4320-a6db-cb00cdaaa337",
      "group_id": "igor-workspace",
      "source_node_uuid": "a79793fc-ccb8-4fd9-a03c-3e089a7babff",
      "target_node_uuid": "b95abfb2-cb8b-4636-881c-37b64b609505",
      "created_at": "2026-08-06T07:05:00.579949Z",
      "name": "EXISTS_FOR",
      "fact": "Proactive L9 skill router was created specifically for Claude Code.",
      "episodes": [
        "19ef80f3-2833-4c4b-97f3-036bb46c2df8"
      ],
      "expired_at": null,
      "valid_at": "2026-08-06T07:04:44.145223Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "f50351a7-55a3-4c2e-84f0-133504257ee2",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "9f291f86-8919-4b21-a438-83be41cb2f0e",
      "created_at": "2026-08-02T20:26:36.442789Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 requires a pr-check when code is in scope.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "89e5f2be-b619-4612-8c19-edcd0c4f8d89",
      "group_id": "igor-workspace",
      "source_node_uuid": "25d34b79-12f1-4a9b-8b0f-8d72f46c758c",
      "target_node_uuid": "4513dc85-7786-4c0f-85b3-908cfa122a23",
      "created_at": "2026-08-02T21:42:00.429824Z",
      "name": "USED",
      "fact": "llm-router utilized anthropic/claude-haiku-4.5 for schema generation.",
      "episodes": [
        "9b69f918-159e-46dd-896f-cd910c7cf9cb"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T21:41:46.807419Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "81436708-05d2-44e3-9bdc-6dd6f58d7bf4",
      "group_id": "igor-workspace",
      "source_node_uuid": "e6cddb7b-b9fe-4bd9-a52d-16eb8c2d4777",
      "target_node_uuid": "112aecc5-b1c2-4a94-83fd-c9fa8c8ad562",
      "created_at": "2026-08-02T22:27:56.819317Z",
      "name": "DIFFERS_FROM",
      "fact": "The Cursor-Governance doctrine is distinct from the /harvest code extraction process.",
      "episodes": [
        "d6cc4793-c5b0-4dcf-852f-3cefb19c03d2"
      ],
      "expired_at": "2026-08-06T05:24:18.453213Z",
      "valid_at": "2026-08-02T22:27:40.822929Z",
      "invalid_at": "2026-08-06T05:23:53.622795Z",
      "attributes": {}
    },
    {
      "uuid": "182cddb0-bdb4-4f6a-9cbf-40a845b32d60",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "9f291f86-8919-4b21-a438-83be41cb2f0e",
      "created_at": "2026-08-02T20:26:36.442931Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 includes a requirement to make the pr-check PASS.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "4a4beeee-de62-4fc0-87fb-58a6a242850c",
      "group_id": "igor-workspace",
      "source_node_uuid": "349d1d99-c318-4980-827c-39a883ea7806",
      "target_node_uuid": "c91836b8-9e40-4c3b-b196-513a44371266",
      "created_at": "2026-08-06T05:24:14.150342Z",
      "name": "SUCCESS_ON",
      "fact": "Website-Bot succeeded with the memory-stack gates post-grant.",
      "episodes": [
        "6fb5864e-1d95-48bf-abae-b39232d6912f"
      ],
      "expired_at": null,
      "valid_at": "2026-08-06T05:23:53.622795Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "3b95c4d0-05a1-4cba-b967-c570c0097f4c",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "5a65de82-cb44-44ed-8038-c3e9b9b1d218",
      "created_at": "2026-08-02T20:26:36.442752Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 requires checkpoints.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "6ced0801-dd3c-4b72-8bb2-0ce433c7a6fa",
      "group_id": "igor-workspace",
      "source_node_uuid": "ee91ade7-e395-43db-a3bf-8ae9a20760f6",
      "target_node_uuid": "04fc6693-ea72-4686-9646-cca6bbaf4a17",
      "created_at": "2026-08-02T20:26:36.442711Z",
      "name": "REQUIRES",
      "fact": "The hardened skill l9-plan v2.1.0 requires Final Validation.",
      "episodes": [
        "1455b589-6a4c-4620-905e-75f8dc939b96"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:26:19.598266Z",
      "invalid_at": null,
      "attributes": {}
    }
  ]
}
======= PICKUP latest =======
{
  "group_id": "cursor-governance",
  "read_groups": [
    "cursor-governance",
    "igor-workspace"
  ],
  "budget_tokens": 400,
  "results": [
    {
      "uuid": "4f629d55-708f-49c2-be7b-0d77ee2ea199",
      "group_id": "cursor-governance",
      "source_node_uuid": "95a46d1c-5065-47ad-ad12-35409895f800",
      "target_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "created_at": "2026-08-14T20:45:36.251262Z",
      "name": "IS_LANDED_IN",
      "fact": "PR #130 has landed in Cursor-Governance on 2026-08-14.",
      "episodes": [
        "88adea6a-d20f-40c9-86c5-6ab5b076b353"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T20:44:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "f446d3ee-4da9-4b14-b6d6-55e83e4bd5a4",
      "group_id": "cursor-governance",
      "source_node_uuid": "168a915b-e3fd-4ede-9cca-7d5435fa59f7",
      "target_node_uuid": "6f1716e1-b5a7-4f72-b774-b9033fffb027",
      "created_at": "2026-08-14T23:57:40.605262Z",
      "name": "PRODUCED",
      "fact": "Phase A successfully produced the PICKUP record with two writes.",
      "episodes": [
        "d10449e5-9679-4365-acd1-0af5f2bbb722"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T21:30:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "6a245d32-9881-41ee-90dc-e993dd977033",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "dedf3429-92ac-4f9b-83df-b1a8f8e47880",
      "created_at": "2026-08-14T20:47:09.259865Z",
      "name": "LANDED_WITH_PR",
      "fact": "The housekeeping-pack was landed with PR #130 on 2026-08-14.",
      "episodes": [
        "16cf9361-15ea-4ae1-81f6-fee409ff5902"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T20:45:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "078d865d-5907-46a2-a058-18e79df40702",
      "group_id": "cursor-governance",
      "source_node_uuid": "1d6e74cf-fb0f-4f0a-8bd1-df44bba54a32",
      "target_node_uuid": "6f1716e1-b5a7-4f72-b774-b9033fffb027",
      "created_at": "2026-08-14T23:57:40.605283Z",
      "name": "ATTEMPTED_TO_DISTILL",
      "fact": "Phase B attempted to distill the PICKUP record but failed due to a potential issue with S3 or Redis.",
      "episodes": [
        "d10449e5-9679-4365-acd1-0af5f2bbb722"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T21:30:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "d2ca7554-5cc3-4aad-89df-49ccd5d74114",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "60690c4d-3acc-4a4e-9f88-971c6c053b1a",
      "created_at": "2026-08-14T18:11:36.135761Z",
      "name": "UPDATES",
      "fact": "The version of l9-update-agent-docs has been updated to 2.0.3 on 2026-08-14.",
      "episodes": [
        "241e31f5-f2ff-401e-8f10-3fa819d29521"
      ],
      "expired_at": null,
      "valid_at": "2026-08-14T00:00:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "bf8eb235-7c26-4fdf-b169-9194bcad41bf",
      "group_id": "cursor-governance",
      "source_node_uuid": "8c97d904-949a-4e99-a30c-966019cb4258",
      "target_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "created_at": "2026-08-11T19:20:35.518190Z",
      "name": "INCLUDES",
      "fact": "PE campaign stack is included in Cursor-Governance recent commits.",
      "episodes": [
        "8f25aea9-fd63-4194-b1c5-9dd9fe01a8fd"
      ],
      "expired_at": "2026-08-11T19:20:48.764160Z",
      "valid_at": "2026-08-11T19:20:17.312551Z",
      "invalid_at": "2026-08-11T19:20:38.003756Z",
      "attributes": {}
    },
    {
      "uuid": "edf6bd15-80d9-4913-a3a2-7cd96a18919e",
      "group_id": "cursor-governance",
      "source_node_uuid": "79dfbc0d-ed6c-4799-8be8-04bb74d6045d",
      "target_node_uuid": "eea57706-a376-41b6-89b5-523840d7c32f",
      "created_at": "2026-08-11T19:57:17.020821Z",
      "name": "END_SESSION",
      "fact": "The Claude Code session ended on 2026-08-11.",
      "episodes": [
        "02b730a2-f5dd-4de9-8296-dbb8d3ac3d73"
      ],
      "expired_at": "2026-08-11T19:57:18.804504Z",
      "valid_at": "2026-08-11T00:00:00Z",
      "invalid_at": "2026-08-11T00:00:00Z",
      "attributes": {}
    },
    {
      "uuid": "b6f7ca10-7c9f-442a-b0e1-03dc72acef0e",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "0acbaaf3-7c46-414e-a1d6-a5feb879969f",
      "created_at": "2026-08-14T18:03:09.675978Z",
      "name": "CONTINUES_WORK_ON",
      "fact": "Work is continuing in the Cursor-Governance project based on the latest Graphiti PICKUP requests.",
      "episodes": [
        "7380eedb-960b-49cf-8611-cf5839f3b8ed"
      ],
      "expired_at": "2026-08-14T21:13:16.527453Z",
      "valid_at": "2026-08-14T18:02:58Z",
      "invalid_at": "2026-08-14T21:13:04.394033Z",
      "attributes": {}
    },
    {
      "uuid": "094505ed-32ec-4dda-9e6f-a985601a668e",
      "group_id": "igor-workspace",
      "source_node_uuid": "0b3be013-5348-420e-a70c-2272c46e4171",
      "target_node_uuid": "40d4dde5-fc66-4c98-ae0f-5404cc131195",
      "created_at": "2026-08-02T21:42:00.429846Z",
      "name": "DEPLOYED_FROM",
      "fact": "Build 30768235988 was successfully deployed to Deploy 30768238035.",
      "episodes": [
        "9b69f918-159e-46dd-896f-cd910c7cf9cb"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T21:41:46.807419Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "c3ccd912-b408-4897-81cd-69a19e0d3f77",
      "group_id": "igor-workspace",
      "source_node_uuid": "63bd691b-178f-49d3-bd45-c6159da0572c",
      "target_node_uuid": "27846499-1247-4abf-b794-a8f5c8d5e20a",
      "created_at": "2026-08-06T05:24:14.150416Z",
      "name": "ARTIFACTS_IN",
      "fact": "Artifacts related to Cursor-Governance can be found in the GitHub repository.",
      "episodes": [
        "6fb5864e-1d95-48bf-abae-b39232d6912f"
      ],
      "expired_at": null,
      "valid_at": "2026-08-06T05:23:53.622795Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "70138ae1-a7be-47c6-8928-db95a274748a",
      "group_id": "igor-workspace",
      "source_node_uuid": "a3e33c12-2ecb-417d-a275-edc49506b13e",
      "target_node_uuid": "b5a9bb0e-1361-41c8-b140-8093f1e42e46",
      "created_at": "2026-08-02T21:42:00.429870Z",
      "name": "HAS_PREFLIGHT_SUCCESS",
      "fact": "Agent Pipeline had a preflight success with INNGEST_EVENT_KEY being empty.",
      "episodes": [
        "9b69f918-159e-46dd-896f-cd910c7cf9cb"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T21:41:46.807419Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "81436708-05d2-44e3-9bdc-6dd6f58d7bf4",
      "group_id": "igor-workspace",
      "source_node_uuid": "e6cddb7b-b9fe-4bd9-a52d-16eb8c2d4777",
      "target_node_uuid": "112aecc5-b1c2-4a94-83fd-c9fa8c8ad562",
      "created_at": "2026-08-02T22:27:56.819317Z",
      "name": "DIFFERS_FROM",
      "fact": "The Cursor-Governance doctrine is distinct from the /harvest code extraction process.",
      "episodes": [
        "d6cc4793-c5b0-4dcf-852f-3cefb19c03d2"
      ],
      "expired_at": "2026-08-06T05:24:18.453213Z",
      "valid_at": "2026-08-02T22:27:40.822929Z",
      "invalid_at": "2026-08-06T05:23:53.622795Z",
      "attributes": {}
    },
    {
      "uuid": "ae47ce1f-b60a-4aa6-b61f-0cc8fe76fc7e",
      "group_id": "igor-workspace",
      "source_node_uuid": "3dd93b5c-3c93-4d39-9cfd-c7ee0d7953f3",
      "target_node_uuid": "6c44e495-02c7-4e23-ac1d-0e75e65f7925",
      "created_at": "2026-08-06T05:24:14.150398Z",
      "name": "UNCHANGED",
      "fact": "Cursor-Governance left unchanged in relation to CI debt repos and future candidate grants.",
      "episodes": [
        "6fb5864e-1d95-48bf-abae-b39232d6912f"
      ],
      "expired_at": null,
      "valid_at": "2026-08-06T05:23:53.622795Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "77b2a374-0547-482d-8c34-b5bbe0c44c2d",
      "group_id": "igor-workspace",
      "source_node_uuid": "3dd93b5c-3c93-4d39-9cfd-c7ee0d7953f3",
      "target_node_uuid": "a79793fc-ccb8-4fd9-a03c-3e089a7babff",
      "created_at": "2026-08-06T07:05:00.580021Z",
      "name": "WIRED_TO",
      "fact": "The skill router is connected to Cursor via a specific hook.",
      "episodes": [
        "19ef80f3-2833-4c4b-97f3-036bb46c2df8"
      ],
      "expired_at": null,
      "valid_at": "2026-08-06T07:04:44.145223Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "02635254-0641-42db-8109-26b9d7aff889",
      "group_id": "igor-workspace",
      "source_node_uuid": "e6cddb7b-b9fe-4bd9-a52d-16eb8c2d4777",
      "target_node_uuid": "3983d4e0-252f-43fc-8d3c-2693fb4cd31c",
      "created_at": "2026-08-02T22:27:56.819210Z",
      "name": "REFERS_TO",
      "fact": "The Cursor-Governance doctrine includes a canonical Load-map shape as defined in skills/l9-plan/references/authority-bindings.md.",
      "episodes": [
        "d6cc4793-c5b0-4dcf-852f-3cefb19c03d2"
      ],
      "expired_at": "2026-08-06T05:24:18.453225Z",
      "valid_at": "2026-08-02T22:27:40.822929Z",
      "invalid_at": "2026-08-06T05:23:53.622795Z",
      "attributes": {}
    },
    {
      "uuid": "d30780bf-b029-452e-ba5a-ebc3ae614320",
      "group_id": "igor-workspace",
      "source_node_uuid": "e6cddb7b-b9fe-4bd9-a52d-16eb8c2d4777",
      "target_node_uuid": "5185b6ac-08fb-4b04-8a43-45c290e32ec7",
      "created_at": "2026-08-02T22:27:56.819241Z",
      "name": "REFERS_TO",
      "fact": "The Cursor-Governance doctrine is discussed in AGENTS.md \u00a75.3 regarding prohibitions on certain actions.",
      "episodes": [
        "d6cc4793-c5b0-4dcf-852f-3cefb19c03d2"
      ],
      "expired_at": "2026-08-06T05:24:18.453200Z",
      "valid_at": "2026-08-02T22:27:40.822929Z",
      "invalid_at": "2026-08-06T05:23:53.622795Z",
      "attributes": {}
    }
  ]
}
======= pec status =======
{
  "active_leases": [],
  "decisions": [
    {
      "evidence_ids": [
        "EVID-002"
      ],
      "id": "DEC-001",
      "source": {
        "blocks": [],
        "evidence_ids": [
          "EVID-002"
        ],
        "id": "DEC-001",
        "options": [
          {
            "benefits": [
              "Current immutable Program Lock."
            ],
            "description": "Current immutable Program Lock.",
            "id": "A",
            "risks": [
              "Rejected alternative would violate accepted ADRs."
            ]
          },
          {
            "benefits": [
              "Dynamically expanded authority derived from the program objective."
            ],
            "description": "Dynamically expanded authority derived from the program objective.",
            "id": "B",
            "risks": [
              "Rejected alternative would violate accepted ADRs."
            ]
          }
        ],
        "owner": "AUTH-005",
        "question": "What is the maximum authority available to autonomous replanning?",
        "rationale": "Selected A per AUTH-005.",
        "required_by": "AUTH-005",
        "selected_option": "A",
        "status": "accepted",
        "supersedes": null
      },
      "status": "accepted"
    },
    {
      "evidence_ids": [
        "EVID-002"
      ],
      "id": "DEC-002",
      "source": {
        "blocks": [],
        "evidence_ids": [
          "EVID-002"
        ],
        "id": "DEC-002",
        "options": [
          {
            "benefits": [
              "Controller after independent validation."
            ],
            "description": "Controller after independent validation.",
            "id": "A",
            "risks": [
              "Rejected alternative would violate accepted ADRs."
            ]
          },
          {
            "benefits": [
              "Worker that proposes the revision."
            ],
            "description": "Worker that proposes the revision.",
            "id": "B",
            "risks": [
              "Rejected alternative would violate accepted ADRs."
            ]
          }
        ],
        "owner": "AUTH-005",
======= pec next =======
{
  "blocked": [
    {
      "blockers": [
        "required_evidence_missing_or_invalid:EVID-001",
        "required_evidence_missing_or_invalid:EVID-002",
        "required_evidence_missing_or_invalid:EVID-003",
        "required_evidence_missing_or_invalid:EVID-004",
        "required_evidence_missing_or_invalid:EVID-005",
        "repository_not_reconciled",
        "source_contract_incomplete"
      ],
      "id": "TASK-001",
      "repository_id": "Quantum-L9/Cursor-Governance",
      "target_id": "TARGET-001",
      "title": "Lock current Program Execution architecture",
      "wave_id": "W0"
    },
    {
      "blockers": [
        "definition_not_ready:blocked",
        "dependency_not_complete:TASK-001",
        "blocking_unknown:UNK-001",
        "required_evidence_missing_or_invalid:EVID-002",
        "required_evidence_missing_or_invalid:EVID-003",
        "predecessor_wave_task_not_completed:W0:TASK-001",
        "predecessor_wave_exit_gate_not_satisfied:W0:GATE-001",
        "repository_not_reconciled",
        "source_contract_incomplete"
      ],
      "id": "TASK-002",
      "repository_id": "Quantum-L9/Cursor-Governance",
      "target_id": "TARGET-001",
      "title": "Implement canonical program-execution.replan.v1 contract",
      "wave_id": "W1"
    },
    {
      "blockers": [
        "definition_not_ready:blocked",
        "dependency_not_complete:TASK-002",
        "required_evidence_missing_or_invalid:EVID-003",
        "required_evidence_missing_or_invalid:EVID-006",
        "predecessor_wave_task_not_completed:W1:TASK-002",
        "predecessor_wave_exit_gate_not_satisfied:W1:GATE-002",
        "repository_not_reconciled",
        "source_contract_incomplete"
      ],
      "id": "TASK-003",
      "repository_id": "Quantum-L9/Cursor-Governance",
      "target_id": "TARGET-001",
      "title": "Implement Controller Replan Revision lifecycle",
      "wave_id": "W2"
    },
    {
      "blockers": [
        "definition_not_ready:blocked",
        "dependency_not_complete:TASK-002",
        "blocking_unknown:UNK-002",
        "blocking_unknown:UNK-003",
        "required_evidence_missing_or_invalid:EVID-003",
        "required_evidence_missing_or_invalid:EVID-004",
        "predecessor_wave_task_not_completed:W1:TASK-002",
        "predecessor_wave_exit_gate_not_satisfied:W1:GATE-002",
        "repository_not_reconciled",
        "source_contract_incomplete"
      ],
      "id": "TASK-004",
      "repository_id": "Quantum-L9/Cursor-Governance",
      "target_id": "TARGET-001",
      "title": "Project canonical replanning semantics to all registered peers",
      "wave_id": "W2"
    },
    {
      "blockers": [
        "definition_not_ready:blocked",
        "dependency_not_complete:TASK-004",
        "required_evidence_missing_or_invalid:EVID-004",
        "required_evidence_missing_or_invalid:EVID-007",
        "predecessor_wave_task_not_completed:W2:TASK-003",
        "predecessor_wave_task_not_completed:W2:TASK-004",
======= pe-crack dirty summary =======
 M environment/program-execution/adapters/chatgpt/provider.py
 M environment/program-execution/adapters/claude-code/provider.py
 M environment/program-execution/adapters/claude-code/tests/test_driver.py
 M environment/program-execution/adapters/cursor-background/provider.py
 M environment/program-execution/adapters/cursor-background/tests/test_provider.py
 M environment/program-execution/adapters/cursor-foreground/provider.py
 M environment/program-execution/adapters/cursor-foreground/tests/test_provider.py
 M environment/program-execution/core/program-execution-blueprint-template/schemas/current-state-delta.schema.json
 M environment/program-execution/core/program-execution-blueprint-template/schemas/cutover-and-rollback.schema.json
 M environment/program-execution/core/program-execution-blueprint-template/schemas/do-not-build.schema.json
 M environment/program-execution/core/program-execution-blueprint-template/schemas/execution-waves.schema.json
 M environment/program-execution/core/program-execution-blueprint-template/schemas/observability-plan.schema.json
 M environment/program-execution/core/program-execution-blueprint-template/schemas/source-traceability.schema.json
 M environment/program-execution/core/program-execution-controller-template/schemas/program-lock.schema.json
 M environment/program-execution/core/program-execution-controller-template/schemas/source-contract.schema.json
 M environment/program-execution/core/program-execution-controller-template/scripts/pec/blueprint.py
 M environment/program-execution/core/program-execution-controller-template/scripts/pec/cli.py
 M environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py
 M environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py
?? environment/program-execution/adapters/chatgpt/tests/test_provider.py
?? environment/program-execution/campaigns/COMPILE_ALLOWLIST.yaml
?? environment/program-execution/conformance/test_campaign_source_schema.py
?? environment/program-execution/core/program-execution-controller-template/scripts/tests/test_bootstrap_admission.py
?? environment/program-execution/core/program-execution-controller-template/scripts/tests/test_do_not_build_verify.py
?? environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_lock_schema.py
?? environment/program-execution/core/program-execution-controller-template/scripts/tests/test_source_contract_placeholder.py
?? environment/program-execution/core/shared/schemas/campaign-source.schema.json
?? environment/program-execution/scripts/compile_campaign_source.py
?? environment/program-execution/scripts/tests/
======= bounded dirty =======
 M environment/program-execution/conformance/test_golden_vectors.py
 M environment/program-execution/conformance/test_replan_peer_parity.py
 M environment/program-execution/conformance/test_replan_projection.py
 M environment/program-execution/core/MANIFEST.yaml
 M environment/program-execution/core/tests/test_replan_handoff.py
 M environment/program-execution/core/tests/test_replan_integration.py
 M environment/program-execution/core/tests/test_replan_lifecycle.py
======= open PRs via gh =======
[{"createdAt":"2026-08-14T21:34:08Z","headRefName":"feat/l9-ecosystem-fix-plan-ceiling-converged","mergeable":"MERGEABLE","number":146,"title":"Expand locked campaign ceilings and record AUTH-001 CONVERGED.","updatedAt":"2026-08-14T21:34:08Z","url":"https://github.com/Quantum-L9/Cursor-Governance/pull/146"},{"createdAt":"2026-08-14T21:33:52Z","headRefName":"feat/l9-devpack-program-execution-hardening-ceiling-converged","mergeable":"MERGEABLE","number":145,"title":"Expand locked campaign ceilings and record AUTH-001 CONVERGED.","updatedAt":"2026-08-14T21:33:52Z","url":"https://github.com/Quantum-L9/Cursor-Governance/pull/145"},{"createdAt":"2026-08-14T21:33:37Z","headRefName":"feat/cc-pe-intent-compiler-v1-ceiling-converged","mergeable":"MERGEABLE","number":144,"title":"Expand locked campaign ceilings and record AUTH-001 CONVERGED.","updatedAt":"2026-08-14T21:33:37Z","url":"https://github.com/Quantum-L9/Cursor-Governance/pull/144"},{"createdAt":"2026-08-14T21:32:35Z","headRefName":"feat/campaign-ceiling-commit-converged","mergeable":"MERGEABLE","number":143,"title":"Expand locked campaign ceilings and record AUTH-001 CONVERGED.","updatedAt":"2026-08-14T21:32:51Z","url":"https://github.com/Quantum-L9/Cursor-Governance/pull/143"}]
