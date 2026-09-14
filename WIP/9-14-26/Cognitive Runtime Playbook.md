# L9 Cognitive Runtime — ChatGPT Custom MCP App Finish-Line Runbook

**Objective:** Register the production-ready L9 Cognitive Runtime `/v1/mcp` endpoint as a
ChatGPT custom app, validate discovery and OAuth, prove real tool invocation from ChatGPT,
then publish it to the workspace.

**Terminal state:** `CHATGPT_CUSTOM_MCP_APP_PUBLISHED_AND_PROVEN`

## 0. Entry Gate

Do not begin ChatGPT registration until all deployment work is on the exact intended
release revision.

Record:

```text
Repository:
https://github.com/Quantum-L9/l9-cognitive-runtime
Git SHA:
<FINAL_MAIN_SHA>
Image digest:
sha256:<FINAL_IMAGE_DIGEST>
MCP endpoint:
https://<FINAL_HOST>/v1/mcp
OAuth issuer:
<ISSUER>
OAuth audience:
<AUDIENCE>
Deployment environment:
<STAGING_OR_PRODUCTION>
```

Required before proceeding:

- [ ] MCP SDK 2.1.1 upgrade merged and proven.
- [ ] MCP-011 OAuth/OIDC protection merged and proven.
- [ ] Exact immutable image deployed.
- [ ] `/healthz` succeeds.
- [ ] `/readyz` succeeds.
- [ ] Direct MCP `initialize` succeeds.
- [ ] Direct `tools/list` succeeds.
- [ ] Direct `runtime_capabilities` succeeds.
- [ ] Direct `plan_kernel_activation` succeeds.
- [ ] Direct `compile_runtime` succeeds with a real governed ContextSnapshot.
- [ ] Release-staging path is either proven or its remaining external deployment boundary is explicitly documented.
- [ ] No unresolved authentication defect exists.
- [ ] No mutable image tag is being used as release evidence.

STOP if the deployed image digest does not correspond to the intended Git SHA.

## 1. Freeze the MCP Contract

Treat the MCP tool surface as release API.

Before registering the app, capture the live server's `tools/list`.

Expected tool surface, if Phases 1 through 4 have not intentionally changed it:

```text
runtime_capabilities
compile_intent
plan_kernel_activation
compile_runtime
validate_runtime_bundle
```

Verify:

- [ ] Exactly the intended tools are exposed.
- [ ] No shell tool exists.
- [ ] No repository mutation tool exists.
- [ ] No execution-provider tool exists.
- [ ] No debugging/admin tool leaked into the production surface.
- [ ] Tool descriptions accurately describe behavior.
- [ ] Tool parameter schemas match deployed behavior.
- [ ] ContextSnapshot schemas are correct.
- [ ] Authentication concerns are absent from compiler-domain inputs.
- [ ] Tool names are stable.
- [ ] Required parameters are stable.
- [ ] Return contracts are stable.

Gate: Resolve tool-schema defects before ChatGPT registration.

ChatGPT may cache the approved tool/input snapshot after publish. Server-side changes are not
always adopted automatically, and incompatible later changes can cause calls to fail until an
admin refreshes or reviews the app. See OpenAI Help Center:
https://help.openai.com/en/articles/11487775-connectors-in-chatgpt

## 2. Verify OAuth Readiness

Before opening ChatGPT, validate the deployed OAuth/OIDC resource-server contract.

Verify:

```text
/.well-known/openid-configuration
or
/.well-known/oauth-authorization-server
```

Confirm the appropriate discovery metadata exposes the configuration ChatGPT needs.

Required:

- [ ] Valid issuer.
- [ ] Valid authorization endpoint.
- [ ] Valid token endpoint.
- [ ] Valid JWKS URI.
- [ ] Expected audience/resource semantics.
- [ ] Refresh-token support.
- [ ] `offline_access` or provider-equivalent capability when required.
- [ ] Correct scopes.
- [ ] Signed tokens accepted.
- [ ] Wrong issuer rejected.
- [ ] Wrong audience rejected.
- [ ] Expired tokens rejected.
- [ ] Invalid signatures rejected.
- [ ] Missing bearer token rejected.
- [ ] Correct `WWW-Authenticate` behavior where applicable.

OpenAI specifically recommends ensuring the OAuth/OIDC provider can issue refresh tokens.
For OIDC, `offline_access` is the standard mechanism, and the capability should be
advertised through discovery metadata. Without refresh-token support, ChatGPT may lose
access after the initial authorization expires. (OpenAI Help Center)

STOP if long-lived ChatGPT connectivity cannot renew authorization correctly.

## 3. Enter ChatGPT Developer Mode

Perform the remaining steps from ChatGPT web.

