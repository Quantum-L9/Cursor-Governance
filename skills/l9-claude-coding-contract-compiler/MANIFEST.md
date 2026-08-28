# MANIFEST — l9-claude-coding-contract-compiler v2.7.0

Current authoritative inventory for the repaired standalone compiler Skill.

## Release identity

- Version: `2.7.0`
- Repair date: `2026-08-27`
- Source pack: `claude-coding-contract-compiler-v2.6.2(4).zip`
- Source pack SHA-256: `6de65f688240ba3a94c4841884034b67713d87e30c0b7c2eb7bc157df89f5cb4`
- Packaging target: ChatGPT Skill archive named exactly `skill.zip`

## Release law

- Explicit target-native cold-resume and commit-gate commands; no implicit ecosystem fallback.
- Exactly one local commit per contract on one shared campaign branch.
- Contract N+1 preflight proves contract N with the exact predecessor HEAD subject plus only N's dedicated `verify_proof` completion proof.
- Repository-wide predecessor commit gates are never replayed merely for chaining.
- Internal seams use `committed_and_validated`.
- No remote delivery between contracts.
- Terminal contract alone may run exact `make pr` once; direct push/PR creation remains denied.

## Inventory summary

- Indexed files excluding this manifest: **48**
- Pack files including this manifest: **49**
- `agents`: **1**
- `examples`: **3**
- `references`: **12**
- `root`: **11**
- `schemas`: **15**
- `scripts`: **7**

`MANIFEST.md` is intentionally not self-hashed. Every other bundled file is indexed below.

## File inventory

