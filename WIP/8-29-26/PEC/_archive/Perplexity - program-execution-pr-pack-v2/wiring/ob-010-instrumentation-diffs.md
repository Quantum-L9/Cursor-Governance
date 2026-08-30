# OB-010 instrumentation wiring

`ops/lib/telemetry.py` is new and tested (see `tests/tools/test_telemetry.py`)
but does nothing until it is called. Apply these four call-site edits to
the files this pack already shipped in PE-010/EN-010/SC-010. Each is a
small, additive diff — no existing logic changes, only new `emit(...)`
calls at points that already exist as function boundaries.

## 1. tools/agent_git.py

Add near the top:
```python
from ops.lib.telemetry import emit
```

In `acquire_lease`, right before `raise RuntimeError(f"lease busy: ...")`:
```python
        raise RuntimeError(f"lease busy: {holder['agent_id']} holds {path.name}")
```
becomes:
```python
        emit("scope_violation", node_id=os.environ.get("L9_NODE_ID", "unknown"),
             agent_id=agent_id, detail={"reason": "lease_busy", "scope": scope, "holder": holder["agent_id"]})
        raise RuntimeError(f"lease busy: {holder['agent_id']} holds {path.name}")
```

In `journal_reclaim`, after the existing journal write:
```python
    with open(journal_dir / "git_ops.jsonl", "a") as f:
        f.write(json.dumps({"event": "lease_reclaimed", ...}) + "\n")
    emit("lease_reclaimed", node_id=os.environ.get("L9_NODE_ID", "unknown"), detail={"scope": scope, "prior_holder": holder})
```

In `cmd_push`, in the retry-exhaustion branch:
```python
        print("FAIL: push exhausted retries; re-run after peer branch settles.")
        emit("push_retry_exhausted", node_id=os.environ.get("L9_NODE_ID", "unknown"),
             agent_id=args.agent_id, detail={"branch": branch, "attempts": attempts})
        sys.exit(1)
```

## 2. tools/check_feature_tree.py

Add near the top:
```python
from ops.lib.telemetry import emit
```

In `main()`, in the `except TreeError as e:` block, right after building `verdict`:
```python
    except TreeError as e:
        verdict.update({"verdict": "FAIL", "error_code": e.code, "error_message": e.message})
        if e.code in ("FT005", "FT031"):
            emit("scope_violation", node_id=args.node or "unknown",
                 detail={"error_code": e.code, "error_message": e.message})
        print(...)
```

## 3. tools/environment_lease.py

Add near the top:
```python
from ops.lib.telemetry import emit
```

At the end of `cmd_claim`, after the lease file is written:
```python
    lease_path(Path(args.reports_dir), args.node_id).write_text(json.dumps(lease, indent=2))
    emit("lease_acquired", node_id=args.node_id, detail={"db_branch": args.db_branch, "port_range": args.port_range})
    print(f"PASS: claimed environment lease for {args.node_id}")
```

At the end of `cmd_release`:
```python
    path.write_text(json.dumps(lease, indent=2))
    emit("lease_released", node_id=args.node_id)
    print(f"PASS: released environment lease for {args.node_id}")
```

## 4. tools/semantic_merge_probe.py

Add near the top:
```python
from ops.lib.telemetry import emit
```

Right after `verdict["verdict"] = "PASS" if ... else "FAIL"`:
```python
            verdict["verdict"] = "PASS" if test_result.returncode == 0 else "FAIL"
            if verdict["verdict"] == "FAIL":
                emit("semantic_conflict_detected", node_id=",".join(args.branches),
                     detail={"base": args.base, "branches": args.branches})
```

## Verification after applying

```
python -m pytest tests/tools/ -q
python tools/environment_lease.py --reports-dir reports/$(date +%F) claim --node-id EN-010 --worktree ../wt-en-010
cat reports/$(date +%F)/telemetry/program_execution_events.jsonl
```
You should see a `lease_acquired` line matching
`ops/schemas/program_execution_event.schema.json`.