For a workspace Admin/Owner:

```text
Workspace Settings
  → Apps
  → Create
```

Developer mode must be enabled for the account performing the registration.

Depending on workspace type and permissions, developer-mode controls may also appear under:

```text
Settings
  → Apps
  → Advanced Settings
```

OpenAI currently limits full MCP custom-app functionality to supported workspace plans on
ChatGPT web. Only Admins/Owners can publish the resulting app. (OpenAI Help Center)

## 4. Create the Draft App

Create a new custom app.

Recommended metadata:

```text
Name:
L9 Cognitive Runtime
Description:
Deterministic task-scoped cognitive compilation for governed L9 missions.
MCP endpoint:
https://<FINAL_HOST>/v1/mcp
Authentication:
OAuth / OIDC
```

Use the exact final `/v1/mcp` URL.

Do not register:

```text
/
```

or:

```text
/healthz
```

or:

```text
/readyz
```

or an internal/private hostname that ChatGPT cannot reach through the selected connection
path.

If ChatGPT supplies an OAuth redirect/callback URI during configuration, register that
exact URI with the identity provider.

Do not invent or approximate callback URLs.

## 5. Scan Tools

Click:

```text
Scan Tools
```

If prompted for OAuth authorization, complete authorization and allow the scan to finish.

OpenAI's current setup flow explicitly performs authentication during tool scanning when
OAuth is configured. (OpenAI Help Center)

Compare the discovered surface against the previously frozen live `tools/list`.

Expected:

```text
runtime_capabilities
compile_intent
plan_kernel_activation
compile_runtime
validate_runtime_bundle
```

For each discovered tool verify:

- [ ] Name matches.
- [ ] Description matches.
- [ ] Input schema matches.
- [ ] Required fields match.
- [ ] No unexpected parameters.
- [ ] No unexpected tools.
- [ ] No write/mutation classification appears unexpectedly.
- [ ] No auth token or credential is exposed as a normal tool argument.
- [ ] ContextSnapshot remains governed domain input, not login plumbing.

Scan Gate

PASS

```text
CHATGPT_SCAN == LIVE_SERVER_TOOL_CONTRACT
```

FAIL

Any of:

```text
missing tool
unexpected tool
schema mismatch
wrong required parameter
wrong endpoint
OAuth failure
authorization loop
tool scan timeout
```

If failed, repair the server or authorization configuration first.

Do not click Publish.

## 6. Create the Draft

After the scan is clean, click:

```text
Create
```

Confirm the app appears under:

```text
Workspace Settings
  → Apps
  → Drafts
```

It should also appear for the authorized developer under:

```text
Settings
  → Apps
  → Enabled Apps
```

with the development indicator.

This is still not deployment proof.

It is only registration proof. (OpenAI Help Center)

## 7. Authorization Proof

Authorize the app using a real permitted identity.

Capture sanitized evidence of:

```text
authenticated subject
issuer
audience
scope set
authorization timestamp
```

Never capture:

```text
access token
refresh token
client secret
private key
authorization code
session cookie
```

Verify server-side:

- [ ] Principal is derived from validated OAuth identity.
- [ ] Hosted requests do not use local-stdio.
- [ ] Run storage is principal-scoped.
- [ ] Another principal cannot retrieve this principal's runs.
- [ ] Authentication changes identity/session context only.
- [ ] Authentication does not modify compilation semantics.

## 8. ChatGPT Draft Smoke

Open a new ChatGPT chat.

Select the draft L9 Cognitive Runtime app from the tools/app menu.

ChatGPT app selection applies to the message performing the call. For later fresh calls,
select or @mention the app again as necessary. (OpenAI Help Center)

Run the following smoke sequence in order.

Smoke 1: `runtime_capabilities`

Prompt:

```text
Use L9 Cognitive Runtime and call runtime_capabilities.
Report the runtime version, available capabilities, MCP tool surface,
read-only status, and whether governed ContextSnapshot input is supported.
Do not infer anything that the tool does not return.
```

PASS requires:

- [ ] Actual MCP tool invocation visible.
- [ ] Correct runtime identity.
- [ ] Correct deployed version.
- [ ] Expected capabilities.
- [ ] Expected read-only semantics.
- [ ] No fake or hallucinated capabilities.

Record:

```text
SMOKE-01 = PASS | FAIL
```

## 9. ChatGPT Governed Context Fixture

Use one deterministic fixture for both planning and compilation.

The fixture must contain at least one real typed context item with provenance.

Minimum conceptual fixture:

