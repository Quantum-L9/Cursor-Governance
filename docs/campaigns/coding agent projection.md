
{
  "expected": "69134217267626182ac95182a56d1d9bc296135e",
  "observed": "39ebfb6096eaf5a5d17447b077d4b3342efc33a6",
  "reason": "AUTHORITY_REVISION_MISMATCH",
  "status": "STALE",
  "verifier": "l9-coding-agent/scripts/verify_canonical_binding.py"
}
=====
{
  "bundle_revision": "7252e3b43c75ad0eab9483feb1552ba504ecbcec",
  "detail": "upstream not observed (no verified Quantum-L9/.github checkout; set L9_AUTHORITY_ROOT)",
  "enforcement": "report_only",
  "mutation_gate": "ops/autonomy/coding_agent_binding_gate.py",
  "profile_ref": "l9.projection/coding-agent-execution@1",
  "rejected_authority_roots": [
    "/Users/ib-mac/.l9/repos/Quantum-L9-github/.github is not the top of a git checkout"
  ],
  "role": "consumer_verifier",
  "schema": "l9.coding-projection-status/v3",
  "status": "UNVERIFIED"
}
====
{
  "applicable_invariants": [
    {
      "digest": "sha256:455e1438325c016de730450688af7786fc0722cd23dc9f86c9842d7f892d71a3",
      "id": "L9-AUTH-001"
    },
    {
      "digest": "sha256:675fde10738de03a4c6cb58bc643f72fb3cc594365afe9f81c19b78761a9eedf",
      "id": "L9-AUTH-002"
    },
    {
      "digest": "sha256:1b010b56e367d576c95134b9d221a0a80f1426f995613b5a7264b9fe4d01392b",
      "id": "L9-OWNER-001"
    },
    {
      "digest": "sha256:429e7e15ea57a53a9d4381f69b794edcf22a95f1d903eb9e0cb5173edfebef57",
      "id": "L9-MONOTONIC-001"
    },
    {
      "digest": "sha256:958fcb7c15b3166b72b78755fc17d626f728a2c8a3b5d3921b0be734b69e7957",
      "id": "L9-PROMOTION-001"
    },
    {
      "digest": "sha256:0d743a935791931b80ec3d6aa33ae2349772d90efe901cfb7d51c54a2286d563",
      "id": "L9-DERIVED-001"
    },
    {
      "digest": "sha256:17284bdcc1acb57c8af9b88aa4953f0f12f084ba3bf10580521c1cda55df85bb",
      "id": "L9-EVIDENCE-001"
    },
    {
      "digest": "sha256:4abc34513df63ab83524df9bbf4dafd8633ce8f9c7cc923d8908c144c75eee7f",
      "id": "L9-ASSURANCE-001"
    },
    {
      "digest": "sha256:97a201530cede20ed28333d2952413d339e6ca26b66446830a4d89edd4ddc226",
      "id": "L9-UNKNOWN-001"
    },
    {
      "digest": "sha256:36e3262e23a34be711d51ee1c1d0e56a56976214519acf49f1ebaa56862f20e8",
      "id": "L9-DEGRADE-001"
    },
    {
      "digest": "sha256:e73b9bc3fb78356272b8a43fe45c0c8c214ed3d9fb8b845de67c433d8b11c70d",
      "id": "L9-PROV-001"
    },
    {
      "digest": "sha256:623bb67ab1e459c4b1142f5a8fca29c4c4e38f450a2a427593d0d28b42eb4dd0",
      "id": "L9-COORD-001"
    },
    {
      "digest": "sha256:530af2f8fd9e5319b195a98163b70f6f76a0bbe4d11e51920abd17a4801ae4ee",
      "id": "L9-COMPAT-001"
    },
    {
      "digest": "sha256:fffd0d71b92a2fb1faf3e7a2e098ff7eb2a81586f4f04ae0101e7597b267f303",
      "id": "L9-REVISION-001"
    },
    {
      "digest": "sha256:422cb958e53c17d4147ec90cbebecaa85209da7cf2d0971f802aa1ef2274e7e3",
      "id": "L9-ADMISSION-001"
    },
    {
      "digest": "sha256:c235a187286a8827dab9ebe996968491d5509f79b887d255fd80d32c6ad2f39f",
      "id": "L9-PROJECTION-001"
    },
    {
      "digest": "sha256:2bad12d6ce7aa37bd1f1eff32340fa2eb75f8f78052894f216c41f335c68a109",
      "id": "L9-VALIDATION-001"
    },
    {
      "digest": "sha256:4e90a6f5ad4555dfa5c3e148e20c793f104c05e366a9985a6e2e0391d41ff9a4",
      "id": "L9-CORRECTNESS-001"
    },
    {
      "digest": "sha256:5f23334e95195ba009b389de842f3781a32f13157a8b70e867591ec00164fd6c",
      "id": "L9-GLOBALIZATION-001"
    }
  ],
  "authority_root": {
    "content_basis": "pinned_commit_objects_hash_verified",
    "repository": "Quantum-L9/.github",
    "revision": "3dcdeaae355b6de08562993f705084d7a3714bfd",
    "revision_basis": "caller_pinned_not_authenticated"
  },
  "bundle": {
    "authority": {
      "repository": "Quantum-L9/.github",
      "revision": "7252e3b43c75ad0eab9483feb1552ba504ecbcec"
    },
    "lock_digest": "sha256:c2a4b6d9690c443d1eb6b5686c3141f216d4b33efe43afa73c85bca671990bad",
    "path": "/Users/ib-mac/.cursor-governance/generated/governance/coding_agent_execution",
    "producer": {
      "compiler": "l9-semantic-compiler",
      "repository": "Quantum-L9/l9-semantic-compiler-engine",
      "revision": "b9b4892c26b706cced32b398fca6eeec3ad86efc",
      "revision_basis": "caller_asserted",
      "version": "0.9.3"
    },
    "producer_authentication": "unauthenticated_unkeyed_receipt"
  },
  "components": [
    {
      "projection_digest": "sha256:0832ad89fdc7c88a6c7b6f835a3af07688553c935b0b60db89026b0b630882fc",
      "receipt_identity": "l9.receipt-instance/d8d9360dcb5ea0a3850677e0ca3abc8c3586a644d8a438234c7ebd9e7198dc50",
      "source_class": "invariants",
      "source_digest": "sha256:771e3509703ea7d177a4bbac965e126f77f390ec359d1544854d95ec4374082a",
      "source_ref": "l9.source/invariants@1"
    },
    {
      "projection_digest": "sha256:f9ae8897731f3a47de1d6e1d331eb452f40927587e6389bb3aee0964e72627d2",
      "receipt_identity": "l9.receipt-instance/d4891b441ab1c10d654ca9c32ca13f9554e341ff732d3c2848115922f3b8aa89",
      "source_class": "contracts",
      "source_digest": "sha256:f1fcc979534d0aa34783710657ae36d765f7078e6ab20dc3b11a31d576539d79",
      "source_ref": "l9.source/contracts@1"
    },
    {
      "projection_digest": "sha256:85d3fa331ace18a6192f5d6eb05523773c6fbe9b651dbb07b92d1dd7d453e88f",
      "receipt_identity": "l9.receipt-instance/bd22b588c5cfa55521cec42870ff79c9effa2aa3c36107642ccbb77e34db85cb",
      "source_class": "authority_model",
      "source_digest": "sha256:9303ee5910f3db2b10abe71bdcb5e360128ee77e7e4bd3ebe9e05dba77018620",
      "source_ref": "l9.source/authority-model@1"
    }
  ],
  "profile": {
    "digest": "sha256:27941a4987ec3861f4e312d991d8016e0769dafa5a5ed6026947c8dfdccc6346",
    "ref": "l9.projection/coding-agent-execution@1"
  },
  "projected_invariant_count": 19,
  "projection": {
    "digest": "sha256:0832ad89fdc7c88a6c7b6f835a3af07688553c935b0b60db89026b0b630882fc",
    "file_digest": "sha256:8ffa92a1c7bc6cb22879b416ef4c867877d2de81990ffaf2da61138ee3e8f581"
  },
  "reason": "PROJECTION_BUNDLE_VERIFIED",
  "receipt": {
    "digest": "sha256:4b98844cfa15c925ba36a7401938043e69a6c3fb66ef6cdbf671f991a86644c3",
    "identity": "l9.receipt-instance/d8d9360dcb5ea0a3850677e0ca3abc8c3586a644d8a438234c7ebd9e7198dc50",
    "producer": {
      "compiler": "l9-semantic-compiler",
      "version": "0.9.3"
    },
    "producer_authentication": "unauthenticated_unkeyed_receipt"
  },
  "source": {
    "digest": "sha256:771e3509703ea7d177a4bbac965e126f77f390ec359d1544854d95ec4374082a",
    "path": "semantics/invariants.yaml",
    "ref": "l9.source/invariants@1"
  },
  "status": "BOUND",
  "verifier": "l9-coding-agent/scripts/verify_canonical_binding.py"
}