| File | Lines | SHA-256 |
|---|---:|---|
| `ALIGNMENT_REPORT.md` | 83 | `fba6db198de265c85aec762b532f865b65c321fab3911736a8ffe9d903d3a3b7` |
| `CHANGE_SUMMARY.md` | 199 | `446fc60c13ad09e81293531e3a4a4cf932abc56c59b4d62413694bcd4b80f792` |
| `PROVENANCE_MAP.yaml` | 85 | `6e45dadedb0797bf378cfce975384afb41ae23645442ba45432339a21b6ab1aa` |
| `README.md` | 73 | `9d859c8f7cfc51e73e4d5fe39df55caf349c3b298aa262b212e13ca030ee9f2a` |
| `REGRESSION_GUARD.md` | 45 | `7bf22648c4a85a169cc51f4ac2797644fca2fadcbc263900d7651a2aa17a4ace` |
| `RUNBOOK.md` | 129 | `495ae2acf53e96e0f3a7dfdd3122dd29713dc52af281646cf12e5f0998555043` |
| `SKILL.md` | 214 | `804de314d08ee3f7920d094b11013d32308a0b8120f27e115d4ec4e10281881b` |
| `VALIDATION.md` | 71 | `76b5bf9fd9aa402b8f7e5ca21cf1f469d7325ad0820a1b35a2e550ce656e5dae` |
| `agents/openai.yaml` | 2 | `84c6c0d84c3afb0c4c46a425b299b2e80e7d664f308e79b1ee8cf059332ea678` |
| `examples/campaign-spec.example.yaml` | 207 | `6838e90448d57a54aa55ddda94c6bac42fa853b41116b758e87bffc07a218727` |
| `examples/campaign-spec.go.example.yaml` | 47 | `54db0e3e823b850314798891da30f15b318a79b24bfb40836bd9acce42a3e822` |
| `examples/campaign-spec.python.example.yaml` | 59 | `741b0e0b8330cc0c48cf805de54b25a742537e999d1e82ae905f37e34a381932` |
| `expertise_model.yaml` | 81 | `7ce38d9dafa6c1fefc64f0f5cbfa2a55008b5c0a1278d43bce04d8e67f17b10a` |
| `references/binding-directives.md` | 35 | `36faf3d6977be2ba7467e300e8a5209065a3978bdf7c83d9366f028a162ab734` |
| `references/canonical-spec.md` | 133 | `f8c6d0e3b4cf593526765177ceda323f2b6981f216dd4cc8bf9ceebc1f3f7a0c` |
| `references/claude-fill-policy.md` | 123 | `d10a730809981bad55a2eabe7d5430522c5a068c2c1af7378bf97a6dc28d5db7` |
| `references/contract-anatomy.md` | 74 | `2d9d9559dc7a01261f3a3e788f210c6adf69dc0bd9fd896b11771403d7ced9f5` |
| `references/dpk-integration.md` | 83 | `5955bf6d8669c035f12aee28842f33f58c8fb60e078f94b74a52ddf12d9a73cf` |
| `references/enforcement-gates.md` | 53 | `9553b61789670bae40d5f91aa5baf4039b1b396015444c7104caf136b07fa641` |
| `references/kernel-fail-closed.md` | 53 | `287c6adcfbe4599f4f20c34f6c6d6eafefd44769593b8df009f8a9f20c6e05bb` |
| `references/kernel-recursive-harden.md` | 195 | `4d2265497839cdc739a658e611bf490f3061e5c30a4bcbe5087f8f3e73641e26` |
| `references/kernel-scope-lock.md` | 40 | `eb52578012bdf0d0b7e599fcdf33e0aa4e329e1215ceaa3cdbb53f7ca6076286` |
| `references/output-modes.md` | 63 | `f4a81119193ebe34460677cfb23d101cceb02b9799a1324dcfb66b76030d14cf` |
| `references/section-contract.md` | 47 | `f8cd61ad97d1a26d374293b6fae791b5780a694f12a9ae4909b70afac65e299e` |
| `references/validation-evidence.md` | 48 | `020616cb99d15b3fe07a4caf5f3ff658167e4b26f8386f500910a3f9b1792572` |
| `schemas/campaign-spec.schema.json` | 362 | `7faf33435c500eb0138de6bf8964eb2f68b5b582999041f00f6073ec5c2a20bd` |
| `schemas/coding-contract.schema.json` | 416 | `de3cb59bc24081e3a0e97168c296466cf0d0ebc7e8a72bad3c8764ed267bc8f0` |
| `schemas/convergence-report.schema.json` | 117 | `345afeafb11aa58a2bb36363038240ebbbc3b753fdb15c93d632b92e4d47fa40` |
| `schemas/delta-report.schema.json` | 115 | `fe00411582e034c924b191142b7161fca19dd073a165f915e0ee5f63d708b7be` |
| `schemas/dpk-alert-runbook.schema.json` | 55 | `43c838bbe31fb2708c4a7504296b580d0eec741de464f005a1231b89bdcbd51d` |
| `schemas/dpk-debt-register.schema.json` | 70 | `805d28514649840e673b4b9741f1bf979c541d3f4dde0e8914e4e501b9095cd0` |
| `schemas/dpk-manifest.schema.json` | 120 | `12dd9c54b6ff107dc4558982272dae23874b024f2b8be5055c08423858a12d03` |
| `schemas/dpk-readiness-score.schema.json` | 84 | `f1e920038cef17b97db4a585c8faed86b924f8c4bd43808c311bb1236443bb08` |
| `schemas/dpk-task-contract.schema.json` | 82 | `7d42b8df918de1154a07d923ac14246d8ec93836a6b2fef1f116260dd1de3bca` |
| `schemas/evidence-record.schema.json` | 145 | `24f56ecc5963c134c2d9c6c99714365332e01e82cd76f966c1307dadeb762245` |
| `schemas/improvement-log.schema.json` | 85 | `10aabc3d5ab0139f2e205aa9310ba57971d7d59cd1eae28dc3f59932d69881a8` |
| `schemas/improvement-report.schema.json` | 175 | `6b39c69b718595afc23bbb56277c89d5f7372aa0e660f69a30815c1f2853f67d` |
| `schemas/promotion-decision.schema.json` | 100 | `133fac1086a0e1d1184864d83119a01704fd5a0cd75a76843f75e1353709259a` |
| `schemas/scope-lock.schema.json` | 78 | `7a38718a1586eca01ebbe854b7cfa7648874f19a73a358d77df8e2138b780795` |
| `schemas/validation-report.schema.json` | 141 | `eab9ca887284895ba53ba9632a9542af620be6f2e97ce791dedc4dedf92b1adb` |
| `scripts/compile_contract.py` | 417 | `5025dcc8143fbe3a802ca7002fa651f8bd10039b54d7356b9dff9ef4392c01d4` |
| `scripts/generate_claude_settings.py` | 160 | `3bb0607fd5b2fb528db749f3ab7494217b681a04d005141452e49642907b79b9` |
| `scripts/generate_preflight.py` | 84 | `5cadfe911d668f66b623ea9530ea9939d1135da76158f8f1d533cbe88dde37d5` |
| `scripts/plan_decomposition.py` | 113 | `23f21c5886dd5f0cce4e17bc49e4493601ddb9a5083bb09a46c9c5aee1dcee32` |
| `scripts/test_target_validation.py` | 242 | `c22216ec16dc155d132d9526e1f5ec008e486c6c1de993bdcc9d6170058a8ea8` |
| `scripts/validate_chain.py` | 181 | `68a85e368fa274247d3e50524a4c2ae3ab52249c6c6315f0bc166a0b344b170a` |
| `scripts/validate_contract.py` | 191 | `2b65832c158cf5429d75c7da5751838361772fa229afb0b1da927abc77cdb4c1` |
| `skill_intelligence_report.yaml` | 174 | `b71ec3b40067f2268c687b12e88dfdc68d2ed608b00518befd77e21b92556670` |

## Validation status

- JSON schemas: 15/15 parse.
- Python scripts: syntax compile PASS.
- Target-validation regression suite: 11/11 PASS, including explicit no-replay predecessor proof.
- Node fixture: 9/9 contract validation PASS; chain VALID; explicit npm preserved.
- Python fixture: 2/2 PASS; chain VALID; zero undeclared npm.
- Go fixture: 1/1 PASS; chain VALID; zero undeclared npm/Python.
- Real Git predecessor/branch preflight regression: PASS.
- Exactly one local commit per contract on one branch: PASS.
- Exactly one terminal `make pr` authority and zero nonterminal delivery authority: PASS.
- Exemplary-tier validator: PASS.
- ChatGPT Skill validator: PASS.
- Cursor-Governance remediation compatibility compile: 7/7 PASS; chain VALID; zero npm fallback; one terminal `make pr`; predecessor chain uses dedicated completion proof only.