```yaml
task_scope:
  objective: "Prove ChatGPT-to-L9 Cognitive Runtime MCP deployment."
architecture_constraints:
  - "CompilePipeline remains semantic composition owner."
  - "Authentication terminates at HTTP ingress."
  - "No observability drift."
prior_decisions:
  - decision: "Cog compiles governed task context but does not execute repository mutations."
    provenance: "deployment-smoke-fixture"
evidence_refs:
  - ref: "deployment-release"
    revision: "<FINAL_MAIN_SHA>"
    image_digest: "sha256:<FINAL_IMAGE_DIGEST>"
unresolved_unknowns: []
```

Translate this into the exact currently accepted ContextSnapshot schema.

Do not weaken the schema to accommodate the smoke.

## 10. Smoke 2: `plan_kernel_activation`

Prompt:

```text
Use L9 Cognitive Runtime.
Call plan_kernel_activation for this mission:
"Prove the final ChatGPT MCP deployment path for l9-cognitive-runtime."
Use the governed ContextSnapshot I provide.
Return the selected activation plan, context digest, provenance,
and any unresolved unknowns. Do not compile the runtime yet.
```

Provide the governed fixture.

PASS requires:

- [ ] Actual tool invocation.
- [ ] Context accepted.
- [ ] Context digest present.
- [ ] Activation plan present.
- [ ] Provenance represented.
- [ ] No unauthorized mutation.
- [ ] No unrelated kernels activated without semantic reason.
- [ ] No authentication data appears inside the semantic context.

Record:

```text
PLAN_CONTEXT_DIGEST=<DIGEST>
SMOKE-02=PASS
```

## 11. Smoke 3: `compile_runtime`

In the same controlled test, invoke the compiler using the same mission and same governed
context.

Prompt:

```text
Use L9 Cognitive Runtime.
Call compile_runtime for exactly the same mission and governed
ContextSnapshot used in the previous planning call.
Return only:
run_id
semantic digest
context digest
manifest digest
selected kernels
execution packet identity
provenance summary
unresolved unknowns
Do not execute the resulting packet.
```

PASS requires:

- [ ] Actual MCP invocation.
- [ ] `run_id` present.
- [ ] Semantic digest present.
- [ ] Context digest present.
- [ ] Context digest agrees with the intended governed input.
- [ ] Manifest digest present.
- [ ] Selected kernels present.
- [ ] Execution packet produced.
- [ ] Provenance present.
- [ ] No repository mutation occurred.
- [ ] No graph execution occurred.
- [ ] No provider-side coding action occurred.

Critical comparison:

```text
PLAN_CONTEXT_DIGEST == COMPILE_CONTEXT_DIGEST
```

unless the canonical contract intentionally distinguishes those representations.

Record:

```text
COMPILE_CONTEXT_DIGEST=<DIGEST>
SMOKE-03=PASS
```

## 12. Determinism Re-Proof

Run `compile_runtime` again with exactly the same semantic inputs.

Compare deterministic fields.

Expected invariant:

```text
same semantic mission
+ same governed context
+ same verified kernel pack
+ same compiler revision
=
same semantic compilation result
```

Ephemeral fields such as timestamps or unique run IDs may differ if the canonical schema
defines them as non-semantic.

PASS requires all semantic digests and selected semantic artifacts that are defined as
deterministic to agree.

Record:

```text
SMOKE-04-DETERMINISM=PASS
```

## 13. Negative Auth Smoke

Before publishing, prove that ChatGPT's successful path has not hidden a permissive
server.

Outside ChatGPT, test:

```text
No token
Malformed token
Expired token
Wrong issuer
Wrong audience
Invalid signature
```

Every case must fail closed.

Then re-run one valid ChatGPT tool invocation.

PASS condition:

```text
INVALID_IDENTITIES_REJECTED
AND
VALID_CHATGPT_IDENTITY_ACCEPTED
```

## 14. Draft Acceptance Gate

Do not publish until all are true:

- [ ] Correct final Git SHA deployed
- [ ] Correct immutable image digest deployed
- [ ] Correct `/v1/mcp` endpoint registered
- [ ] OAuth discovery valid
- [ ] Refresh-token path valid
- [ ] Scan Tools completed
- [ ] Discovered tool surface matches server
- [ ] Authorization succeeds
- [ ] `runtime_capabilities` passes from ChatGPT
- [ ] `plan_kernel_activation` passes from ChatGPT
- [ ] `compile_runtime` passes from ChatGPT
- [ ] Real governed ContextSnapshot proven
- [ ] Semantic/context digest evidence captured
- [ ] Determinism re-proof passes
- [ ] Negative auth matrix passes
- [ ] No compiler/auth boundary contamination found
- [ ] No unexpected write tools exposed
- [ ] No unresolved release-blocking UNKNOWN remains

Terminal draft verdict:

```text
CHATGPT_DRAFT_PROVEN
```

Anything less remains:

