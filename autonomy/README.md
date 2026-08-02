# L9 Enforceable Autonomy Control Plane

Wave 1 converts autonomy orchestration from IDE convention into validated,
machine-readable contracts.

## Properties enforced

- Campaigns require resolved base SHAs.
- Autonomous merge, admin merge, and force push are forbidden.
- Executors require synthesis inputs.
- Mutation roles require exclusive write claims.
- Read-only roles cannot request write claims.
- Reviewers must be independent from executors.
- Reviews must consume verifier outputs.
- Every action declares a typed completion artifact.
- Role cardinality is validated before execution.
- Action graphs must be acyclic and dependency-complete.

## Compile the W7 graph

Replace the example base SHA first:

```bash
python - <<'PY'
import json
from pathlib import Path
path = Path("autonomy/examples/w7-campaign.json")
data = json.loads(path.read_text())
data["base_state"]["commit_sha"] = "YOUR_RESOLVED_BASE_SHA"
path.write_text(json.dumps(data, indent=2) + "\n")
PY
```

Compile:

```bash
python -m autonomy.compiler.graph_compiler \
  --campaign autonomy/examples/w7-campaign.json \
  --deployment autonomy/examples/w7-deployment.json \
  --actions autonomy/examples/w7-actions.json \
  --output .l9/autonomy/w7-compiled-graph.json
```

Validate:

```bash
python -m autonomy.validation.graph_linter \
  --graph .l9/autonomy/w7-compiled-graph.json \
  --deployment autonomy/examples/w7-deployment.json
```

Run tests:

```bash
python -m unittest discover -s autonomy/tests -v
```

## Wave boundaries

Wave 1 only compiles and validates authority and topology.

It intentionally does not yet grant leases or mediate tools. Runtime mutation
must remain disabled until Wave 2 is installed and its capability gateway is
active.
