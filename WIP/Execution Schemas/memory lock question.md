export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:$PATH"
cd /Users/ib-mac/Cursor-Governance
python3 environment/agents/adapters/claude-code/hooks/memory_lock.py acquire --namespace cursor-governance --task "backup local unpushed WIP + kernel-pack branch default docs to remote" --force
{
  "namespace": "cursor-governance",
  "conflicts": [
    {
      "uuid": "763c266a-c7f9-4ea9-838f-9c8bf12c75f7",
      "group_id": "cursor-governance",
      "source_node_uuid": "024ac46c-c9c5-427f-8d89-07300e34f041",
      "target_node_uuid": "eaeb7b15-3b0c-4252-9a94-edf27602c89f",
      "created_at": "2026-08-06T06:56:58.411444Z",
      "name": "USED_FOR",
      "fact": "An admin merge was used for PR #19 after conflict remediation.",
      "episodes": [
        "58bfe444-1c25-48eb-ba60-757e80809542"
      ],
      "expired_at": null,
      "valid_at": "2026-08-06T06:56:46.577018Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "f2ad37a3-c3b1-44a3-9488-62d9f564422c",
      "group_id": "cursor-governance",
      "source_node_uuid": "43a0ea33-da39-4c94-8377-f1369c2f3dd1",
      "target_node_uuid": "83d04a37-50ae-41cf-9a11-5dd3602f9d4a",
      "created_at": "2026-08-12T03:52:19.456830Z",
      "name": "FAILS_CLOSED",
      "fact": "Peer Execution Conformance fails closed when MANIFEST.json lists files that are uncommitted.",
      "episodes": [
        "5a78fb42-b72e-4ec6-92d4-47997d0043ce"
      ],
      "expired_at": null,
      "valid_at": "2026-08-12T03:52:13.713654Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "11f8d603-5536-4205-a379-478ee2d9f1d3",
      "group_id": "cursor-governance",
      "source_node_uuid": "024ac46c-c9c5-427f-8d89-07300e34f041",
      "target_node_uuid": "c3b61b0d-dcf9-42cf-b3a0-aa7932d6c214",
      "created_at": "2026-08-06T06:56:58.411415Z",
      "name": "USED_FOR",
      "fact": "An admin merge was used for PR #31 after conflict remediation.",
      "episodes": [
        "58bfe444-1c25-48eb-ba60-757e80809542"
      ],
      "expired_at": null,
      "valid_at": "2026-08-06T06:56:46.577018Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "e4de7501-2126-4a62-9071-f5e02633a2eb",
      "group_id": "cursor-governance",
      "source_node_uuid": "2fcdf841-114e-488d-b5ea-037110f79876",
      "target_node_uuid": "51a06634-3ab1-4141-ab15-4290b1caeaa4",
      "created_at": "2026-08-11T19:04:17.935756Z",
      "name": "BLOCKS",
      "fact": "Current CI blocks normal gh pr merge due to stale contexts required by LLM-Router branch protection.",
      "episodes": [
        "7c856b9a-3504-4bfe-98a0-bcdd841120a3"
      ],
      "expired_at": null,
      "valid_at": "2026-08-11T19:04:07.690173Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "071f4b19-e41f-42ce-bca0-b8ec9ec3b1d8",
      "group_id": "cursor-governance",
      "source_node_uuid": "714810fa-0ce7-4d31-9ad4-22342d504636",
      "target_node_uuid": "43193110-5c50-4cf1-88da-9ec1cf55898e",
      "created_at": "2026-08-13T15:03:55.677960Z",
      "name": "INCLUDES",
      "fact": "The Evidence ingest plan will include a conflict-flagged event log.",
      "episodes": [
        "3e29983f-f192-4ed2-9d55-aee3286272c2"
      ],
      "expired_at": null,
      "valid_at": "2026-08-13T15:01:00Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "e0ea6e4f-2069-4899-addb-973a06f2929d",
      "group_id": "cursor-governance",
      "source_node_uuid": "aa97c6e5-a33d-4da2-8479-1ed7903976d6",
      "target_node_uuid": "d878f78d-0fb1-4aed-9fbc-197f4a917c09",
      "created_at": "2026-08-11T22:53:56.847236Z",
      "name": "HAS_COLLISION_WITH",
      "fact": "The 'pr31-rebase-test' had a collision with 'l9-ci-core' due to using possibly stale local HEAD.",
      "episodes": [
        "201b1699-7c31-4912-aafc-f766a0e05230"
      ],
      "expired_at": null,
      "valid_at": "2026-08-11T22:53:48.865795Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "d5c3bdcf-61be-49f1-b392-a8dd59f7ef21",
      "group_id": "cursor-governance",
      "source_node_uuid": "9acc8d0f-b4c8-48d4-9287-d5309f747c59",
      "target_node_uuid": "3113b15b-a23c-49af-aaa4-56551626dc71",
      "created_at": "2026-08-06T06:56:42.033850Z",
      "name": "MUST_NOT_SOFTEN",
      "fact": "Process.env.CI must not soften deploy workflows that exclude --ci.",
      "episodes": [
        "578164ee-bf7e-482c-9124-fb3d97ab33c1"
      ],
      "expired_at": null,
      "valid_at": "2026-08-06T06:56:34Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "a8703f63-12a0-4b10-a4f7-cd185ab76562",
      "group_id": "cursor-governance",
      "source_node_uuid": "2977bcce-7f81-4b96-b771-444bbd013fc8",
      "target_node_uuid": "b3432d25-2f88-4f2b-8df4-af2ac038dcd5",
      "created_at": "2026-08-11T19:26:22.185779Z",
      "name": "RECONCILES_WITH",
      "fact": "The program-execution topic reconciles with Claude settings.",
      "episodes": [
        "3a622fc8-9712-4b1a-8f46-0176691ce6b3"
      ],
      "expired_at": "2026-08-11T19:37:58.435807Z",
      "valid_at": "2026-08-11T19:26:11.324210Z",
      "invalid_at": "2026-08-11T19:37:39.644694Z",
      "attributes": {}
    },
    {
      "uuid": "39e8cf86-a3dc-4d78-9d5a-11fbf085aa8a",
      "group_id": "cursor-governance",
      "source_node_uuid": "7a3187f0-f9e4-4a5d-af0f-877c8f5716aa",
      "target_node_uuid": "de10657f-4232-416d-b516-d0a0fb124325",
      "created_at": "2026-08-11T18:25:33.319086Z",
      "name": "DOCUMENTS",
      "fact": "Decisions document includes ADR-0016.",
      "episodes": [
        "60689f97-4fbc-4780-9675-b7f389c785e4"
      ],
      "expired_at": "2026-08-11T19:56:04.398676Z",
      "valid_at": "2026-08-11T18:25:20.447395Z",
      "invalid_at": "2026-08-11T18:29:10.154944Z",
      "attributes": {}
    },
    {
      "uuid": "3efef7e6-1242-484e-ba81-ea257126bc24",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "503fe481-c898-412c-9aad-0dd79a4f7f4d",
      "created_at": "2026-08-11T19:42:34.006187Z",
      "name": "SKIPS",
      "fact": "Cursor-Governance skips CI on WIP-only diffs.",
      "episodes": [
        "ca0f1ccd-5c63-4c69-97ec-5f2716cdc5b6"
      ],
      "expired_at": null,
      "valid_at": "2026-08-11T19:42:24.039587Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "2b635c13-f4b8-4ad4-b486-616def9c7c42",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "3c9cc315-c533-4c3e-ac21-c0854a7e9ead",
      "created_at": "2026-08-02T20:47:30.513828Z",
      "name": "MUST_USE",
      "fact": "Cursor-Governance CI Test Suite must use uv sync --locked --extra dev.",
      "episodes": [
        "9d965753-9c2a-4672-bb42-42368cc7f309"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T20:47:23.750860Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "a7fd3143-faaa-4b49-8eeb-22815b2232bb",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "4c815c22-7a38-4e90-9cd6-85117d6b8f95",
      "created_at": "2026-08-13T17:38:15.955170Z",
      "name": "REFERENCES",
      "fact": "The task will check against the AUTONOMY_MANIFEST.yaml for manifest coupling.",
      "episodes": [
        "e44e99f5-b5fb-4deb-9b8a-03c58dd7b807"
      ],
      "expired_at": null,
      "valid_at": "2026-08-13T17:38:06.783000Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "0efeb15e-e2d9-45ae-ae91-a83da67a3a2b",
      "group_id": "cursor-governance",
      "source_node_uuid": "2ddc4572-93c0-41bb-8487-ff97b5317828",
      "target_node_uuid": "11f529ee-c314-4b41-ba6b-37fa907b5d36",
      "created_at": "2026-08-12T16:48:52.027756Z",
      "name": "DESCRIBES",
      "fact": "A4_CAMPAIGN_BOUNDED_EXTERNAL_WRITE describes the context for the pr-convergence process.",
      "episodes": [
        "7c55181f-056e-444f-a3dd-78568635904f"
      ],
      "expired_at": null,
      "valid_at": "2026-08-12T16:48:38Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "5127ec37-d700-4b43-80e4-93e13a2786ab",
      "group_id": "cursor-governance",
      "source_node_uuid": "7a3187f0-f9e4-4a5d-af0f-877c8f5716aa",
      "target_node_uuid": "388d62c8-315f-4554-8a63-ccce95125e55",
      "created_at": "2026-08-11T18:25:33.319067Z",
      "name": "DOCUMENTS",
      "fact": "Decisions document includes ADR-0007.",
      "episodes": [
        "60689f97-4fbc-4780-9675-b7f389c785e4",
        "4f62efa2-3877-4a9a-9ed0-a4a3c41d1295"
      ],
      "expired_at": "2026-08-11T19:56:04.398667Z",
      "valid_at": "2026-08-11T18:25:20.447395Z",
      "invalid_at": "2026-08-11T18:29:10.154944Z",
      "attributes": {}
    },
    {
      "uuid": "4c50005b-4239-4c37-b5b1-10bfbc2ea8cf",
      "group_id": "cursor-governance",
      "source_node_uuid": "cb164ac2-f77b-4e4a-8f39-022be88980b0",
      "target_node_uuid": "b3432d25-2f88-4f2b-8df4-af2ac038dcd5",
      "created_at": "2026-08-11T19:29:16.566073Z",
      "name": "INCLUDES",
      "fact": "Cursor-Governance involves the reconciliation of Claude settings.",
      "episodes": [
        "19544f90-2136-470e-a7fb-c79e903d7e42"
      ],
      "expired_at": "2026-08-11T19:42:36.514138Z",
      "valid_at": "2026-08-11T19:29:03.826084Z",
      "invalid_at": "2026-08-11T19:42:24.039587Z",
      "attributes": {}
    },
    {
      "uuid": "d2454843-a7d2-4f75-9c5b-c37229edfcfe",
      "group_id": "cursor-governance",
      "source_node_uuid": "4e44b376-6848-4387-ae0a-2791cc47dbba",
      "target_node_uuid": "b3666afd-acf5-4b7e-9c88-0ad30a08aa32",
      "created_at": "2026-08-12T15:29:12.387770Z",
      "name": "RUNS",
      "fact": "claude-code is running a diff to check configurations in the environment for the adapter.",
      "episodes": [
        "f94f3ea7-bfe3-4343-918f-8b659ab823a0"
      ],
      "expired_at": null,
      "valid_at": "2026-08-12T15:28:51.893605Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "b5a5421a-de9e-4d82-972f-c279f6bce2a5",
      "group_id": "cursor-governance",
      "source_node_uuid": "7d24a4e0-40c4-45ad-b9ea-f28295aa25b8",
      "target_node_uuid": "ccb00198-0469-4ee2-ad06-d8ea48d89ebc",
      "created_at": "2026-08-11T21:59:02.929518Z",
      "name": "ENABLES",
      "fact": "The converged l9-graphiti-memory task implements local ACL bypass, allowing the CLI to honor local write namespaces.",
      "episodes": [
        "a33d8461-47a2-40de-9e3e-aaec349eed53"
      ],
      "expired_at": "2026-08-11T22:06:31.414916Z",
      "valid_at": "2026-08-11T21:58:50.630312Z",
      "invalid_at": "2026-08-11T22:06:18.830901Z",
      "attributes": {}
    },
    {
      "uuid": "334c2995-7672-4d93-9538-8bbb6d6d5761",
      "group_id": "cursor-governance",
      "source_node_uuid": "0053d697-3322-4cc9-8423-5636fc4da56c",
      "target_node_uuid": "ad4cc0a5-fa14-4522-ab1e-09c8fe4eccd6",
      "created_at": "2026-08-11T18:57:22.469907Z",
      "name": "ASSOCIATED_WITH",
      "fact": "Commit 46271b8 is associated with the l9-devpack-program-execution-hardening campaign.",
      "episodes": [
        "9f8908f9-bc78-48b8-a30a-cd27c09617cc"
      ],
      "expired_at": null,
      "valid_at": "2026-08-11T18:57:09.265124Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "629c8151-9ec9-434a-a98d-81a0bc79c0ae",
      "group_id": "cursor-governance",
      "source_node_uuid": "2fcdf841-114e-488d-b5ea-037110f79876",
      "target_node_uuid": "50e9dd5c-9f3c-4431-ba07-5d32d5a390ab",
      "created_at": "2026-08-11T19:04:17.935775Z",
      "name": "REQUIRES_CLEANUP",
      "fact": "CI needs cleanup of the CI_PIPELINE to resolve the issues with LLM-Router branch protection.",
      "episodes": [
        "7c856b9a-3504-4bfe-98a0-bcdd841120a3"
      ],
      "expired_at": null,
      "valid_at": "2026-08-11T19:04:07.690173Z",
      "invalid_at": null,
      "attributes": {}
    },
    {
      "uuid": "689e8575-4063-4779-ba87-a2edf5a81807",
      "group_id": "cursor-governance",
      "source_node_uuid": "39311354-2c2a-4de4-b2f1-21c4da156959",
      "target_node_uuid": "42625ac1-c98f-478f-bce9-0c00cb62dbfa",
      "created_at": "2026-08-02T21:45:37.660657Z",
      "name": "PAIRS_WITH",
      "fact": "LL-002 is associated with the AUTHORIZATION_MODEL, which outlines restrictions during the execution process.",
      "episodes": [
        "a1786301-2063-41f6-927b-a0db5a999702"
      ],
      "expired_at": null,
      "valid_at": "2026-08-02T21:45:26.070340Z",
      "invalid_at": null,
      "attributes": {}
    }
  ]
}
{
  "acquired": true,
  "graphiti": {
    "memory_satisfied_for": [
      "a08dab3177cfb10d",
      "gmp:phase_lock"
    ],
    "phase_lock": "granted",
    "state_file": "/Users/ib-mac/.cursor/graphiti-state/7fd9eb94-d232-48e4-a068-1dbd408bbfb0.json"
  },
  "namespace": "cursor-governance",
  "server_granted": true,
  "session_id": "7fd9eb94-d232-48e4-a068-1dbd408bbfb0",
  "task": "backup local unpushed WIP + kernel-pack branch default docs to remote",
  "transport": "cursor-graphiti-phase-lock"
}