```text
NOT_READY_TO_PUBLISH
```

## 15. Publish

Publishing requires an Admin/Owner.

Navigate:

```text
Workspace Settings
  → Apps
  → Drafts
  → L9 Cognitive Runtime
  → Publish
```

Review the safety warnings and discovered actions.

OpenAI currently requires Admin/Owner authority for publishing. (OpenAI Help Center)

### Business Workspace

Treat Publish as a particularly hard boundary.

Current OpenAI behavior states that Business custom apps cannot simply be edited in place
after publication. Changes to tools or metadata require recreation and republication.
(OpenAI Help Center)

Therefore:

```text
DO NOT PUBLISH UNTIL TOOL CONTRACT IS FROZEN
```

### Enterprise / Edu

Before completing publication:

```text
Configure Actions
Configure Access
```

Grant only intended tool actions and intended users/groups.

New or changed actions should be reviewed explicitly rather than silently trusted.
(OpenAI Help Center)

Then complete:

```text
Publish
```

## 16. Post-Publish Proof

Do not stop at the Publish confirmation.

Open a completely new ChatGPT chat as an authorized workspace user.

Locate:

```text
L9 Cognitive Runtime
```

The app should now appear as the published custom app rather than merely the developer
draft. (OpenAI Help Center)

Perform two final calls:

```text
runtime_capabilities
compile_runtime
```

Use a governed context fixture.

Verify:

- [ ] Published app resolves.
- [ ] OAuth completes.
- [ ] Real tool call occurs.
- [ ] Correct runtime responds.
- [ ] Correct image/revision can be tied to deployment evidence.
- [ ] Compilation succeeds.
- [ ] Provenance is intact.
- [ ] Context digest is intact.
- [ ] No draft-only behavior was required.

Terminal runtime verdict:

```text
PUBLISHED_CHATGPT_CALL = PASS
```

## 17. Evidence Capture

Create (keep it next to this playbook, not at the repo root):

```text
WIP/8-31-26/FINAL_FINDINGS-CHATGPT-CUSTOM-MCP-PUBLISH.md
```

Record:

```yaml
verdict: PASS | BLOCKED | UNKNOWN
repository:
  sha: "<SHA>"
deployment:
  image_digest: "sha256:<DIGEST>"
  endpoint: "https://<HOST>/v1/mcp"
  environment: "<ENVIRONMENT>"
chatgpt_app:
  name: "L9 Cognitive Runtime"
  status: "PUBLISHED"
  tool_scan: "PASS"
  authorization: "PASS"
  post_publish_call: "PASS"
tools:
  expected:
    - runtime_capabilities
    - compile_intent
    - plan_kernel_activation
    - compile_runtime
    - validate_runtime_bundle
smoke:
  runtime_capabilities: PASS
  plan_kernel_activation: PASS
  compile_runtime: PASS
  deterministic_recompile: PASS
  negative_auth_matrix: PASS
evidence:
  context_digest: "<DIGEST>"
  semantic_digest: "<DIGEST>"
  manifest_digest: "<DIGEST>"
  run_id: "<SANITIZED_RUN_ID>"
security:
  oauth_oidc: PASS
  principal_binding: PASS
  cross_principal_isolation: PASS
  credentials_committed: false
unknowns: []
terminal_state: "CHATGPT_CUSTOM_MCP_APP_PUBLISHED_AND_PROVEN"
```

Never include credentials or bearer tokens.

## 18. Final Operational Test

Start an ordinary new ChatGPT conversation.

Invoke:

```text
@L9 Cognitive Runtime
```

Ask it to compile a legitimate governed mission.

The finish line is crossed only when the following chain is real:

```text
ChatGPT
    │
    ▼
Published L9 Cognitive Runtime custom app
    │
    ▼
OAuth/OIDC
    │
    ▼
HTTPS /v1/mcp
    │
    ▼
MCPServer
    │
    ▼
CognitiveRuntimeService
    │
    ▼
CompilePipeline
    │
    ▼
CompiledTaskContext
    │
    ▼
Governed execution packet
```

No parallel semantic compiler.

No ChatGPT-specific compiler.

No authentication inside CompilePipeline.

No deployment configuration masquerading as proof.

No repository mutation by Cog.

## Terminal Gate

```yaml
finish_line:
  app_registered: true
  tools_scanned: true
  oauth_authorized: true
  draft_chatgpt_calls_proven: true
  governed_context_proven: true
  deterministic_compile_proven: true
  negative_auth_proven: true
  app_published: true
  published_chatgpt_call_proven: true
  verdict: CHATGPT_CUSTOM_MCP_APP_PUBLISHED_AND_PROVEN
```

If any field is false:

```text
THE DEPLOYMENT IS NOT FINISHED.
```
