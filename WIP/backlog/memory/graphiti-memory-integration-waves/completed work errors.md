PR_BASE="origin/main" PR_SECURITY_ADVISORY="0" \
	PR_MYPY_STRICT="0" WS="/Users/ib-mac/Cursor-Governance" \
		bash ops/scripts/run_pr_gate.sh
=== make pr (changed files vs origin/main; full-tree = make pr-full / nightly) ===
SOURCE:working-tree;comparison-empty base=origin/main
pre-commit (changed files: 367)
check for merge conflicts................................................................Passed
No hardcoded /Users or /home paths (governance SSOT path contract).......................Passed
Governance symlink wiring is healthy....................................................Skipped
ruff (legacy alias)......................................................................Failed
- hook id: ruff
- exit code: 1

E501 Line too long (105 > 100)
  --> environment/program-execution/core/program-execution-blueprint-template/scripts/instantiate.py:17:101
   |
15 |     if target.exists():
16 |         raise SystemExit(f"target already exists: {target}")
17 |     shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns("MANIFEST.yaml", "__pycache__", "*.pyc"))
   |                                                                                                     ^^^^^
18 |     for path in target.rglob("*"):
19 |         if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".py"}:
   |

E501 Line too long (101 > 100)
  --> environment/program-execution/core/program-execution-blueprint-template/scripts/instantiate.py:19:101
   |
17 |     shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns("MANIFEST.yaml", "__pycache__", "*.pyc"))
18 |     for path in target.rglob("*"):
19 |         if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".py"}:
   |                                                                                                     ^
20 |             continue
21 |         text = path.read_text(encoding="utf-8")
   |

E501 Line too long (121 > 100)
  --> environment/program-execution/core/program-execution-blueprint-template/scripts/instantiate.py:35:101
   |
33 |     files = []
34 |     for path in sorted(root.rglob("*")):
35 |         if path.is_file() and path.name != "MANIFEST.yaml" and "__pycache__" not in path.parts and path.suffix != ".pyc":
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^
36 |             files.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
37 |     manifest = {
   |

E501 Line too long (126 > 100)
  --> environment/program-execution/core/program-execution-blueprint-template/scripts/instantiate.py:36:101
   |
34 |     for path in sorted(root.rglob("*")):
35 |         if path.is_file() and path.name != "MANIFEST.yaml" and "__pycache__" not in path.parts and path.suffix != ".pyc":
36 |             files.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
37 |     manifest = {
38 |         "schema": "program-execution-blueprint.manifest.v2",
   |

E501 Line too long (111 > 100)
  --> environment/program-execution/core/program-execution-blueprint-template/scripts/instantiate.py:44:101
   |
42 |         "integrity": {"algorithm": "sha256", "self_excluded": True},
43 |     }
44 |     (root / "MANIFEST.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False, width=110), encoding="utf-8")
   |                                                                                                     ^^^^^^^^^^^
   |

E501 Line too long (104 > 100)
  --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:16:101
   |
14 | REQUIRED_FILES = [
15 |     "README.md", "PROGRAM.yaml", "EXECUTION_INDEX.yaml", "EXECUTIVE_DECISION.md", "ARCHITECTURE.md",
16 |     "OPERATING_MODEL.md", "EXECUTION_TARGETS.yaml", "AUTHORITY_REGISTRY.yaml", "DECISION_REGISTER.yaml",
   |                                                                                                     ^^^^
17 |     "UNKNOWN_REGISTER.yaml", "RISK_REGISTER.yaml", "WAIVER_REGISTER.yaml", "EVIDENCE_CATALOG.yaml",
18 |     "DO_NOT_BUILD.yaml", "CURRENT_STATE_DELTA.yaml", "WORKSTREAMS.yaml", "DEPENDENCY_GRAPH.yaml",
   |

E501 Line too long (103 > 100)
  --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:22:101
   |
20 |     "CUTOVER_AND_ROLLBACK.yaml", "SOURCE_TRACEABILITY.yaml", "DEFINITION_OF_DONE.md",
21 |     "AGENT_EXECUTION_CONTRACT.md", "HANDOFF.md", "RUNBOOK.md", "INSTANTIATION_GUIDE.md",
22 |     "VALIDATION.md", "DESIGN_RATIONALE.md", "TEMPLATE_VARIABLES.yaml", "CHANGELOG.md", "MANIFEST.yaml",
   |                                                                                                     ^^^
23 | ]
24 | SCHEMA_MAP = {
   |

E501 Line too long (115 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:116:101
    |
114 |             value = load_yaml(root / rel)
115 |             schema = json.loads((root / "schemas" / schema_name).read_text(encoding="utf-8"))
116 |             validation_errors = sorted(Draft202012Validator(schema).iter_errors(value), key=lambda e: list(e.path))
    |                                                                                                     ^^^^^^^^^^^^^^^
117 |             for exc in validation_errors:
118 |                 path = ".".join(str(p) for p in exc.path) or "<root>"
    |

E501 Line too long (149 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:137:101
    |
135 | …ot in {"EXECUTION_INDEX.yaml"}}
136 | …
137 | …smatch: missing={sorted(expected_index-indexed)}, extra={sorted(indexed-expected_index)}")
    |                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
138 | …
139 | …
    |

E501 Line too long (123 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:184:101
    |
182 |         if target["execution_mode"] == "repo_local" and not target.get("repository_id"):
183 |             errors.append(f"target {target['id']}: repo_local requires repository_id")
184 |         if target["execution_mode"] != "repo_local" and target.get("repository_id") and target["kind"] != "git_repository":
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^
185 |             errors.append(f"target {target['id']}: repository_id is only valid for git_repository targets")
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:185:101
    |
183 |             errors.append(f"target {target['id']}: repo_local requires repository_id")
184 |         if target["execution_mode"] != "repo_local" and target.get("repository_id") and target["kind"] != "git_repository":
185 |             errors.append(f"target {target['id']}: repository_id is only valid for git_repository targets")
    |                                                                                                     ^^^^^^^
186 |
187 |     normalized_responsibilities = [a["responsibility"].strip().lower() for a in authorities]
    |

E501 Line too long (109 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:188:101
    |
187 |     normalized_responsibilities = [a["responsibility"].strip().lower() for a in authorities]
188 |     duplicates = sorted({x for x in normalized_responsibilities if normalized_responsibilities.count(x) > 1})
    |                                                                                                     ^^^^^^^^^
189 |     if duplicates:
190 |         errors.append(f"duplicate authoritative responsibilities: {duplicates}")
    |

E501 Line too long (108 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:192:101
    |
190 |         errors.append(f"duplicate authoritative responsibilities: {duplicates}")
191 |     for authority in authorities:
192 |         check_refs([authority["owner_target_id"]], target_ids, f"authority {authority['id']} owner", errors)
    |                                                                                                     ^^^^^^^^
193 |         check_refs(authority.get("prohibited_owner_target_ids") or [], target_ids, f"authority {authority['id']} prohibited owners", …
194 |         check_refs(authority.get("validation_gate_ids") or [], gate_ids, f"authority {authority['id']} gates", errors)
    |

E501 Line too long (140 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:193:101
    |
191 | …
192 | …get_ids, f"authority {authority['id']} owner", errors)
193 | …get_ids") or [], target_ids, f"authority {authority['id']} prohibited owners", errors)
    |                                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
194 | …) or [], gate_ids, f"authority {authority['id']} gates", errors)
    |

E501 Line too long (118 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:194:101
    |
192 |         check_refs([authority["owner_target_id"]], target_ids, f"authority {authority['id']} owner", errors)
193 |         check_refs(authority.get("prohibited_owner_target_ids") or [], target_ids, f"authority {authority['id']} prohibited owners", …
194 |         check_refs(authority.get("validation_gate_ids") or [], gate_ids, f"authority {authority['id']} gates", errors)
    |                                                                                                     ^^^^^^^^^^^^^^^^^^
195 |
196 |     for decision in decisions:
    |

E501 Line too long (115 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:197:101
    |
196 |     for decision in decisions:
197 |         check_refs(decision.get("evidence_ids") or [], evidence_ids, f"decision {decision['id']} evidence", errors)
    |                                                                                                     ^^^^^^^^^^^^^^^
198 |         check_refs(decision.get("blocks") or [], task_ids, f"decision {decision['id']} blocks", errors)
199 |         if decision["status"] == "accepted" and not decision.get("selected_option"):
    |

E501 Line too long (103 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:198:101
    |
196 |     for decision in decisions:
197 |         check_refs(decision.get("evidence_ids") or [], evidence_ids, f"decision {decision['id']} evidence", errors)
198 |         check_refs(decision.get("blocks") or [], task_ids, f"decision {decision['id']} blocks", errors)
    |                                                                                                     ^^^
199 |         if decision["status"] == "accepted" and not decision.get("selected_option"):
200 |             errors.append(f"decision {decision['id']}: accepted decision requires selected_option")
    |

E501 Line too long (121 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:201:101
    |
199 |         if decision["status"] == "accepted" and not decision.get("selected_option"):
200 |             errors.append(f"decision {decision['id']}: accepted decision requires selected_option")
201 |         if decision.get("selected_option") and decision["selected_option"] not in {o["id"] for o in decision["options"]}:
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^
202 |             errors.append(f"decision {decision['id']}: selected_option is not one of the declared options")
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:202:101
    |
200 |             errors.append(f"decision {decision['id']}: accepted decision requires selected_option")
201 |         if decision.get("selected_option") and decision["selected_option"] not in {o["id"] for o in decision["options"]}:
202 |             errors.append(f"decision {decision['id']}: selected_option is not one of the declared options")
    |                                                                                                     ^^^^^^^
203 |
204 |     for item in unknowns:
    |

E501 Line too long (117 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:206:101
    |
204 |     for item in unknowns:
205 |         check_refs(item.get("blocks") or [], task_ids, f"unknown {item['id']} blocks", errors)
206 |         check_refs(item.get("resolution_evidence_ids") or [], evidence_ids, f"unknown {item['id']} evidence", errors)
    |                                                                                                     ^^^^^^^^^^^^^^^^^
207 |         if item["status"] == "resolved" and not item.get("resolution_evidence_ids"):
208 |             errors.append(f"unknown {item['id']}: resolved status requires resolution evidence")
    |

E501 Line too long (120 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:214:101
    |
212 |         check_refs(risk.get("related_gates") or [], gate_ids, f"risk {risk['id']} gates", errors)
213 |         if risk.get("acceptance_decision_id"):
214 |             check_refs([risk["acceptance_decision_id"]], decision_ids, f"risk {risk['id']} acceptance decision", errors)
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^
215 |
216 |     for waiver in waivers:
    |

E501 Line too long (109 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:218:101
    |
216 |     for waiver in waivers:
217 |         check_refs(waiver.get("scope") or [], gate_ids, f"waiver {waiver['id']} scope", errors)
218 |         check_refs(waiver.get("evidence_ids") or [], evidence_ids, f"waiver {waiver['id']} evidence", errors)
    |                                                                                                     ^^^^^^^^^
219 |         if waiver["status"] == "active" and not waiver.get("evidence_ids"):
220 |             errors.append(f"waiver {waiver['id']}: active waiver requires evidence")
    |

E501 Line too long (106 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:224:101
    |
222 |     for ws in workstreams:
223 |         check_refs(ws.get("target_ids") or [], target_ids, f"workstream {ws['id']} targets", errors)
224 |         check_refs(ws.get("entry_gate_ids") or [], gate_ids, f"workstream {ws['id']} entry gates", errors)
    |                                                                                                     ^^^^^^
225 |         check_refs(ws.get("exit_gate_ids") or [], gate_ids, f"workstream {ws['id']} exit gates", errors)
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:225:101
    |
223 |         check_refs(ws.get("target_ids") or [], target_ids, f"workstream {ws['id']} targets", errors)
224 |         check_refs(ws.get("entry_gate_ids") or [], gate_ids, f"workstream {ws['id']} entry gates", errors)
225 |         check_refs(ws.get("exit_gate_ids") or [], gate_ids, f"workstream {ws['id']} exit gates", errors)
    |                                                                                                     ^^^^
226 |
227 |     if node_ids != task_ids:
    |

E501 Line too long (142 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:228:101
    |
227 | …
228 | …atch task IDs: missing={sorted(task_ids-node_ids)}, extra={sorted(node_ids-task_ids)}")
    |                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
229 | …
230 | …, f"edge {edge['id']}", errors)
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:231:101
    |
229 |     for edge in graph.get("edges") or []:
230 |         check_refs([edge["from"], edge["to"]], node_ids, f"edge {edge['id']}", errors)
231 |         check_refs(edge.get("proof_gate_ids") or [], gate_ids, f"edge {edge['id']} proof gates", errors)
    |                                                                                                     ^^^^
232 |         if edge["from"] == edge["to"]:
233 |             errors.append(f"edge {edge['id']}: self-dependency forbidden")
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:243:101
    |
241 |             errors.append("wave sequence values must be strictly increasing")
242 |         last_sequence = wave["sequence"]
243 |         check_refs(wave.get("depends_on") or [], wave_ids, f"wave {wave['id']} dependencies", errors)
    |                                                                                                     ^
244 |         check_refs(wave.get("workstream_ids") or [], workstream_ids, f"wave {wave['id']} workstreams", errors)
245 |         check_refs(wave.get("task_ids") or [], task_ids, f"wave {wave['id']} tasks", errors)
    |

E501 Line too long (110 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:244:101
    |
242 |         last_sequence = wave["sequence"]
243 |         check_refs(wave.get("depends_on") or [], wave_ids, f"wave {wave['id']} dependencies", errors)
244 |         check_refs(wave.get("workstream_ids") or [], workstream_ids, f"wave {wave['id']} workstreams", errors)
    |                                                                                                     ^^^^^^^^^^
245 |         check_refs(wave.get("task_ids") or [], task_ids, f"wave {wave['id']} tasks", errors)
246 |         check_refs(wave.get("entry_gate_ids") or [], gate_ids, f"wave {wave['id']} entry gates", errors)
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:246:101
    |
244 |         check_refs(wave.get("workstream_ids") or [], workstream_ids, f"wave {wave['id']} workstreams", errors)
245 |         check_refs(wave.get("task_ids") or [], task_ids, f"wave {wave['id']} tasks", errors)
246 |         check_refs(wave.get("entry_gate_ids") or [], gate_ids, f"wave {wave['id']} entry gates", errors)
    |                                                                                                     ^^^^
247 |         check_refs(wave.get("exit_gate_ids") or [], gate_ids, f"wave {wave['id']} exit gates", errors)
248 |         for task_id in wave.get("task_ids") or []:
    |

E501 Line too long (102 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:247:101
    |
245 |         check_refs(wave.get("task_ids") or [], task_ids, f"wave {wave['id']} tasks", errors)
246 |         check_refs(wave.get("entry_gate_ids") or [], gate_ids, f"wave {wave['id']} entry gates", errors)
247 |         check_refs(wave.get("exit_gate_ids") or [], gate_ids, f"wave {wave['id']} exit gates", errors)
    |                                                                                                     ^^
248 |         for task_id in wave.get("task_ids") or []:
249 |             task_wave_membership[task_id].append(wave["id"])
    |

E501 Line too long (114 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:260:101
    |
258 |         check_refs([task["wave_id"]], wave_ids, f"task {task['id']} wave", errors)
259 |         check_refs([task["target_id"]], target_ids, f"task {task['id']} target", errors)
260 |         check_refs(task.get("authority_basis_ids") or [], authority_ids, f"task {task['id']} authorities", errors)
    |                                                                                                     ^^^^^^^^^^^^^^
261 |         check_refs(task.get("required_decision_ids") or [], decision_ids, f"task {task['id']} decisions", errors)
262 |         check_refs(task.get("blocking_unknown_ids") or [], unknown_ids, f"task {task['id']} unknowns", errors)
    |

E501 Line too long (113 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:261:101
    |
259 |         check_refs([task["target_id"]], target_ids, f"task {task['id']} target", errors)
260 |         check_refs(task.get("authority_basis_ids") or [], authority_ids, f"task {task['id']} authorities", errors)
261 |         check_refs(task.get("required_decision_ids") or [], decision_ids, f"task {task['id']} decisions", errors)
    |                                                                                                     ^^^^^^^^^^^^^
262 |         check_refs(task.get("blocking_unknown_ids") or [], unknown_ids, f"task {task['id']} unknowns", errors)
263 |         check_refs(task.get("input_evidence_ids") or [], evidence_ids, f"task {task['id']} evidence", errors)
    |

E501 Line too long (110 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:262:101
    |
260 |         check_refs(task.get("authority_basis_ids") or [], authority_ids, f"task {task['id']} authorities", errors)
261 |         check_refs(task.get("required_decision_ids") or [], decision_ids, f"task {task['id']} decisions", errors)
262 |         check_refs(task.get("blocking_unknown_ids") or [], unknown_ids, f"task {task['id']} unknowns", errors)
    |                                                                                                     ^^^^^^^^^^
263 |         check_refs(task.get("input_evidence_ids") or [], evidence_ids, f"task {task['id']} evidence", errors)
264 |         check_refs(task.get("completion_gate_ids") or [], gate_ids, f"task {task['id']} completion gates", errors)
    |

E501 Line too long (109 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:263:101
    |
261 |         check_refs(task.get("required_decision_ids") or [], decision_ids, f"task {task['id']} decisions", errors)
262 |         check_refs(task.get("blocking_unknown_ids") or [], unknown_ids, f"task {task['id']} unknowns", errors)
263 |         check_refs(task.get("input_evidence_ids") or [], evidence_ids, f"task {task['id']} evidence", errors)
    |                                                                                                     ^^^^^^^^^
264 |         check_refs(task.get("completion_gate_ids") or [], gate_ids, f"task {task['id']} completion gates", errors)
265 |         if task_wave_membership.get(task["id"]) != [task["wave_id"]]:
    |

E501 Line too long (114 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:264:101
    |
262 |         check_refs(task.get("blocking_unknown_ids") or [], unknown_ids, f"task {task['id']} unknowns", errors)
263 |         check_refs(task.get("input_evidence_ids") or [], evidence_ids, f"task {task['id']} evidence", errors)
264 |         check_refs(task.get("completion_gate_ids") or [], gate_ids, f"task {task['id']} completion gates", errors)
    |                                                                                                     ^^^^^^^^^^^^^^
265 |         if task_wave_membership.get(task["id"]) != [task["wave_id"]]:
266 |             errors.append(f"task {task['id']}: wave_id disagrees with EXECUTION_WAVES.yaml")
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:269:101
    |
267 |         if set(task["authorization_ceiling"]) != AUTH_ACTIONS:
268 |             errors.append(f"task {task['id']}: authorization_ceiling keys are not canonical")
269 |         if task["execution_kind"] == "program_control" and task["authorization_ceiling"]["local_write"]:
    |                                                                                                     ^^^^
270 |             errors.append(f"task {task['id']}: program_control task cannot authorize repository local_write")
271 |         if task["risk"]["tier"] == "T4" and not task["authorization_ceiling"]["destructive_change"]:
    |

E501 Line too long (109 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:270:101
    |
268 |             errors.append(f"task {task['id']}: authorization_ceiling keys are not canonical")
269 |         if task["execution_kind"] == "program_control" and task["authorization_ceiling"]["local_write"]:
270 |             errors.append(f"task {task['id']}: program_control task cannot authorize repository local_write")
    |                                                                                                     ^^^^^^^^^
271 |         if task["risk"]["tier"] == "T4" and not task["authorization_ceiling"]["destructive_change"]:
272 |             errors.append(f"task {task['id']}: T4 task must explicitly declare destructive_change ceiling")
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:272:101
    |
270 |             errors.append(f"task {task['id']}: program_control task cannot authorize repository local_write")
271 |         if task["risk"]["tier"] == "T4" and not task["authorization_ceiling"]["destructive_change"]:
272 |             errors.append(f"task {task['id']}: T4 task must explicitly declare destructive_change ceiling")
    |                                                                                                     ^^^^^^^
273 |
274 |     for gate in gates:
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:277:101
    |
275 |         if "status" in gate:
276 |             errors.append(f"gate {gate['id']}: runtime status is forbidden in Blueprint definition")
277 |         check_refs(gate["scope"].get("wave_ids") or [], wave_ids, f"gate {gate['id']} waves", errors)
    |                                                                                                     ^
278 |         check_refs(gate["scope"].get("task_ids") or [], task_ids, f"gate {gate['id']} tasks", errors)
279 |         check_refs(gate.get("required_evidence_ids") or [], evidence_ids, f"gate {gate['id']} evidence", errors)
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:278:101
    |
276 |             errors.append(f"gate {gate['id']}: runtime status is forbidden in Blueprint definition")
277 |         check_refs(gate["scope"].get("wave_ids") or [], wave_ids, f"gate {gate['id']} waves", errors)
278 |         check_refs(gate["scope"].get("task_ids") or [], task_ids, f"gate {gate['id']} tasks", errors)
    |                                                                                                     ^
279 |         check_refs(gate.get("required_evidence_ids") or [], evidence_ids, f"gate {gate['id']} evidence", errors)
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:279:101
    |
277 |         check_refs(gate["scope"].get("wave_ids") or [], wave_ids, f"gate {gate['id']} waves", errors)
278 |         check_refs(gate["scope"].get("task_ids") or [], task_ids, f"gate {gate['id']} tasks", errors)
279 |         check_refs(gate.get("required_evidence_ids") or [], evidence_ids, f"gate {gate['id']} evidence", errors)
    |                                                                                                     ^^^^^^^^^^^^
280 |
281 |     current = data["CURRENT_STATE_DELTA.yaml"]
    |

E501 Line too long (102 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:283:101
    |
281 |     current = data["CURRENT_STATE_DELTA.yaml"]
282 |     for source in current.get("sources") or []:
283 |         check_refs([source.get("evidence_id")], evidence_ids, "current-state source evidence", errors)
    |                                                                                                     ^^
284 |     for delta in current.get("deltas") or []:
285 |         check_refs([delta.get("target_id")], target_ids, f"delta {delta.get('id')} target", errors)
    |

E501 Line too long (110 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:286:101
    |
284 |     for delta in current.get("deltas") or []:
285 |         check_refs([delta.get("target_id")], target_ids, f"delta {delta.get('id')} target", errors)
286 |         check_refs(delta.get("evidence_ids") or [], evidence_ids, f"delta {delta.get('id')} evidence", errors)
    |                                                                                                     ^^^^^^^^^^
287 |
288 |     for source in sources:
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:289:101
    |
288 |     for source in sources:
289 |         check_refs([source.get("evidence_id")], evidence_ids, f"source {source['id']} evidence", errors)
    |                                                                                                     ^^^^
290 |         check_refs(source.get("target_ids") or [], target_ids, f"source {source['id']} targets", errors)
291 |         check_refs(source.get("workstream_ids") or [], workstream_ids, f"source {source['id']} workstreams", errors)
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:290:101
    |
288 |     for source in sources:
289 |         check_refs([source.get("evidence_id")], evidence_ids, f"source {source['id']} evidence", errors)
290 |         check_refs(source.get("target_ids") or [], target_ids, f"source {source['id']} targets", errors)
    |                                                                                                     ^^^^
291 |         check_refs(source.get("workstream_ids") or [], workstream_ids, f"source {source['id']} workstreams", errors)
292 |         check_refs(source.get("task_ids") or [], task_ids, f"source {source['id']} tasks", errors)
    |

E501 Line too long (116 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:291:101
    |
289 |         check_refs([source.get("evidence_id")], evidence_ids, f"source {source['id']} evidence", errors)
290 |         check_refs(source.get("target_ids") or [], target_ids, f"source {source['id']} targets", errors)
291 |         check_refs(source.get("workstream_ids") or [], workstream_ids, f"source {source['id']} workstreams", errors)
    |                                                                                                     ^^^^^^^^^^^^^^^^
292 |         check_refs(source.get("task_ids") or [], task_ids, f"source {source['id']} tasks", errors)
293 |         check_refs(source.get("gate_ids") or [], gate_ids, f"source {source['id']} gates", errors)
    |

E501 Line too long (133 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:314:101
    |
312 |     actual = {
313 |         p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
314 |         for p in root.rglob("*") if p.is_file() and p.name != "MANIFEST.yaml" and "__pycache__" not in p.parts and p.suffix != ".pyc"
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
315 |     }
316 |     if set(expected) != set(actual):
    |

E501 Line too long (136 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:317:101
    |
315 | …
316 | …
317 | …ing={sorted(set(actual)-set(expected))}, stale={sorted(set(expected)-set(actual))}")
    |                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
318 | …
319 | …
    |

E501 Line too long (105 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:327:101
    |
325 |     if mode == "instantiated":
326 |         for path in root.rglob("*"):
327 |             if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".py"}:
    |                                                                                                     ^^^^^
328 |                 continue
329 |             text = path.read_text(encoding="utf-8", errors="ignore")
    |

E501 Line too long (103 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:333:101
    |
331 |                 match = pattern.search(text)
332 |                 if match:
333 |                     errors.append(f"{path.relative_to(root)}: unresolved placeholder {match.group(0)}")
    |                                                                                                     ^^^
334 |                     break
335 |         if program["definition_status"] != "accepted":
    |

E501 Line too long (106 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:336:101
    |
334 |                     break
335 |         if program["definition_status"] != "accepted":
336 |             errors.append("instantiated executable Blueprint requires program.definition_status=accepted")
    |                                                                                                     ^^^^^^
337 |         for task in tasks:
338 |             if task["definition_status"] not in {"ready", "blocked", "cancelled", "superseded"}:
    |

E501 Line too long (132 > 100)
   --> environment/program-execution/core/program-execution-blueprint-template/scripts/validate_blueprint.py:339:101
    |
337 |         for task in tasks:
338 |             if task["definition_status"] not in {"ready", "blocked", "cancelled", "superseded"}:
339 |                 errors.append(f"task {task['id']}: instantiated definition_status must be ready, blocked, cancelled, or superseded")
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
340 |
341 |     return errors
    |

E501 Line too long (121 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/instantiate.py:17:101
   |
15 |     files = []
16 |     for path in sorted(root.rglob("*")):
17 |         if path.is_file() and path.name != "MANIFEST.yaml" and "__pycache__" not in path.parts and path.suffix != ".pyc":
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^
18 |             files.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
19 |     manifest = {
   |

E501 Line too long (126 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/instantiate.py:18:101
   |
16 |     for path in sorted(root.rglob("*")):
17 |         if path.is_file() and path.name != "MANIFEST.yaml" and "__pycache__" not in path.parts and path.suffix != ".pyc":
18 |             files.append({"path": path.relative_to(root).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
19 |     manifest = {
20 |         "schema": "program-execution-controller.manifest.v2",
   |

E501 Line too long (111 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/instantiate.py:26:101
   |
24 |         "integrity": {"algorithm": "sha256", "self_excluded": True},
25 |     }
26 |     (root / "MANIFEST.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False, width=110), encoding="utf-8")
   |                                                                                                     ^^^^^^^^^^^
   |

E501 Line too long (105 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/instantiate.py:40:101
   |
38 |     if target.exists():
39 |         raise SystemExit(f"target already exists: {target}")
40 |     shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns("MANIFEST.yaml", "__pycache__", "*.pyc"))
   |                                                                                                     ^^^^^
41 |     replacements = {
42 |         "CONTROLLER_NAME": args.name, "CONTROLLER_ID": args.id,
   |

E501 Line too long (101 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/instantiate.py:46:101
   |
44 |     }
45 |     for path in target.rglob("*"):
46 |         if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".json", ".py"}:
   |                                                                                                     ^
47 |             continue
48 |         text = path.read_text(encoding="utf-8")
   |

E501 Line too long (104 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/instantiate.py:55:101
   |
53 |     definition = yaml.safe_load(definition_path.read_text(encoding="utf-8"))
54 |     definition["controller"]["definition_status"] = "instantiated"
55 |     definition_path.write_text(yaml.safe_dump(definition, sort_keys=False, width=110), encoding="utf-8")
   |                                                                                                     ^^^^
56 |     write_manifest(target)
57 |     print(target)
   |

E501 Line too long (103 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/pec/blueprint.py:28:101
   |
26 |     index = _load(root, "EXECUTION_INDEX.yaml")
27 |     if index.get("blueprint_contract") != "program-execution-blueprint.v2":
28 |         raise BlueprintError("unsupported Blueprint contract; expected program-execution-blueprint.v2")
   |                                                                                                     ^^^
29 |     required = list(index.get("required_sources") or [])
30 |     if not required:
   |

E501 Line too long (108 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/cli.py:137:101
    |
135 |     cmd = sub.add_parser("evaluate-gate")
136 |     cmd.add_argument("gate_id")
137 |     cmd.add_argument("result", choices=["PASS", "FAIL", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE_WITH_REASON"])
    |                                                                                                     ^^^^^^^^
138 |     cmd.add_argument("--workspace", required=True, type=Path)
139 |     cmd.add_argument("--evidence-id", action="append", default=[])
    |

E702 Multiple statements on one line (semicolon)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/cli.py:169:34
    |
167 |             value = validate_runtime(args.workspace)
168 |             if value["status"] != "PASS":
169 |                 print_json(value); return 1
    |                                  ^
170 |         elif args.command == "reconcile":
171 |             value = reconcile_repositories(args.workspace, args.repository)
    |

E501 Line too long (137 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/cli.py:185:101
    |
183 | …
184 | …
185 | …ledger, args.workspace.resolve(), args.task_id, args.file, args.actor, args.replace)
    |                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
186 | …
187 | …
    |

E501 Line too long (109 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/cli.py:213:101
    |
211 |             value = add_approval(args.workspace, args.file)
212 |         elif args.command == "set-decision":
213 |             value = set_decision(args.workspace, args.decision_id, args.status, args.evidence_id, args.actor)
    |                                                                                                     ^^^^^^^^^
214 |         elif args.command == "set-unknown":
215 |             value = set_unknown(args.workspace, args.unknown_id, args.status, args.evidence_id, args.actor)
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/cli.py:215:101
    |
213 | …         value = set_decision(args.workspace, args.decision_id, args.status, args.evidence_id, args.actor)
214 | …     elif args.command == "set-unknown":
215 | …         value = set_unknown(args.workspace, args.unknown_id, args.status, args.evidence_id, args.actor)
    |                                                                                                   ^^^^^^^
216 | …     elif args.command == "evaluate-gate":
217 | …         value = evaluate_gate(args.workspace, args.gate_id, args.result, args.evidence_id, args.method, args.actor, args.waiver_id)
    |

E501 Line too long (135 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/cli.py:217:101
    |
215 | ….unknown_id, args.status, args.evidence_id, args.actor)
216 | …
217 | …gs.gate_id, args.result, args.evidence_id, args.method, args.actor, args.waiver_id)
    |                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
218 | …
219 | …rgs.reason, args.actor)
    |

E501 Line too long (101 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/pec/common.py:42:101
   |
40 |     path.parent.mkdir(parents=True, exist_ok=True)
41 |     payload = json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
42 |     with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
   |                                                                                                     ^
43 |         handle.write(payload)
44 |         temp = Path(handle.name)
   |

E501 Line too long (113 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/pec/common.py:74:101
   |
72 |     )
73 |     if check and completed.returncode != 0:
74 |         raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or f"git command failed: {args}")
   |                                                                                                     ^^^^^^^^^^^^^
75 |     return completed
   |

E501 Line too long (105 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:36:101
   |
34 |     if not parts:
35 |         raise ContractError("empty repository path")
36 |     if parts[0] in {".git", ".program-controller", ".pec", "runtime", "ledger", "receipts", "contracts"}:
   |                                                                                                     ^^^^^
37 |         raise ContractError(f"controller or git internals forbidden: {value}")
38 |     normalized = "/".join(parts)
   |

E501 Line too long (126 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:97:101
   |
95 |     required_commands = set(task.get("required_validation_commands") or [])
96 |     if not required_commands <= set(commands):
97 |         raise ContractError(f"Source Contract omits Blueprint validation commands: {sorted(required_commands-set(commands))}")
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
98 |     if not set(task.get("required_acceptance") or []) <= set(contract.get("acceptance_obligation_ids") or []):
99 |         raise ContractError("Source Contract omits Blueprint acceptance obligations")
   |

E501 Line too long (110 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:98:101
    |
 96 |     if not required_commands <= set(commands):
 97 |         raise ContractError(f"Source Contract omits Blueprint validation commands: {sorted(required_commands-set(commands))}")
 98 |     if not set(task.get("required_acceptance") or []) <= set(contract.get("acceptance_obligation_ids") or []):
    |                                                                                                     ^^^^^^^^^^
 99 |         raise ContractError("Source Contract omits Blueprint acceptance obligations")
100 |     if not set(task.get("completion_gates") or []) <= set(contract.get("required_gate_ids") or []):
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:102:101
    |
100 |     if not set(task.get("completion_gates") or []) <= set(contract.get("required_gate_ids") or []):
101 |         raise ContractError("Source Contract omits Blueprint completion gates")
102 |     if not set(task.get("required_evidence") or []) <= set(contract.get("required_evidence_ids") or []):
    |                                                                                                     ^^^^
103 |         raise ContractError("Source Contract omits Blueprint evidence obligations")
104 |     if not contract.get("stop_conditions") or not contract.get("rollback"):
    |

E501 Line too long (161 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:106:101
    |
104 | …ollback"):
105 | …uired")
106 | …, "writable_paths": sorted(set(writable)), "validation_commands": list(dict.fromkeys(commands))}
    |                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |

E501 Line too long (137 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:115:101
    |
113 | …task.get("repository_id"):
114 | …sitory Source Contract")
115 | …authorization_ceiling"].items() if allowed and action in {"inspect", "local_write"}]
    |                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
116 | …
117 | …e-contract.v2",
    |

E501 Line too long (161 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:137:101
    |
137 | …rkspace: Path, task_id: str, source: Path, actor: str, replace: bool = False) -> dict[str, Any]:
    |                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
138 | …
139 | …
    |

E501 Line too long (114 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:147:101
    |
145 |     write_json(target, contract)
146 |     digest = digest_object(contract)
147 |     db.update_task(task_id, source_contract_path=str(target), source_contract_digest=digest, scope_status="exact")
    |                                                                                                     ^^^^^^^^^^^^^^
148 |     ledger.append("SOURCE_CONTRACT_REGISTERED", actor, {"task_id": task_id, "path": str(target), "digest": digest, "replaced": bool(r…
149 |     return {"status": "REGISTERED", "task_id": task_id, "path": str(target), "digest": digest}
    |

E501 Line too long (142 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:148:101
    |
146 | …
147 | …rget), source_contract_digest=digest, scope_status="exact")
148 | …{"task_id": task_id, "path": str(target), "digest": digest, "replaced": bool(replace)})
    |                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
149 | … "path": str(target), "digest": digest}
    |

E501 Line too long (103 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:152:101
    |
152 | def render_contract(db: StateDB, ledger: EventLedger, workspace: Path, task_id: str) -> dict[str, Any]:
    |                                                                                                     ^^^
153 |     task = db.task(task_id)
154 |     if task is None:
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:160:101
    |
158 |         raise ContractError("active lease required")
159 |     if task["runtime_state"] != "PREPARED":
160 |         raise ContractError(f"task must be PREPARED before rendering, found {task['runtime_state']}")
    |                                                                                                     ^
161 |     if not task.get("source_contract_path"):
162 |         raise ContractError("registered Source Contract required")
    |

E501 Line too long (110 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:169:101
    |
167 |     program_digest = db.get_meta("program_digest")
168 |     attempt_number = db.next_attempt_number(task_id)
169 |     receipt_path = workspace / "attempts" / task_id / f"attempt-{attempt_number:03d}" / "attempt-receipt.json"
    |                                                                                                     ^^^^^^^^^^
170 |     rendered = {
171 |         **source,
    |

E501 Line too long (119 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:191:101
    |
189 |             f"Target: `{rendered['target_id']}` / `{rendered['repository_id']}`",
190 |             f"Worktree: `{rendered['worktree']}`", f"Base SHA: `{rendered['base_sha']}`",
191 |             f"Program digest: `{rendered['program_digest']}`", f"Contract digest: `{rendered['contract_digest']}`", "",
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^
192 |             "Allowed actions:", *[f"- `{action}`" for action in rendered["requested_actions"]], "",
193 |             "Writable paths:", *[f"- `{path}`" for path in rendered["writable_paths"]], "",
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:194:101
    |
192 |             "Allowed actions:", *[f"- `{action}`" for action in rendered["requested_actions"]], "",
193 |             "Writable paths:", *[f"- `{path}`" for path in rendered["writable_paths"]], "",
194 |             "Validation commands:", *[f"- `{command}`" for command in rendered["validation_commands"]], "",
    |                                                                                                     ^^^^^^^
195 |             "Stop immediately on any program, contract, scope, authorization, lease, or base-state drift.",
196 |             "Do not use remote credentials or claim independent verification.",
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:195:101
    |
193 |             "Writable paths:", *[f"- `{path}`" for path in rendered["writable_paths"]], "",
194 |             "Validation commands:", *[f"- `{command}`" for command in rendered["validation_commands"]], "",
195 |             "Stop immediately on any program, contract, scope, authorization, lease, or base-state drift.",
    |                                                                                                     ^^^^^^^
196 |             "Do not use remote credentials or claim independent verification.",
197 |             f"Write the Attempt Receipt to `{rendered['attempt_receipt_path']}`.", "",
    |

E501 Line too long (117 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:201:101
    |
199 |         encoding="utf-8",
200 |     )
201 |     db.update_task(task_id, rendered_contract_path=str(target), rendered_contract_digest=rendered["contract_digest"])
    |                                                                                                     ^^^^^^^^^^^^^^^^^
202 |     db.transition_task(task_id, "CONTRACTED")
203 |     db.update_lease(lease["lease_id"], contract_digest=rendered["contract_digest"])
    |

E501 Line too long (165 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:204:101
    |
202 | …
203 | …ntract_digest"])
204 | …sk_id, "path": str(target), "digest": rendered["contract_digest"], "lease_id": lease["lease_id"]})
    |                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
205 | …ief": str(brief), "contract_digest": rendered["contract_digest"]}
    |

E501 Line too long (132 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/contracts.py:205:101
    |
203 | …gest=rendered["contract_digest"])
204 | …", {"task_id": task_id, "path": str(target), "digest": rendered["contract_digest"], "lease_id": lease["lease_id"]})
205 | …rget), "worker_brief": str(brief), "contract_digest": rendered["contract_digest"]}
    |                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |

E501 Line too long (110 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:28:101
   |
26 |     if not (workspace / "runtime" / "state.sqlite").is_file():
27 |         raise ControllerError(f"Controller runtime not bootstrapped: {workspace}")
28 |     return StateDB(workspace / "runtime" / "state.sqlite"), EventLedger(workspace / "ledger" / "events.jsonl")
   |                                                                                                     ^^^^^^^^^^
   |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:103:101
    |
101 |         ledger.append("CONTROLLER_BOOTSTRAPPED", "controller", {
102 |             "workspace": str(workspace), "blueprint": str(blueprint),
103 |             "program_digest": lock["lock_digest"], "controller_contract": config["controller_contract"],
    |                                                                                                     ^^^^
104 |         })
105 |     finally:
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:108:101
    |
106 |         db.close()
107 |     return {
108 |         "status": "BOOTSTRAPPED", "workspace": str(workspace), "program_digest": lock["lock_digest"],
    |                                                                                                     ^
109 |         "tasks": len(lock["tasks"]), "targets": len(lock["targets"]),
110 |     }
    |

E501 Line too long (105 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:163:101
    |
161 |             repository_id, raw_path = mapping.split("=", 1)
162 |             if repository_id not in target_by_repo:
163 |                 raise ControllerError(f"repository ID is not declared by the Blueprint: {repository_id}")
    |                                                                                                     ^^^^^
164 |             repo = Path(raw_path).expanduser().resolve()
165 |             if run_git(repo, "rev-parse", "--git-dir", check=False).returncode != 0:
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:170:101
    |
168 |             head = run_git(repo, "rev-parse", "HEAD").stdout.strip()
169 |             dirty = bool(run_git(repo, "status", "--porcelain").stdout.strip())
170 |             remote = run_git(repo, "remote", "get-url", "origin", check=False).stdout.strip() or None
    |                                                                                                     ^
171 |             target = target_by_repo[repository_id]
172 |             record = {
    |

E501 Line too long (141 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:177:101
    |
175 | …utc_now(),
176 | …
177 | …"id"], **{k: v for k, v in record.items() if k not in {"repository_id", "target_id"}})
    |                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
178 | …
179 | …oller", {"repositories": results})
    |

E501 Line too long (122 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:221:101
    |
221 | def _approval_valid(db: StateDB, task: dict[str, Any], repo: dict[str, Any] | None, requested_actions: list[str]) -> bool:
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^
222 |     requires = task["risk_tier"] == "T4" or "destructive_change" in requested_actions
223 |     if not requires:
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:236:101
    |
234 |         if approval.get("repository_id") != task.get("repository_id"):
235 |             continue
236 |         if approval.get("program_digest") != program_digest or approval.get("base_sha") != repo.get("head_sha"):
    |                                                                                                     ^^^^^^^^^^^^
237 |             continue
238 |         if not set(requested_actions) <= set(approval.get("permits") or []):
    |

E501 Line too long (106 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:242:101
    |
240 |         if set(requested_actions) & set(approval.get("forbids") or []):
241 |             continue
242 |         if not all(_evidence_valid(db, item) for item in approval.get("prerequisite_evidence_ids") or []):
    |                                                                                                     ^^^^^^
243 |             continue
244 |         if parse_time(approval["expires_at"]) <= now:
    |

E501 Line too long (111 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:250:101
    |
250 | def task_readiness(db: StateDB, task: dict[str, Any], workspace: Path | None = None) -> tuple[bool, list[str]]:
    |                                                                                                     ^^^^^^^^^^^
251 |     blockers: list[str] = []
252 |     if workspace is not None:
    |

E501 Line too long (150 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:260:101
    |
258 | …
259 | …ition_status']}")
260 | …TRACTED", "EXECUTING", "SUBMITTED", "VERIFYING", "PASSED_LOCAL", "COMPLETED", "CANCELLED"}:
    |                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
261 | …['runtime_state']}")
262 | …
    |

E501 Line too long (121 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:272:101
    |
270 |     for unknown_id in task["blocking_unknowns"]:
271 |         item = db.unknown(unknown_id)
272 |         if item is None or item["status"] not in {"resolved", "accepted_risk", "superseded"} or not item["evidence_ids"]:
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^
273 |             blockers.append(f"blocking_unknown:{unknown_id}")
274 |     for evidence_id in task["required_evidence"]:
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:310:101
    |
308 |         else:
309 |             try:
310 |                 contract = validate_source_contract(load_json(Path(task["source_contract_path"])), task)
    |                                                                                                     ^^^^
311 |                 requested_actions = contract["requested_actions"]
312 |                 if any(action not in {"inspect", "local_write", "destructive_change"} for action in requested_actions):
    |

E501 Line too long (119 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:312:101
    |
310 |                 contract = validate_source_contract(load_json(Path(task["source_contract_path"])), task)
311 |                 requested_actions = contract["requested_actions"]
312 |                 if any(action not in {"inspect", "local_write", "destructive_change"} for action in requested_actions):
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^
313 |                     blockers.append("requested_action_requires_uninstalled_adapter")
314 |             except Exception as exc:
    |

E501 Line too long (121 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:330:101
    |
328 |             ready, blockers = task_readiness(db, task, workspace)
329 |             tasks.append({
330 |                 "id": task["id"], "runtime_state": task["runtime_state"], "definition_status": task["definition_status"],
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^
331 |                 "target_id": task["target_id"], "repository_id": task.get("repository_id"),
332 |                 "eligible": ready, "blockers": blockers,
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:338:101
    |
336 |             "program": db.get_meta("program"), "program_digest": db.get_meta("program_digest"),
337 |             "global_halt": db.get_meta("global_halt", False), "tasks": tasks, "gates": db.gates(),
338 |             "decisions": db.decisions(), "unknowns": db.unknowns(), "active_leases": db.active_leases(),
    |                                                                                                     ^^^^
339 |             "ledger": {"valid": ledger_ok, "message": ledger_message},
340 |         }
    |

E501 Line too long (187 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:351:101
    |
349 | …
350 | …
351 | …"wave_id"], "target_id": task["target_id"], "repository_id": task.get("repository_id"), "blockers": blockers}
    |                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
352 | …
353 | …
    |

E501 Line too long (117 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:386:101
    |
384 |             db.create_lease(lease)
385 |         except Exception as exc:
386 |             raise ControllerError(f"repository already has an active writer lease: {task['repository_id']}") from exc
    |                                                                                                     ^^^^^^^^^^^^^^^^^
387 |         db.update_task(task_id, base_sha=repo["head_sha"], branch=branch, lease_id=lease_id, last_error=None)
388 |         db.transition_task(task_id, "LEASED")
    |

E501 Line too long (109 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:387:101
    |
385 |         except Exception as exc:
386 |             raise ControllerError(f"repository already has an active writer lease: {task['repository_id']}") from exc
387 |         db.update_task(task_id, base_sha=repo["head_sha"], branch=branch, lease_id=lease_id, last_error=None)
    |                                                                                                     ^^^^^^^^^
388 |         db.transition_task(task_id, "LEASED")
389 |         ledger.append("TASK_LEASED", holder, lease)
    |

E501 Line too long (124 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:416:101
    |
414 |         if worktree.exists():
415 |             raise ControllerError(f"worktree already exists: {worktree}")
416 |         result = run_git(repo_path, "worktree", "add", "-b", lease["branch"], str(worktree), lease["base_sha"], check=False)
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^
417 |         if result.returncode != 0:
418 |             raise ControllerError(f"failed to create worktree: {result.stderr.strip()}")
    |

E501 Line too long (167 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:422:101
    |
420 | …
421 | …
422 | … task_id, "lease_id": lease["lease_id"], "worktree": str(worktree), "base_sha": lease["base_sha"]})
    |                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
423 | …ch": lease["branch"], "base_sha": lease["base_sha"]}
424 | …
    |

E501 Line too long (120 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:423:101
    |
421 |         db.transition_task(task_id, "PREPARED")
422 |         ledger.append("WORKTREE_PREPARED", "controller", {"task_id": task_id, "lease_id": lease["lease_id"], "worktree": str(worktree…
423 |         return {"task_id": task_id, "worktree": str(worktree), "branch": lease["branch"], "base_sha": lease["base_sha"]}
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^
424 |     finally:
425 |         db.close()
    |

E501 Line too long (129 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:435:101
    |
433 |             raise ControllerError("task must be CONTRACTED")
434 |         db.transition_task(task_id, "EXECUTING")
435 |         ledger.append("TASK_EXECUTION_STARTED", actor, {"task_id": task_id, "contract_digest": task["rendered_contract_digest"]})
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
436 |         return {"status": "EXECUTING", "task_id": task_id}
437 |     finally:
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:460:101
    |
458 |             raise ControllerError("Attempt Receipt base SHA mismatch")
459 |         attempt = db.next_attempt_number(task_id)
460 |         target = workspace / "attempts" / task_id / f"attempt-{attempt:03d}" / "attempt-receipt.json"
    |                                                                                                     ^
461 |         write_json(target, receipt)
462 |         db.create_attempt(task_id, attempt, str(target), utc_now())
    |

E501 Line too long (159 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:465:101
    |
463 | …
464 | …
465 | …task_id, "attempt": attempt, "receipt": str(target), "receipt_digest": digest_object(receipt)})
    |                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
466 | …mpt": attempt, "receipt": str(target)}
467 | …
    |

E501 Line too long (102 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:466:101
    |
464 |         db.transition_task(task_id, "SUBMITTED")
465 |         ledger.append("ATTEMPT_RECORDED", "worker", {"task_id": task_id, "attempt": attempt, "receipt": str(target), "receipt_digest"…
466 |         return {"status": "SUBMITTED", "task_id": task_id, "attempt": attempt, "receipt": str(target)}
    |                                                                                                     ^^
467 |     finally:
468 |         db.close()
    |

E501 Line too long (114 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:498:101
    |
496 |     return {
497 |         "command": command, "status": "PASS" if completed.returncode == 0 else "FAIL",
498 |         "exit_code": completed.returncode, "stdout": completed.stdout[-8000:], "stderr": completed.stderr[-8000:],
    |                                                                                                     ^^^^^^^^^^^^^^
499 |     }
    |

E501 Line too long (102 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:516:101
    |
514 |         ledger_ok, _ = ledger.verify()
515 |         gates["ledger"] = "PASS" if ledger_ok else "FAIL"
516 |         gates["lease"] = "PASS" if lease and lease.get("lease_id") == task.get("lease_id") else "FAIL"
    |                                                                                                     ^^
517 |         contract: dict[str, Any] = {}
518 |         if task.get("rendered_contract_path") and Path(task["rendered_contract_path"]).is_file():
    |

E702 Multiple statements on one line (semicolon)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:523:38
    |
521 |                 _validate_schema(workspace, "task-contract.schema.json", contract)
522 |                 claimed = contract["contract_digest"]
523 |                 body = dict(contract); body.pop("contract_digest", None)
    |                                      ^
524 |                 gates["contract"] = "PASS" if digest_object(body) == claimed == task["rendered_contract_digest"] else "FAIL"
525 |             except Exception:
    |

E501 Line too long (124 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:524:101
    |
522 |                 claimed = contract["contract_digest"]
523 |                 body = dict(contract); body.pop("contract_digest", None)
524 |                 gates["contract"] = "PASS" if digest_object(body) == claimed == task["rendered_contract_digest"] else "FAIL"
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^
525 |             except Exception:
526 |                 gates["contract"] = "FAIL"
    |

E501 Line too long (121 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:529:101
    |
527 | …     else:
528 | …         gates["contract"] = "FAIL"
529 | …     receipt = load_json(Path(attempt["receipt_path"])) if attempt and Path(attempt["receipt_path"]).is_file() else {}
    |                                                                                                   ^^^^^^^^^^^^^^^^^^^^^
530 | …     gates["receipt_binding"] = "PASS" if receipt and receipt.get("task_id") == task_id and receipt.get("contract_digest") == task["…
531 | …     worktree = Path(task["worktree"]) if task.get("worktree") else None
    |

E501 Line too long (288 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:530:101
    |
528 | …
529 | …_path"]).is_file() else {}
530 | …receipt.get("contract_digest") == task["rendered_contract_digest"] and receipt.get("program_digest") == db.get_meta("program_digest") and receipt.get("base_sha") == task["base_sha"] else "FAIL"
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
531 | …
532 | …
    |

E501 Line too long (121 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:536:101
    |
534 |         candidate_sha = None
535 |         if worktree is None or not worktree.is_dir():
536 |             for name in ["base_sha", "changed_files_exact", "scope", "symlink", "worker_validation_claim", "validation"]:
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^
537 |                 gates[name] = "FAIL"
538 |         else:
    |

E501 Line too long (157 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:539:101
    |
537 | …
538 | …
539 | …rge-base", "--is-ancestor", task["base_sha"], "HEAD", check=False).returncode == 0 else "FAIL"
    |                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
540 | …
541 | …or []))
    |

E501 Line too long (116 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:544:101
    |
542 | …     gates["changed_files_exact"] = "PASS" if declared == changed else "FAIL"
543 | …     patterns = contract.get("writable_paths") or []
544 | …     gates["scope"] = "PASS" if changed and all(path_allowed(path, patterns) for path in changed) else "FAIL"
    |                                                                                               ^^^^^^^^^^^^^^^^
545 | …     gates["symlink"] = "PASS" if not any((worktree / path).is_symlink() for path in changed if (worktree / path).exists()) else "FA…
546 | …     claimed_results = receipt.get("validation_results") or []
    |

E501 Line too long (142 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:545:101
    |
543 | …r []
544 | …path_allowed(path, patterns) for path in changed) else "FAIL"
545 | …ree / path).is_symlink() for path in changed if (worktree / path).exists()) else "FAIL"
    |                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
546 | …esults") or []
547 | … item in claimed_results]
    |

E501 Line too long (190 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:548:101
    |
546 | …
547 | …]
548 | …ntract.get("validation_commands") and all(item.get("status") == "PASS" for item in claimed_results) else "FAIL"
    |                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
549 | …ntract.get("validation_commands") or []]
550 | …== "PASS" for item in validations) else "FAIL"
    |

E501 Line too long (119 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:549:101
    |
547 | …     claimed_commands = [item.get("command") for item in claimed_results]
548 | …     gates["worker_validation_claim"] = "PASS" if claimed_commands == contract.get("validation_commands") and all(item.get("status")…
549 | …     validations = [_run_validation(command, worktree) for command in contract.get("validation_commands") or []]
    |                                                                                               ^^^^^^^^^^^^^^^^^^^
550 | …     gates["validation"] = "PASS" if validations and all(item["status"] == "PASS" for item in validations) else "FAIL"
551 | …     candidate_sha = run_git(worktree, "rev-parse", "HEAD").stdout.strip()
    |

E501 Line too long (125 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:550:101
    |
548 | …         gates["worker_validation_claim"] = "PASS" if claimed_commands == contract.get("validation_commands") and all(item.get("stat…
549 | …         validations = [_run_validation(command, worktree) for command in contract.get("validation_commands") or []]
550 | …         gates["validation"] = "PASS" if validations and all(item["status"] == "PASS" for item in validations) else "FAIL"
    |                                                                                                   ^^^^^^^^^^^^^^^^^^^^^^^^^
551 | …         candidate_sha = run_git(worktree, "rev-parse", "HEAD").stdout.strip()
552 | …     gates["residual_unknowns"] = "PASS" if not (receipt.get("residual_unknowns") or []) else "BLOCKED"
    |

E501 Line too long (106 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:552:101
    |
550 | …         gates["validation"] = "PASS" if validations and all(item["status"] == "PASS" for item in validations) else "FAIL"
551 | …         candidate_sha = run_git(worktree, "rev-parse", "HEAD").stdout.strip()
552 | …     gates["residual_unknowns"] = "PASS" if not (receipt.get("residual_unknowns") or []) else "BLOCKED"
    |                                                                                                   ^^^^^^
553 | …     verdict = "PASSED_LOCAL" if gates and all(value == "PASS" for value in gates.values()) else ("STALE" if "STALE" in gates.values…
554 | …     attempt_number = attempt["attempt_number"] if attempt else task["attempts"]
    |

E501 Line too long (152 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:553:101
    |
551 | …HEAD").stdout.strip()
552 | …get("residual_unknowns") or []) else "BLOCKED"
553 | …PASS" for value in gates.values()) else ("STALE" if "STALE" in gates.values() else "FAILED")
    |                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
554 | …t else task["attempts"]
555 | …number):03d}"
    |

E501 Line too long (118 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:561:101
    |
559 |             "task_id": task_id, "contract_digest": task.get("rendered_contract_digest"),
560 |             "program_digest": db.get_meta("program_digest"), "base_sha": task.get("base_sha"),
561 |             "candidate_sha": candidate_sha, "declared_changed_files": sorted(set(receipt.get("changed_files") or [])),
    |                                                                                                     ^^^^^^^^^^^^^^^^^^
562 |             "observed_changed_files": changed, "validations": validations, "gates": gates,
563 |             "verdict": verdict, "evidence_id": evidence_id, "verified_at": utc_now(),
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:571:101
    |
569 |         db.upsert_evidence({
570 |             "id": evidence_id, "type": "test_result", "source": str(target),
571 |             "revision": candidate_sha or task.get("base_sha"), "digest": verification["receipt_digest"],
    |                                                                                                     ^^^^
572 |             "method": "independent_controller_verification", "environment": "local_worktree",
573 |             "producer": "Program Execution Controller", "produced_at": verification["verified_at"],
    |

E501 Line too long (129 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:577:101
    |
575 | …         "status": "available", "supports": [task_id], "contradicts": [], "notes": None,
576 | …     })
577 | …     db.transition_task(task_id, verdict, last_error=None if verdict == "PASSED_LOCAL" else json.dumps(gates, sort_keys=True))
    |                                                                                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
578 | …     ledger.append("ATTEMPT_VERIFIED", "controller", {"task_id": task_id, "verdict": verdict, "receipt": str(target), "receipt_diges…
579 | …     return verification
    |

E501 Line too long (199 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:578:101
    |
576 | …
577 | …OCAL" else json.dumps(gates, sort_keys=True))
578 | …t": verdict, "receipt": str(target), "receipt_digest": verification["receipt_digest"], "evidence_id": evidence_id})
    |                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
579 | …
580 | …
    |

E501 Line too long (117 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:592:101
    |
590 |         db.release_lease(lease["lease_id"])
591 |         db.update_task(task_id, lease_id=None)
592 |         ledger.append("LEASE_RELEASED", actor, {"task_id": task_id, "lease_id": lease["lease_id"], "reason": reason})
    |                                                                                                     ^^^^^^^^^^^^^^^^^
593 |         return {"status": "RELEASED", "task_id": task_id, "lease_id": lease["lease_id"]}
594 |     finally:
    |

E501 Line too long (129 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:612:101
    |
610 |             worktree = Path(lease["worktree"]) if lease.get("worktree") else None
611 |             if worktree and worktree.is_dir():
612 |                 (recovery_root / "status.txt").write_text(run_git(worktree, "status", "--porcelain=v1").stdout, encoding="utf-8")
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
613 |                 patch = run_git(worktree, "diff", "--binary", check=False).stdout
614 |                 (recovery_root / "changes.patch").write_text(patch, encoding="utf-8")
    |

E501 Line too long (150 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:615:101
    |
613 | …", check=False).stdout
614 | …t(patch, encoding="utf-8")
615 | …t(run_git(worktree, "ls-files", "--others", "--exclude-standard").stdout, encoding="utf-8")
    |                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
616 | …adata)
617 | …]}"
    |

E501 Line too long (117 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:620:101
    |
618 |             db.upsert_evidence({
619 |                 "id": evidence_id, "type": "recovery_artifact", "source": str(recovery_root),
620 |                 "revision": lease["base_sha"], "digest": digest_object(metadata), "method": "expired_lease_recovery",
    |                                                                                                     ^^^^^^^^^^^^^^^^^
621 |                 "environment": "controller_runtime", "producer": actor, "produced_at": metadata["recovered_at"],
622 |                 "expires_at": None, "result": "INFORMATIONAL", "status": "available",
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:621:101
    |
619 |                 "id": evidence_id, "type": "recovery_artifact", "source": str(recovery_root),
620 |                 "revision": lease["base_sha"], "digest": digest_object(metadata), "method": "expired_lease_recovery",
621 |                 "environment": "controller_runtime", "producer": actor, "produced_at": metadata["recovered_at"],
    |                                                                                                     ^^^^^^^^^^^^
622 |                 "expires_at": None, "result": "INFORMATIONAL", "status": "available",
623 |                 "supports": [lease["task_id"]], "contradicts": [], "notes": "Expired lease evidence preserved.",
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:623:101
    |
621 |                 "environment": "controller_runtime", "producer": actor, "produced_at": metadata["recovered_at"],
622 |                 "expires_at": None, "result": "INFORMATIONAL", "status": "available",
623 |                 "supports": [lease["task_id"]], "contradicts": [], "notes": "Expired lease evidence preserved.",
    |                                                                                                     ^^^^^^^^^^^^
624 |             })
625 |             db.release_lease(lease["lease_id"])
    |

E501 Line too long (173 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:632:101
    |
630 | …
631 | …
632 | …task_id"], "lease_id": lease["lease_id"], "artifact": str(recovery_root), "evidence_id": evidence_id})
    |                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
633 | …lease["lease_id"], "artifact": str(recovery_root), "evidence_id": evidence_id})
634 | …
    |

E501 Line too long (150 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:633:101
    |
631 | …
632 | …id": lease["task_id"], "lease_id": lease["lease_id"], "artifact": str(recovery_root), "evidence_id": evidence_id})
633 | …"lease_id": lease["lease_id"], "artifact": str(recovery_root), "evidence_id": evidence_id})
    |                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
634 | …
635 | …
    |

E501 Line too long (128 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:647:101
    |
645 |             raise ControllerError("approval Program Lock mismatch")
646 |         task = db.task(approval["task_id"])
647 |         if task is None or approval["target_id"] != task["target_id"] or approval["repository_id"] != task.get("repository_id"):
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
648 |             raise ControllerError("approval task or target mismatch")
649 |         if set(approval["permits"]) & set(approval["forbids"]):
    |

E501 Line too long (165 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:656:101
    |
654 | …
655 | …
656 | … {"approval_id": approval["approval_id"], "task_id": approval["task_id"], "receipt": str(target)})
    |                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
657 | …oval_id"], "receipt": str(target)}
658 | …
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:657:101
    |
655 |         db.add_approval(approval)
656 |         ledger.append("APPROVAL_RECORDED", approval["approved_by"], {"approval_id": approval["approval_id"], "task_id": approval["tas…
657 |         return {"status": "RECORDED", "approval_id": approval["approval_id"], "receipt": str(target)}
    |                                                                                                     ^
658 |     finally:
659 |         db.close()
    |

E501 Line too long (126 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:662:101
    |
662 | def set_decision(workspace: Path, decision_id: str, status_value: str, evidence_ids: list[str], actor: str) -> dict[str, Any]:
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
663 |     db, ledger = open_runtime(workspace)
664 |     try:
    |

E501 Line too long (143 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:672:101
    |
670 | …missing, stale, or invalid")
671 | …nce_ids)
672 | …or, {"decision_id": decision_id, "status": status_value, "evidence_ids": evidence_ids})
    |                                              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
673 | …ecision_id, "evidence_ids": evidence_ids}
674 | …
    |

E501 Line too long (124 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:678:101
    |
678 | def set_unknown(workspace: Path, unknown_id: str, status_value: str, evidence_ids: list[str], actor: str) -> dict[str, Any]:
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^
679 |     db, ledger = open_runtime(workspace)
680 |     try:
    |

E501 Line too long (140 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:688:101
    |
686 | …evidence is missing, stale, or invalid")
687 | …nce_ids)
688 | …tor, {"unknown_id": unknown_id, "status": status_value, "evidence_ids": evidence_ids})
    |                                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
689 | …unknown_id, "evidence_ids": evidence_ids}
690 | …
    |

E501 Line too long (160 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:694:101
    |
694 | …idence_ids: list[str], method: str, actor: str, waiver_id: str | None = None) -> dict[str, Any]:
    |                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
695 | …
696 | …
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:704:101
    |
702 |         if result == "NOT_APPLICABLE_WITH_REASON":
703 |             if not gate["definition"].get("waiver_allowed") or not waiver_id:
704 |                 raise ControllerError("NOT_APPLICABLE_WITH_REASON requires an allowed, explicit waiver")
    |                                                                                                     ^^^^
705 |             waiver = db.waiver(waiver_id)
706 |             if waiver is None or waiver.get("status") != "active" or gate_id not in (waiver.get("scope") or []):
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:706:101
    |
704 |                 raise ControllerError("NOT_APPLICABLE_WITH_REASON requires an allowed, explicit waiver")
705 |             waiver = db.waiver(waiver_id)
706 |             if waiver is None or waiver.get("status") != "active" or gate_id not in (waiver.get("scope") or []):
    |                                                                                                     ^^^^^^^^^^^^
707 |                 raise ControllerError("waiver is missing, inactive, or out of scope")
708 |             if parse_time(waiver["expires_at"]) <= dt.datetime.now(dt.UTC):
    |

E501 Line too long (155 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:728:101
    |
726 | …
727 | …str(target))
728 | …e_id, "result": result, "receipt": str(target), "receipt_digest": receipt["receipt_digest"]})
    |                                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
729 | …
730 | …
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:734:101
    |
734 | def complete_task(workspace: Path, task_id: str, actor: str, evidence_ids: list[str]) -> dict[str, Any]:
    |                                                                                                     ^^^^
735 |     db, ledger = open_runtime(workspace)
736 |     try:
    |

E501 Line too long (113 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:789:101
    |
787 |         unknowns = db.unknowns()
788 |         blocking_gates = [gate for gate in gates if gate["blocking"]]
789 |         required_tasks = [task for task in tasks if task["definition_status"] not in {"cancelled", "superseded"}]
    |                                                                                                     ^^^^^^^^^^^^^
790 |         open_risks = [risk["id"] for risk in db.get_meta("risks", []) if risk.get("status") not in {"closed", "superseded"}]
791 |         unresolved_decisions = [item["id"] for item in decisions if item["status"] == "pending"]
    |

E501 Line too long (124 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:790:101
    |
788 |         blocking_gates = [gate for gate in gates if gate["blocking"]]
789 |         required_tasks = [task for task in tasks if task["definition_status"] not in {"cancelled", "superseded"}]
790 |         open_risks = [risk["id"] for risk in db.get_meta("risks", []) if risk.get("status") not in {"closed", "superseded"}]
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^
791 |         unresolved_decisions = [item["id"] for item in decisions if item["status"] == "pending"]
792 |         unresolved_unknowns = [item["id"] for item in unknowns if item["status"] == "open"]
    |

E501 Line too long (163 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:797:101
    |
795 | …
796 | …
797 | …LETED" for task in required_tasks) and all(_gate_satisfied(db, gate) for gate in blocking_gates):
    |                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
798 | …f open_risks else "CONVERGED"
799 | …
    |

E501 Line too long (122 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:805:101
    |
803 |             "schema": "program-execution-controller.handoff-receipt.v2",
804 |             "handoff_id": f"HANDOFF-{uuid.uuid4().hex[:16]}", "program_id": program["id"],
805 |             "program_digest": db.get_meta("program_digest"), "controller_id": _runtime_config(workspace)["controller_id"],
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^
806 |             "exported_at": utc_now(),
807 |             "runtime_summary": {
    |

E501 Line too long (103 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:812:101
    |
810 |                 "completed_tasks": sum(1 for task in tasks if task["runtime_state"] == "COMPLETED"),
811 |                 "total_required_tasks": len(required_tasks),
812 |                 "blocking_gates_passed": sum(1 for gate in blocking_gates if gate["result"] == "PASS"),
    |                                                                                                     ^^^
813 |                 "total_blocking_gates": len(blocking_gates),
814 |                 "unresolved_decisions": len(unresolved_decisions),
    |

E501 Line too long (151 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:817:101
    |
815 | …ns),
816 | …
817 | …ntime_state"], "target_id": t["target_id"], "last_error": t["last_error"]} for t in tasks],
    |                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
818 | … "evidence_ids": g["evidence_ids"], "evaluation_receipt": g["evaluation_receipt"]} for g in gates],
819 | …s"], "evidence_ids": d["evidence_ids"]} for d in decisions],
    |

E501 Line too long (159 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:818:101
    |
816 | …
817 | …e_state"], "target_id": t["target_id"], "last_error": t["last_error"]} for t in tasks],
818 | …idence_ids": g["evidence_ids"], "evaluation_receipt": g["evaluation_receipt"]} for g in gates],
    |                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
819 | … "evidence_ids": d["evidence_ids"]} for d in decisions],
820 | …"evidence_ids": u["evidence_ids"]} for u in unknowns],
    |

E501 Line too long (120 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:819:101
    |
817 | …     "tasks": [{"id": t["id"], "runtime_state": t["runtime_state"], "target_id": t["target_id"], "last_error": t["last_error"]} for …
818 | …     "gates": [{"id": g["id"], "result": g["result"], "evidence_ids": g["evidence_ids"], "evaluation_receipt": g["evaluation_receipt…
819 | …     "decisions": [{"id": d["id"], "status": d["status"], "evidence_ids": d["evidence_ids"]} for d in decisions],
    |                                                                                               ^^^^^^^^^^^^^^^^^^^^
820 | …     "unknowns": [{"id": u["id"], "status": u["status"], "evidence_ids": u["evidence_ids"]} for u in unknowns],
821 | …     "approvals": [{"approval_id": a["approval_id"], "task_id": a["task_id"], "expires_at": a["expires_at"]} for a in db.approvals()…
    |

E501 Line too long (118 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:820:101
    |
818 | …     "gates": [{"id": g["id"], "result": g["result"], "evidence_ids": g["evidence_ids"], "evaluation_receipt": g["evaluation_receipt…
819 | …     "decisions": [{"id": d["id"], "status": d["status"], "evidence_ids": d["evidence_ids"]} for d in decisions],
820 | …     "unknowns": [{"id": u["id"], "status": u["status"], "evidence_ids": u["evidence_ids"]} for u in unknowns],
    |                                                                                               ^^^^^^^^^^^^^^^^^^
821 | …     "approvals": [{"approval_id": a["approval_id"], "task_id": a["task_id"], "expires_at": a["expires_at"]} for a in db.approvals()…
822 | …     "residual_risks": open_risks,
    |

E501 Line too long (141 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:821:101
    |
819 | …status"], "evidence_ids": d["evidence_ids"]} for d in decisions],
820 | …tatus"], "evidence_ids": u["evidence_ids"]} for u in unknowns],
821 | …d"], "task_id": a["task_id"], "expires_at": a["expires_at"]} for a in db.approvals()],
    |                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
822 | …
823 | …on,
    |

E501 Line too long (180 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/controller.py:830:101
    |
828 | …f_id']}.json"
829 | …
830 | …andoff_id"], "output": str(output), "archive": str(archive), "receipt_digest": receipt["receipt_digest"]})
    |                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
831 | …
832 | …
    |

E501 Line too long (106 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:151:101
    |
149 |     def set_meta(self, key: str, value: Any) -> None:
150 |         self.conn.execute(
151 |             "INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
    |                                                                                                     ^^^^^^
152 |             (key, json.dumps(value, sort_keys=True)),
153 |         )
    |

E501 Line too long (109 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:161:101
    |
160 |     def upsert_repository(self, repository_id: str, target_id: str, **fields: Any) -> None:
161 |         existing = self.repository(repository_id) or {"repository_id": repository_id, "target_id": target_id}
    |                                                                                                     ^^^^^^^^^
162 |         existing.update(fields)
163 |         self.conn.execute(
    |

E501 Line too long (130 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:164:101
    |
162 |         existing.update(fields)
163 |         self.conn.execute(
164 |             """INSERT INTO repositories(repository_id,target_id,local_path,current_branch,head_sha,dirty,remote_url,reconciled_at)
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
165 |                VALUES(:repository_id,:target_id,:local_path,:current_branch,:head_sha,:dirty,:remote_url,:reconciled_at)
166 |                ON CONFLICT(repository_id) DO UPDATE SET target_id=excluded.target_id,local_path=excluded.local_path,
    |

E501 Line too long (116 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:166:101
    |
164 |             """INSERT INTO repositories(repository_id,target_id,local_path,current_branch,head_sha,dirty,remote_url,reconciled_at)
165 |                VALUES(:repository_id,:target_id,:local_path,:current_branch,:head_sha,:dirty,:remote_url,:reconciled_at)
166 |                ON CONFLICT(repository_id) DO UPDATE SET target_id=excluded.target_id,local_path=excluded.local_path,
    |                                                                                                     ^^^^^^^^^^^^^^^^
167 |                current_branch=excluded.current_branch,head_sha=excluded.head_sha,dirty=excluded.dirty,
168 |                remote_url=excluded.remote_url,reconciled_at=excluded.reconciled_at""",
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:183:101
    |
182 |     def repository(self, repository_id: str) -> dict[str, Any] | None:
183 |         row = self.conn.execute("SELECT * FROM repositories WHERE repository_id=?", (repository_id,)).fetchone()
    |                                                                                                     ^^^^^^^^^^^^
184 |         return None if row is None else dict(row)
    |

E501 Line too long (108 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:187:101
    |
186 |     def repositories(self) -> list[dict[str, Any]]:
187 |         return [dict(row) for row in self.conn.execute("SELECT * FROM repositories ORDER BY repository_id")]
    |                                                                                                     ^^^^^^^^
188 |
189 |     @staticmethod
    |

E501 Line too long (111 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:193:101
    |
191 |         return {
192 |             "dependencies", "required_decisions", "blocking_unknowns", "required_evidence",
193 |             "completion_gates", "authorization_ceiling", "required_acceptance", "required_validation_commands",
    |                                                                                                     ^^^^^^^^^^^
194 |         }
    |

E501 Line too long (105 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:208:101
    |
206 |             "required_evidence": json.dumps(task.get("required_evidence") or []),
207 |             "completion_gates": json.dumps(task.get("completion_gates") or []),
208 |             "authorization_ceiling": json.dumps(task.get("authorization_ceiling") or {}, sort_keys=True),
    |                                                                                                     ^^^^^
209 |             "required_acceptance": json.dumps(task.get("required_acceptance") or []),
210 |             "required_validation_commands": json.dumps(task.get("required_validation_commands") or []),
    |

E501 Line too long (103 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:210:101
    |
208 |             "authorization_ceiling": json.dumps(task.get("authorization_ceiling") or {}, sort_keys=True),
209 |             "required_acceptance": json.dumps(task.get("required_acceptance") or []),
210 |             "required_validation_commands": json.dumps(task.get("required_validation_commands") or []),
    |                                                                                                     ^^^
211 |             "risk_tier": task["risk_tier"], "definition_status": task["definition_status"],
212 |             "runtime_state": current["runtime_state"] if current else "BLOCKED",
    |

E501 Line too long (151 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:213:101
    |
211 | …us": task["definition_status"],
212 | …rent else "BLOCKED",
213 | …nt else ("not_required" if task["execution_kind"] == "program_control" else "intent_only"),
    |                                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
214 | …_path"] if current else None,
215 | …ct_digest"] if current else None,
    |

E501 Line too long (241 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:229:101
    |
227 | …
228 | …
229 | …ce_contract_digest", "rendered_contract_path", "rendered_contract_digest", "base_sha", "branch", "worktree", "lease_id", "attempts", "last_error"}
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
230 | …
231 | …
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:232:101
    |
230 |         )
231 |         self.conn.execute(
232 |             f"INSERT INTO tasks({columns}) VALUES({placeholders}) ON CONFLICT(id) DO UPDATE SET {updates}",
    |                                                                                                     ^^^^^^^
233 |             payload,
234 |         )
    |

E501 Line too long (102 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:250:101
    |
248 |         return [self._task_row(row) for row in self.conn.execute("SELECT * FROM tasks ORDER BY id")]
249 |
250 |     def transition_task(self, task_id: str, new_state: str, *, last_error: str | None = None) -> None:
    |                                                                                                     ^^
251 |         if new_state not in TASK_STATES:
252 |             raise ValueError(f"invalid task state: {new_state}")
    |

E501 Line too long (120 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:259:101
    |
257 |         if new_state != current and new_state not in ALLOWED_TRANSITIONS[current]:
258 |             raise ValueError(f"invalid task transition: {current} -> {new_state}")
259 |         self.conn.execute("UPDATE tasks SET runtime_state=?, last_error=? WHERE id=?", (new_state, last_error, task_id))
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^
260 |         self.conn.commit()
    |

E501 Line too long (103 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:264:101
    |
262 |     def update_task(self, task_id: str, **fields: Any) -> None:
263 |         allowed = {
264 |             "scope_status", "source_contract_path", "source_contract_digest", "rendered_contract_path",
    |                                                                                                     ^^^
265 |             "rendered_contract_digest", "base_sha", "branch", "worktree", "lease_id", "attempts", "last_error",
266 |         }
    |

E501 Line too long (111 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:265:101
    |
263 |         allowed = {
264 |             "scope_status", "source_contract_path", "source_contract_digest", "rendered_contract_path",
265 |             "rendered_contract_digest", "base_sha", "branch", "worktree", "lease_id", "attempts", "last_error",
    |                                                                                                     ^^^^^^^^^^^
266 |         }
267 |         unknown = set(fields) - allowed
    |

E501 Line too long (115 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:279:101
    |
277 |         existing = self.gate(gate["id"])
278 |         self.conn.execute(
279 |             """INSERT INTO gates(id,definition,result,blocking,evidence_ids,evaluation_receipt) VALUES(?,?,?,?,?,?)
    |                                                                                                     ^^^^^^^^^^^^^^^
280 |                ON CONFLICT(id) DO UPDATE SET definition=excluded.definition,blocking=excluded.blocking""",
281 |             (
    |

E501 Line too long (106 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:280:101
    |
278 |         self.conn.execute(
279 |             """INSERT INTO gates(id,definition,result,blocking,evidence_ids,evaluation_receipt) VALUES(?,?,?,?,?,?)
280 |                ON CONFLICT(id) DO UPDATE SET definition=excluded.definition,blocking=excluded.blocking""",
    |                                                                                                     ^^^^^^
281 |             (
282 |                 gate["id"], json.dumps(gate, sort_keys=True), existing["result"] if existing else "UNKNOWN",
    |

E501 Line too long (108 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:282:101
    |
280 |                ON CONFLICT(id) DO UPDATE SET definition=excluded.definition,blocking=excluded.blocking""",
281 |             (
282 |                 gate["id"], json.dumps(gate, sort_keys=True), existing["result"] if existing else "UNKNOWN",
    |                                                                                                     ^^^^^^^^
283 |                 int(bool(gate.get("blocking", True))), json.dumps(existing["evidence_ids"] if existing else []),
284 |                 existing.get("evaluation_receipt") if existing else None,
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:283:101
    |
281 |             (
282 |                 gate["id"], json.dumps(gate, sort_keys=True), existing["result"] if existing else "UNKNOWN",
283 |                 int(bool(gate.get("blocking", True))), json.dumps(existing["evidence_ids"] if existing else []),
    |                                                                                                     ^^^^^^^^^^^^
284 |                 existing.get("evaluation_receipt") if existing else None,
285 |             ),
    |

E501 Line too long (102 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:299:101
    |
298 |     def gates(self) -> list[dict[str, Any]]:
299 |         return [self.gate(row["id"]) for row in self.conn.execute("SELECT id FROM gates ORDER BY id")]  # type: ignore[list-item]
    |                                                                                                     ^^
300 |
301 |     def set_gate(self, gate_id: str, result: str, evidence_ids: list[str], receipt: str) -> None:
    |

E501 Line too long (136 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:313:101
    |
311 | …xisting else item.get("evidence_ids", [])
312 | …
313 | …e_ids,source) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET source=excluded.source",
    |                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
314 | …_ids), json.dumps(item, sort_keys=True)),
315 | …
    |

E702 Multiple statements on one line (semicolon)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:322:25
    |
320 |         if row is None:
321 |             return None
322 |         item = dict(row); item["evidence_ids"] = json.loads(item["evidence_ids"]); item["source"] = json.loads(item["source"])
    |                         ^
323 |         return item
    |

E702 Multiple statements on one line (semicolon)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:322:82
    |
320 |         if row is None:
321 |             return None
322 |         item = dict(row); item["evidence_ids"] = json.loads(item["evidence_ids"]); item["source"] = json.loads(item["source"])
    |                                                                                  ^
323 |         return item
    |

E501 Line too long (126 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:322:101
    |
320 |         if row is None:
321 |             return None
322 |         item = dict(row); item["evidence_ids"] = json.loads(item["evidence_ids"]); item["source"] = json.loads(item["source"])
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
323 |         return item
    |

E501 Line too long (110 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:326:101
    |
325 |     def decisions(self) -> list[dict[str, Any]]:
326 |         return [self.decision(row["id"]) for row in self.conn.execute("SELECT id FROM decisions ORDER BY id")]  # type: ignore[list-i…
    |                                                                                                     ^^^^^^^^^^
327 |
328 |     def set_decision(self, decision_id: str, status: str, evidence_ids: list[str]) -> None:
    |

E501 Line too long (134 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:331:101
    |
329 |         if status not in {"pending", "accepted", "rejected", "superseded"}:
330 |             raise ValueError(f"invalid decision status: {status}")
331 |         self.conn.execute("UPDATE decisions SET status=?, evidence_ids=? WHERE id=?", (status, json.dumps(evidence_ids), decision_id))
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
332 |         self.conn.commit()
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:337:101
    |
335 | …     existing = self.unknown(item["id"])
336 | …     status = existing["status"] if existing else item.get("status", "open")
337 | …     evidence_ids = existing["evidence_ids"] if existing else item.get("resolution_evidence_ids", [])
    |                                                                                                   ^^^^
338 | …     self.conn.execute(
339 | …         "INSERT INTO unknowns(id,status,blocks,evidence_ids,source) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET blocks=excluded…
    |

E501 Line too long (167 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:339:101
    |
337 | …m.get("resolution_evidence_ids", [])
338 | …
339 | …ce) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET blocks=excluded.blocks,source=excluded.source",
    |                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
340 | …), json.dumps(evidence_ids), json.dumps(item, sort_keys=True)),
341 | …
    |

E501 Line too long (131 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:340:101
    |
338 | …
339 | …,evidence_ids,source) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET blocks=excluded.blocks,source=excluded.source",
340 | …et("blocks") or []), json.dumps(evidence_ids), json.dumps(item, sort_keys=True)),
    |                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
341 | …
342 | …
    |

E702 Multiple statements on one line (semicolon)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:348:25
    |
346 | …     if row is None:
347 | …         return None
348 | …     item = dict(row); item["blocks"] = json.loads(item["blocks"]); item["evidence_ids"] = json.loads(item["evidence_ids"]); item["s…
    |                       ^
349 | …     return item
    |

E702 Multiple statements on one line (semicolon)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:348:70
    |
346 | …     if row is None:
347 | …         return None
348 | …     item = dict(row); item["blocks"] = json.loads(item["blocks"]); item["evidence_ids"] = json.loads(item["evidence_ids"]); item["s…
    |                                                                    ^
349 | …     return item
    |

E501 Line too long (171 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:348:101
    |
346 | …
347 | …
348 | … item["evidence_ids"] = json.loads(item["evidence_ids"]); item["source"] = json.loads(item["source"])
    |                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
349 | …
    |

E702 Multiple statements on one line (semicolon)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:348:127
    |
346 | …     if row is None:
347 | …         return None
348 | …     item = dict(row); item["blocks"] = json.loads(item["blocks"]); item["evidence_ids"] = json.loads(item["evidence_ids"]); item["s…
    |                                                                                                                             ^
349 | …     return item
    |

E501 Line too long (108 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:352:101
    |
351 |     def unknowns(self) -> list[dict[str, Any]]:
352 |         return [self.unknown(row["id"]) for row in self.conn.execute("SELECT id FROM unknowns ORDER BY id")]  # type: ignore[list-ite…
    |                                                                                                     ^^^^^^^^
353 |
354 |     def set_unknown(self, unknown_id: str, status: str, evidence_ids: list[str]) -> None:
    |

E501 Line too long (132 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:357:101
    |
355 |         if status not in {"open", "resolved", "accepted_risk", "superseded"}:
356 |             raise ValueError(f"invalid unknown status: {status}")
357 |         self.conn.execute("UPDATE unknowns SET status=?, evidence_ids=? WHERE id=?", (status, json.dumps(evidence_ids), unknown_id))
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
358 |         self.conn.commit()
    |

E501 Line too long (131 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:361:101
    |
360 |     def upsert_waiver(self, item: dict[str, Any]) -> None:
361 |         self.conn.execute("INSERT OR REPLACE INTO waivers(id,payload) VALUES(?,?)", (item["id"], json.dumps(item, sort_keys=True)))
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
362 |         self.conn.commit()
    |

E501 Line too long (115 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:369:101
    |
368 |     def waivers(self) -> list[dict[str, Any]]:
369 |         return [json.loads(row["payload"]) for row in self.conn.execute("SELECT payload FROM waivers ORDER BY id")]
    |                                                                                                     ^^^^^^^^^^^^^^^
370 |
371 |     def upsert_evidence(self, item: dict[str, Any]) -> None:
    |

E501 Line too long (132 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:372:101
    |
371 |     def upsert_evidence(self, item: dict[str, Any]) -> None:
372 |         self.conn.execute("INSERT OR REPLACE INTO evidence(id,payload) VALUES(?,?)", (item["id"], json.dumps(item, sort_keys=True)))
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
373 |         self.conn.commit()
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:376:101
    |
375 |     def evidence(self, evidence_id: str) -> dict[str, Any] | None:
376 |         row = self.conn.execute("SELECT payload FROM evidence WHERE id=?", (evidence_id,)).fetchone()
    |                                                                                                     ^
377 |         return None if row is None else json.loads(row["payload"])
    |

E501 Line too long (116 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:380:101
    |
379 |     def evidence_items(self) -> list[dict[str, Any]]:
380 |         return [json.loads(row["payload"]) for row in self.conn.execute("SELECT payload FROM evidence ORDER BY id")]
    |                                                                                                     ^^^^^^^^^^^^^^^^
381 |
382 |     def create_lease(self, lease: dict[str, Any]) -> None:
    |

E501 Line too long (171 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:384:101
    |
382 | …
383 | …
384 | …base_sha,branch,worktree,contract_digest,issued_at,expires_at,active) VALUES(?,?,?,?,?,?,?,?,?,?,1)",
    |                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
385 | …"], lease["holder"], lease["base_sha"], lease["branch"], lease.get("worktree"), lease.get("contract_digest"), lease["issued_at"], le…
386 | …
    |

E501 Line too long (221 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:385:101
    |
383 | …
384 | …contract_digest,issued_at,expires_at,active) VALUES(?,?,?,?,?,?,?,?,?,?,1)",
385 | …e["base_sha"], lease["branch"], lease.get("worktree"), lease.get("contract_digest"), lease["issued_at"], lease["expires_at"]),
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
386 | …
387 | …
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:394:101
    |
392 |             raise ValueError("unsupported lease update")
393 |         sets = ",".join(f"{name}=?" for name in fields)
394 |         self.conn.execute(f"UPDATE leases SET {sets} WHERE lease_id=?", [*fields.values(), lease_id])
    |                                                                                                     ^
395 |         self.conn.commit()
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:398:101
    |
397 |     def active_lease_for_task(self, task_id: str) -> dict[str, Any] | None:
398 |         row = self.conn.execute("SELECT * FROM leases WHERE task_id=? AND active=1", (task_id,)).fetchone()
    |                                                                                                     ^^^^^^^
399 |         return None if row is None else dict(row)
    |

E501 Line too long (113 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:402:101
    |
401 |     def active_leases(self) -> list[dict[str, Any]]:
402 |         return [dict(row) for row in self.conn.execute("SELECT * FROM leases WHERE active=1 ORDER BY issued_at")]
    |                                                                                                     ^^^^^^^^^^^^^
403 |
404 |     def release_lease(self, lease_id: str) -> None:
    |

E501 Line too long (133 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:409:101
    |
408 |     def next_attempt_number(self, task_id: str) -> int:
409 |         row = self.conn.execute("SELECT COALESCE(MAX(attempt_number),0)+1 AS n FROM attempts WHERE task_id=?", (task_id,)).fetchone()
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
410 |         return int(row["n"])
    |

E501 Line too long (108 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:412:101
    |
410 |         return int(row["n"])
411 |
412 |     def create_attempt(self, task_id: str, attempt_number: int, receipt_path: str, created_at: str) -> None:
    |                                                                                                     ^^^^^^^^
413 |         self.conn.execute(
414 |             "INSERT INTO attempts(task_id,attempt_number,receipt_path,status,created_at) VALUES(?,?,?,?,?)",
    |

E501 Line too long (108 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:414:101
    |
412 |     def create_attempt(self, task_id: str, attempt_number: int, receipt_path: str, created_at: str) -> None:
413 |         self.conn.execute(
414 |             "INSERT INTO attempts(task_id,attempt_number,receipt_path,status,created_at) VALUES(?,?,?,?,?)",
    |                                                                                                     ^^^^^^^^
415 |             (task_id, attempt_number, receipt_path, "RECORDED", created_at),
416 |         )
    |

E501 Line too long (133 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:420:101
    |
419 |     def latest_attempt(self, task_id: str) -> dict[str, Any] | None:
420 |         row = self.conn.execute("SELECT * FROM attempts WHERE task_id=? ORDER BY attempt_number DESC LIMIT 1", (task_id,)).fetchone()
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
421 |         return None if row is None else dict(row)
    |

E501 Line too long (159 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:424:101
    |
423 | …
424 | …oval_id,payload) VALUES(?,?)", (approval["approval_id"], json.dumps(approval, sort_keys=True)))
    |                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
425 | …
    |

E501 Line too long (126 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/pec/state.py:428:101
    |
427 |     def approvals(self) -> list[dict[str, Any]]:
428 |         return [json.loads(row["payload"]) for row in self.conn.execute("SELECT payload FROM approvals ORDER BY approval_id")]
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
    |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/run_negative_tests.py:13:34
   |
11 | def run(cmd:list[str], success:bool)->subprocess.CompletedProcess[str]:
12 |     r=subprocess.run(cmd,text=True,capture_output=True,check=False,timeout=180,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
13 |     if (r.returncode==0)!=success: raise SystemExit(f"unexpected result: {cmd}\n{r.stdout}\n{r.stderr}")
   |                                  ^
14 |     return r
15 | def main()->int:
   |

E501 Line too long (104 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/run_negative_tests.py:13:101
   |
11 | def run(cmd:list[str], success:bool)->subprocess.CompletedProcess[str]:
12 |     r=subprocess.run(cmd,text=True,capture_output=True,check=False,timeout=180,env={**os.environ,"PYTHONDONTWRITEBYTECODE":"1"})
13 |     if (r.returncode==0)!=success: raise SystemExit(f"unexpected result: {cmd}\n{r.stdout}\n{r.stderr}")
   |                                                                                                     ^^^^
14 |     return r
15 | def main()->int:
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/run_negative_tests.py:18:76
   |
16 |     run([sys.executable,str(ROOT/"scripts/validate_controller.py"),str(ROOT),"--mode","template"],True)
17 |     policy=(ROOT/"policy/autonomy.yaml").read_text()
18 |     if "push: denied" not in policy or "pull_request: denied" not in policy: raise SystemExit("remote denial missing")
   |                                                                            ^
19 |     print(json.dumps({"status":"PASS","fixtures":["controller_structure","remote_authority_denial"]},indent=2));return 0
20 | if __name__=="__main__":raise SystemExit(main())
   |

E501 Line too long (118 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/run_negative_tests.py:18:101
   |
16 |     run([sys.executable,str(ROOT/"scripts/validate_controller.py"),str(ROOT),"--mode","template"],True)
17 |     policy=(ROOT/"policy/autonomy.yaml").read_text()
18 |     if "push: denied" not in policy or "pull_request: denied" not in policy: raise SystemExit("remote denial missing")
   |                                                                                                     ^^^^^^^^^^^^^^^^^^
19 |     print(json.dumps({"status":"PASS","fixtures":["controller_structure","remote_authority_denial"]},indent=2));return 0
20 | if __name__=="__main__":raise SystemExit(main())
   |

E501 Line too long (120 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/run_negative_tests.py:19:101
   |
17 |     policy=(ROOT/"policy/autonomy.yaml").read_text()
18 |     if "push: denied" not in policy or "pull_request: denied" not in policy: raise SystemExit("remote denial missing")
19 |     print(json.dumps({"status":"PASS","fixtures":["controller_structure","remote_authority_denial"]},indent=2));return 0
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^
20 | if __name__=="__main__":raise SystemExit(main())
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/run_negative_tests.py:19:112
   |
17 |     policy=(ROOT/"policy/autonomy.yaml").read_text()
18 |     if "push: denied" not in policy or "pull_request: denied" not in policy: raise SystemExit("remote denial missing")
19 |     print(json.dumps({"status":"PASS","fixtures":["controller_structure","remote_authority_denial"]},indent=2));return 0
   |                                                                                                                ^
20 | if __name__=="__main__":raise SystemExit(main())
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/run_negative_tests.py:20:24
   |
18 |     if "push: denied" not in policy or "pull_request: denied" not in policy: raise SystemExit("remote denial missing")
19 |     print(json.dumps({"status":"PASS","fixtures":["controller_structure","remote_authority_denial"]},indent=2));return 0
20 | if __name__=="__main__":raise SystemExit(main())
   |                        ^
   |

E501 Line too long (148 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:59:101
   |
57 | …
58 | …NCY_GRAPH.yaml"},
59 | …lgorithm": "sha256", "unknown_contract": "reject", "source_change": "mark_runtime_stale"},
   |                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
60 | …
61 | …
   |

E501 Line too long (109 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:66:101
   |
64 |             "id": "test-program", "name": "Test Program", "version": "2.0.0", "owner": "operator",
65 |             "definition_status": "accepted", "snapshot_at": "2026-08-01T13:00:00-04:00",
66 |             "objective": "Exercise the Controller", "problem_statement": "Execution requires governed proof",
   |                                                                                                     ^^^^^^^^^
67 |             "target_state": "The bounded change is independently verified",
68 |             "scope": {"include": ["repo-a"], "exclude": ["remote mutation"]},
   |

E501 Line too long (169 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:69:101
   |
67 | …ified",
68 | …ation"]},
69 | …v2", "controller_minimum": "program-execution-controller.v2", "pair": "program-execution-system.v2"},
   |                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
70 | …erified_evidence", "UNKNOWN"],
71 | …,
   |

E501 Line too long (117 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:72:101
   |
70 |             "authority_order": ["operator", "accepted_blueprint", "verified_evidence", "UNKNOWN"],
71 |             "operating_rules": ["controller_may_narrow_never_widen"],
72 |             "terminal_verdicts": ["CONVERGED", "CONVERGED_WITH_NON_BLOCKING_RISKS", "NOT_CONVERGED", "INCONCLUSIVE"],
   |                                                                                                     ^^^^^^^^^^^^^^^^^
73 |         },
74 |     })
   |

E501 Line too long (112 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:78:101
   |
76 |         "schema": "program-execution-blueprint.execution-targets.v2", "schema_version": "2.0.0",
77 |         "targets": [{
78 |             "id": "TARGET-001", "name": "Repository A", "kind": "git_repository", "authority_owner": "operator",
   |                                                                                                     ^^^^^^^^^^^^
79 |             "execution_mode": "repo_local", "repository_id": "repo-a", "source_of_truth": "git",
80 |             "environments": ["local"], "mutability": "reversible", "expected_revision": "UNKNOWN", "adapter": "git",
   |

E501 Line too long (116 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:80:101
   |
78 |             "id": "TARGET-001", "name": "Repository A", "kind": "git_repository", "authority_owner": "operator",
79 |             "execution_mode": "repo_local", "repository_id": "repo-a", "source_of_truth": "git",
80 |             "environments": ["local"], "mutability": "reversible", "expected_revision": "UNKNOWN", "adapter": "git",
   |                                                                                                     ^^^^^^^^^^^^^^^^
81 |         }],
82 |     })
   |

E501 Line too long (146 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:85:101
   |
83 | …
84 | …registry.v2", "schema_version": "2.0.0",
85 | …"projection_does_not_transfer_authority": True, "unresolved_conflict_result": "BLOCKED"},
   |                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
86 | …
87 | …ry implementation", "owner_target_id": "TARGET-001",
   |

E501 Line too long (109 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:87:101
   |
85 | …     "policy": {"one_owner_per_responsibility": True, "projection_does_not_transfer_authority": True, "unresolved_conflict_result": "…
86 | …     "responsibilities": [{
87 | …         "id": "AUTH-001", "responsibility": "repository implementation", "owner_target_id": "TARGET-001",
   |                                                                                                   ^^^^^^^^^
88 | …         "source_of_truth": "repo-a", "consumers": ["controller"], "allowed_roles": ["authority"],
89 | …         "prohibited_owner_target_ids": [], "enforcement": ["source contract"], "validation_gate_ids": ["GATE-001"], "definition_stat…
   |

E501 Line too long (101 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:88:101
   |
86 | …     "responsibilities": [{
87 | …         "id": "AUTH-001", "responsibility": "repository implementation", "owner_target_id": "TARGET-001",
88 | …         "source_of_truth": "repo-a", "consumers": ["controller"], "allowed_roles": ["authority"],
   |                                                                                                   ^
89 | …         "prohibited_owner_target_ids": [], "enforcement": ["source contract"], "validation_gate_ids": ["GATE-001"], "definition_stat…
90 | …     }],
   |

E501 Line too long (150 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:89:101
   |
87 | … implementation", "owner_target_id": "TARGET-001",
88 | …troller"], "allowed_roles": ["authority"],
89 | …": ["source contract"], "validation_gate_ids": ["GATE-001"], "definition_status": "active",
   |                                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
90 | …
91 | …
   |

E501 Line too long (104 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:97:101
   |
95 |         decisions = [{
96 |             "id": "DEC-001", "question": "Proceed?", "status": "pending", "owner": "operator",
97 |             "options": [{"id": "A", "description": "Proceed", "benefits": ["test"], "risks": ["test"]}],
   |                                                                                                     ^^^^
98 |             "selected_option": None, "rationale": None, "evidence_ids": [], "blocks": ["TASK-001"],
99 |             "required_by": "TASK-001", "supersedes": None,
   |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:102:101
    |
100 |         }]
101 |         unknowns = [{
102 |             "id": "UNK-001", "topic": "Input certainty", "owner": "operator", "blocks": ["TASK-001"],
    |                                                                                                     ^
103 |             "safe_state": "Do not execute", "resolution_requirements": ["inspect evidence"],
104 |             "resolution_evidence_ids": [], "status": "open", "resolved_at": None,
    |

E501 Line too long (194 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:106:101
    |
104 | …
105 | …
106 | …eprint.decision-register.v2", "schema_version": "2.0.0", "policy": "No silent defaults", "decisions": decisions})
    |                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
107 | …print.unknown-register.v2", "schema_version": "2.0.0", "policy": "Scoped blocking", "unknowns": unknowns})
108 | …
    |

E501 Line too long (187 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:107:101
    |
105 | …
106 | …blueprint.decision-register.v2", "schema_version": "2.0.0", "policy": "No silent defaults", "decisions": decisions})
107 | …lueprint.unknown-register.v2", "schema_version": "2.0.0", "policy": "Scoped blocking", "unknowns": unknowns})
    |                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
108 | …
109 | …
    |

E501 Line too long (120 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:111:101
    |
109 |     if open_risk:
110 |         risks = [{
111 |             "id": "RISK-001", "risk": "Residual risk", "severity": "low", "likelihood": "possible", "owner": "operator",
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^
112 |             "trigger": "observed", "preventive_controls": ["verify"], "contingency": ["rollback"],
113 |             "related_tasks": ["TASK-001"], "related_gates": ["GATE-001"], "acceptance_decision_id": None, "status": "open",
    |

E501 Line too long (123 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:113:101
    |
111 |             "id": "RISK-001", "risk": "Residual risk", "severity": "low", "likelihood": "possible", "owner": "operator",
112 |             "trigger": "observed", "preventive_controls": ["verify"], "contingency": ["rollback"],
113 |             "related_tasks": ["TASK-001"], "related_gates": ["GATE-001"], "acceptance_decision_id": None, "status": "open",
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^
114 |         }]
115 |     write_yaml(root / "RISK_REGISTER.yaml", {"schema": "program-execution-blueprint.risk-register.v2", "schema_version": "2.0.0", "ri…
    |

E501 Line too long (146 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:115:101
    |
113 | …": ["GATE-001"], "acceptance_decision_id": None, "status": "open",
114 | …
115 | …rogram-execution-blueprint.risk-register.v2", "schema_version": "2.0.0", "risks": risks})
    |                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
116 | …"program-execution-blueprint.waiver-register.v2", "schema_version": "2.0.0", "policy": {"implicit_waivers_forbidden": True, "expired…
117 | …
    |

E501 Line too long (233 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:116:101
    |
114 | …
115 | …er.v2", "schema_version": "2.0.0", "risks": risks})
116 | …gister.v2", "schema_version": "2.0.0", "policy": {"implicit_waivers_forbidden": True, "expired_waiver_non_passing": True}, "waivers": []})
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
117 | …
118 | …
    |

E501 Line too long (109 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:120:101
    |
118 |         "schema": "program-execution-blueprint.evidence-catalog.v2", "schema_version": "2.0.0",
119 |         "evidence": [{
120 |             "id": "EVID-PLAN", "type": "source_snapshot", "source": "test fixture", "revision": "fixture-v2",
    |                                                                                                     ^^^^^^^^^
121 |             "digest": None, "method": "fixture inspection", "environment": "planning", "producer": "test",
122 |             "produced_at": "2026-08-01T13:00:00-04:00", "expires_at": None, "result": "PASS",
    |

E501 Line too long (106 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:121:101
    |
119 |         "evidence": [{
120 |             "id": "EVID-PLAN", "type": "source_snapshot", "source": "test fixture", "revision": "fixture-v2",
121 |             "digest": None, "method": "fixture inspection", "environment": "planning", "producer": "test",
    |                                                                                                     ^^^^^^
122 |             "produced_at": "2026-08-01T13:00:00-04:00", "expires_at": None, "result": "PASS",
123 |             "status": "available", "supports": ["TASK-001"], "contradicts": [], "notes": None,
    |

E501 Line too long (187 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:126:101
    |
124 | …
125 | …
126 | …rint.do-not-build.v2", "schema_version": "2.0.0", "prohibited_primary_paths": [], "allowed_experiments": []})
    |                        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
127 | …
128 | …a_version": "2.0.0",
    |

E501 Line too long (122 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:129:101
    |
127 |     write_yaml(root / "CURRENT_STATE_DELTA.yaml", {
128 |         "schema": "program-execution-blueprint.current-state-delta.v2", "schema_version": "2.0.0",
129 |         "snapshot_at": "2026-08-01T13:00:00-04:00", "freshness_policy": {"maximum_age": "30d", "stale_result": "BLOCKED"},
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^
130 |         "sources": [{"source_id": "SRC-001", "evidence_id": "EVID-PLAN", "revision": "fixture-v2", "freshness": "fresh"}],
131 |         "deltas": [{"id": "DELTA-001", "target_id": "TARGET-001", "expected_state": "result exists", "observed_state": "result absent…
    |

E501 Line too long (122 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:130:101
    |
128 | …     "schema": "program-execution-blueprint.current-state-delta.v2", "schema_version": "2.0.0",
129 | …     "snapshot_at": "2026-08-01T13:00:00-04:00", "freshness_policy": {"maximum_age": "30d", "stale_result": "BLOCKED"},
130 | …     "sources": [{"source_id": "SRC-001", "evidence_id": "EVID-PLAN", "revision": "fixture-v2", "freshness": "fresh"}],
    |                                                                                                   ^^^^^^^^^^^^^^^^^^^^^^
131 | …     "deltas": [{"id": "DELTA-001", "target_id": "TARGET-001", "expected_state": "result exists", "observed_state": "result absent",…
132 | …     "next_blocking_action": "Execute TASK-001",
    |

E501 Line too long (255 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:131:101
    |
129 | …"stale_result": "BLOCKED"},
130 | …2", "freshness": "fresh"}],
131 | …sts", "observed_state": "result absent", "classification": "gap", "impact": "task required", "required_action": "execute task", "evidence_ids": ["EVID-PLAN"]}],
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
132 | …
133 | …
    |

E501 Line too long (103 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:137:101
    |
135 |         "schema": "program-execution-blueprint.workstreams.v2", "schema_version": "2.0.0",
136 |         "workstreams": [{
137 |             "id": "WS-01", "name": "Implementation", "objective": "Create result", "owner": "operator",
    |                                                                                                     ^^^
138 |             "target_ids": ["TARGET-001"], "scope": {"include": ["docs/result.txt"], "exclude": ["remote"]},
139 |             "inputs": ["EVID-PLAN"], "outputs": ["docs/result.txt"], "entry_gate_ids": [], "exit_gate_ids": ["GATE-001"],
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:138:101
    |
136 |         "workstreams": [{
137 |             "id": "WS-01", "name": "Implementation", "objective": "Create result", "owner": "operator",
138 |             "target_ids": ["TARGET-001"], "scope": {"include": ["docs/result.txt"], "exclude": ["remote"]},
    |                                                                                                     ^^^^^^^
139 |             "inputs": ["EVID-PLAN"], "outputs": ["docs/result.txt"], "entry_gate_ids": [], "exit_gate_ids": ["GATE-001"],
140 |             "rollback_boundary": "delete result", "definition_status": "active",
    |

E501 Line too long (121 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:139:101
    |
137 |             "id": "WS-01", "name": "Implementation", "objective": "Create result", "owner": "operator",
138 |             "target_ids": ["TARGET-001"], "scope": {"include": ["docs/result.txt"], "exclude": ["remote"]},
139 |             "inputs": ["EVID-PLAN"], "outputs": ["docs/result.txt"], "entry_gate_ids": [], "exit_gate_ids": ["GATE-001"],
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^
140 |             "rollback_boundary": "delete result", "definition_status": "active",
141 |         }],
    |

E501 Line too long (103 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:148:101
    |
146 |         "schema": "program-execution-blueprint.dependency-graph.v2", "schema_version": "2.0.0",
147 |         "direction": "predecessor_to_successor",
148 |         "nodes": [{"id": task_id, "entity_type": "task", "owner": "operator"} for task_id in task_ids],
    |                                                                                                     ^^^
149 |         "edges": edges, "critical_path": ["TASK-001"], "parallelizable_groups": [task_ids] if two_tasks else [],
150 |         "hard_rule": "No bypass",
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:149:101
    |
147 |         "direction": "predecessor_to_successor",
148 |         "nodes": [{"id": task_id, "entity_type": "task", "owner": "operator"} for task_id in task_ids],
149 |         "edges": edges, "critical_path": ["TASK-001"], "parallelizable_groups": [task_ids] if two_tasks else [],
    |                                                                                                     ^^^^^^^^^^^^
150 |         "hard_rule": "No bypass",
151 |     })
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:156:101
    |
154 |         "promotion_rule": "Blocking gates pass",
155 |         "waves": [{
156 |             "id": "W0", "name": "local execution", "sequence": 0, "depends_on": [], "workstream_ids": ["WS-01"],
    |                                                                                                     ^^^^^^^^^^^^
157 |             "task_ids": task_ids, "entry_gate_ids": [], "exit_gate_ids": ["GATE-001"],
158 |             "rollback_boundary": "delete result", "definition_status": "active",
    |

E501 Line too long (198 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:161:101
    |
159 | …
160 | …
161 | …sh", "pull_request", "merge", "publish_or_release", "deploy_or_migrate", "destructive_change", "external_message"]}
    |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
162 | …
163 | …
    |

E501 Line too long (127 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:165:101
    |
163 |     def task(task_id: str, output: str) -> dict[str, Any]:
164 |         return {
165 |             "id": task_id, "title": f"Write {output}", "definition_status": "ready", "workstream_id": "WS-01", "wave_id": "W0",
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^
166 |             "target_id": "TARGET-001", "execution_kind": "repo_local", "objective": f"Write {output}",
167 |             "authority_basis_ids": ["AUTH-001"],
    |

E501 Line too long (102 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:166:101
    |
164 |         return {
165 |             "id": task_id, "title": f"Write {output}", "definition_status": "ready", "workstream_id": "WS-01", "wave_id": "W0",
166 |             "target_id": "TARGET-001", "execution_kind": "repo_local", "objective": f"Write {output}",
    |                                                                                                     ^^
167 |             "authority_basis_ids": ["AUTH-001"],
168 |             "required_decision_ids": ["DEC-001"] if with_decision_unknown and task_id == "TASK-001" else [],
    |

E501 Line too long (108 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:168:101
    |
166 |             "target_id": "TARGET-001", "execution_kind": "repo_local", "objective": f"Write {output}",
167 |             "authority_basis_ids": ["AUTH-001"],
168 |             "required_decision_ids": ["DEC-001"] if with_decision_unknown and task_id == "TASK-001" else [],
    |                                                                                                     ^^^^^^^^
169 |             "blocking_unknown_ids": ["UNK-001"] if with_decision_unknown and task_id == "TASK-001" else [],
170 |             "input_evidence_ids": ["EVID-PLAN"], "actions": ["write_file"],
    |

E501 Line too long (107 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:169:101
    |
167 |             "authority_basis_ids": ["AUTH-001"],
168 |             "required_decision_ids": ["DEC-001"] if with_decision_unknown and task_id == "TASK-001" else [],
169 |             "blocking_unknown_ids": ["UNK-001"] if with_decision_unknown and task_id == "TASK-001" else [],
    |                                                                                                     ^^^^^^^
170 |             "input_evidence_ids": ["EVID-PLAN"], "actions": ["write_file"],
171 |             "outputs": [{"id": f"OUT-{task_id[-3:]}", "type": "artifact", "location": output, "required": True}],
    |

E501 Line too long (113 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:171:101
    |
169 | …     "blocking_unknown_ids": ["UNK-001"] if with_decision_unknown and task_id == "TASK-001" else [],
170 | …     "input_evidence_ids": ["EVID-PLAN"], "actions": ["write_file"],
171 | …     "outputs": [{"id": f"OUT-{task_id[-3:]}", "type": "artifact", "location": output, "required": True}],
    |                                                                                               ^^^^^^^^^^^^^
172 | …     "acceptance": [{"id": f"AC-{task_id[-3:]}", "statement": f"{output} contains ok", "required_evidence_types": ["test_result"]}],
173 | …     "validation": [{"id": f"VAL-{task_id[-3:]}", "method": "command", "command_or_inspection": f"python3 -c \"from pathlib import P…
    |

E501 Line too long (139 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:172:101
    |
170 | …ons": ["write_file"],
171 | …"type": "artifact", "location": output, "required": True}],
172 | …, "statement": f"{output} contains ok", "required_evidence_types": ["test_result"]}],
    |                                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
173 | …", "method": "command", "command_or_inspection": f"python3 -c \"from pathlib import Path; assert Path('{output}').read_text() == 'ok…
174 | …
    |

E501 Line too long (247 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:173:101
    |
171 | …required": True}],
172 | …required_evidence_types": ["test_result"]}],
173 | …ction": f"python3 -c \"from pathlib import Path; assert Path('{output}').read_text() == 'ok\\n'\"", "environment": "local", "expected_result": "PASS"}],
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
174 | …
175 | …dation": "file absent"},
    |

E501 Line too long (119 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:175:101
    |
173 | …     "validation": [{"id": f"VAL-{task_id[-3:]}", "method": "command", "command_or_inspection": f"python3 -c \"from pathlib import P…
174 | …     "negative_cases": ["wrong content"],
175 | …     "rollback": {"strategy": f"delete {output}", "trigger": "validation_failure", "validation": "file absent"},
    |                                                                                               ^^^^^^^^^^^^^^^^^^^
176 | …     "risk": {"tier": risk_tier if task_id == "TASK-001" else "T2", "reversibility": "reversible", "blast_radius": "single_target"},
177 | …     "authorization_ceiling": dict(ceiling), "completion_gate_ids": ["GATE-001"],
    |

E501 Line too long (139 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:176:101
    |
174 | …
175 | …", "trigger": "validation_failure", "validation": "file absent"},
176 | …TASK-001" else "T2", "reversibility": "reversible", "blast_radius": "single_target"},
    |                                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
177 | …ompletion_gate_ids": ["GATE-001"],
178 | …
    |

E501 Line too long (140 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:182:101
    |
180 | …
181 | …"))
182 | …rogram-execution-blueprint.task-cards.v2", "schema_version": "2.0.0", "tasks": tasks})
    |                                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
183 | …
184 | …ence-gates.v2", "schema_version": "2.0.0",
    |

E501 Line too long (126 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:185:101
    |
183 |     write_yaml(root / "CONVERGENCE_GATES.yaml", {
184 |         "schema": "program-execution-blueprint.convergence-gates.v2", "schema_version": "2.0.0",
185 |         "result_values": ["PASS", "FAIL", "BLOCKED", "UNKNOWN", "NOT_APPLICABLE_WITH_REASON"], "unknown_is_non_passing": True,
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
186 |         "gates": [{
187 |             "id": "GATE-001", "name": "local verification", "definition_status": "active", "owner": "operator", "class": "execution",
    |

E501 Line too long (133 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:187:101
    |
185 | …, "UNKNOWN", "NOT_APPLICABLE_WITH_REASON"], "unknown_is_non_passing": True,
186 | …
187 | …cation", "definition_status": "active", "owner": "operator", "class": "execution",
    |                                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
188 | …": task_ids}, "method": {"type": "command_and_inspection", "steps": ["verify result"]},
189 | …ion passes", "fail_condition": "Verification fails", "blocking": True,
    |

E501 Line too long (138 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:188:101
    |
186 | …
187 | …tion", "definition_status": "active", "owner": "operator", "class": "execution",
188 | … task_ids}, "method": {"type": "command_and_inspection", "steps": ["verify result"]},
    |                                                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
189 | …n passes", "fail_condition": "Verification fails", "blocking": True,
190 | …wed": False,
    |

E501 Line too long (121 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:189:101
    |
187 | …         "id": "GATE-001", "name": "local verification", "definition_status": "active", "owner": "operator", "class": "execution",
188 | …         "scope": {"wave_ids": ["W0"], "task_ids": task_ids}, "method": {"type": "command_and_inspection", "steps": ["verify result"…
189 | …         "pass_condition": "Controller verification passes", "fail_condition": "Verification fails", "blocking": True,
    |                                                                                                   ^^^^^^^^^^^^^^^^^^^^^
190 | …         "required_evidence_ids": [], "waiver_allowed": False,
191 | …     }],
    |

E501 Line too long (179 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:193:101
    |
191 | …
192 | …
193 | …tion-blueprint.observability-plan.v2", "schema_version": "2.0.0", "signals": [], "incident_routing": []})
    |                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
194 | …cution-blueprint.cutover-and-rollback.v2", "schema_version": "2.0.0", "cutover": {"required_gate_ids": ["GATE-001"], "approval_actio…
195 | …ution-blueprint.source-traceability.v2", "schema_version": "2.0.0", "authority_classes": ["governing", "supporting", "contradicting"…
    |

E501 Line too long (514 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:194:101
    |
192 | …
193 | …ability-plan.v2", "schema_version": "2.0.0", "signals": [], "incident_routing": []})
194 | …ver-and-rollback.v2", "schema_version": "2.0.0", "cutover": {"required_gate_ids": ["GATE-001"], "approval_action": "deploy_or_migrate", "steps": ["not applicable locally"], "abort_conditions": ["gate failure"], "observation_window": "immediate"}, "rollback": {"trigger_conditions": ["gate failure"], "steps": ["delete result"], "data_reconciliation": "none", "validation": ["working tree clean"], "owner": "operator"}})
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
195 | …e-traceability.v2", "schema_version": "2.0.0", "authority_classes": ["governing", "supporting", "contradicting", "example", "historical", "inferred"], "sources": [{"id": "SRC-001", "source": "fixture", "revision": "v2", "authority_class": "governing", "evidence_id": "EVID-PLAN", "claims": ["test"], "target_ids": ["TARGET-001"], "workstream_ids": ["WS-01"], "task_ids": task_ids, "gate_ids": ["GATE-001"], "status": "active…
196 | …
    |

E501 Line too long (524 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:195:101
    |
193 | …ability-plan.v2", "schema_version": "2.0.0", "signals": [], "incident_routing": []})
194 | …ver-and-rollback.v2", "schema_version": "2.0.0", "cutover": {"required_gate_ids": ["GATE-001"], "approval_action": "deploy_or_migrate", "steps": ["not applicable locally"], "abort_conditions": ["gate failure"], "observation_window": "immediate"}, "rollback": {"trigger_conditions": ["gate failure"], "steps": ["delete result"], "data_reconciliation": "none", "validation": ["working tree clean"], "owner": "operator"}})
195 | …e-traceability.v2", "schema_version": "2.0.0", "authority_classes": ["governing", "supporting", "contradicting", "example", "historical", "inferred"], "sources": [{"id": "SRC-001", "source": "fixture", "revision": "v2", "authority_class": "governing", "evidence_id": "EVID-PLAN", "claims": ["test"], "target_ids": ["TARGET-001"], "workstream_ids": ["WS-01"], "task_ids": task_ids, "gate_ids": ["GATE-001"], "status": "active"}]})
    |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
196 | …
    |

E501 Line too long (104 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:202:101
    |
200 |     root.mkdir(parents=True, exist_ok=True)
201 |     subprocess.run(["git", "-C", str(root), "init", "-b", "main"], check=True, capture_output=True)
202 |     subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
    |                                                                                                     ^^^^
203 |     subprocess.run(["git", "-C", str(root), "config", "user.name", "Controller Test"], check=True)
204 |     (root / "README.md").write_text("# test\n", encoding="utf-8")
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:206:101
    |
204 |     (root / "README.md").write_text("# test\n", encoding="utf-8")
205 |     subprocess.run(["git", "-C", str(root), "add", "README.md"], check=True)
206 |     subprocess.run(["git", "-C", str(root), "commit", "-m", "init"], check=True, capture_output=True)
    |                                                                                                     ^
207 |     return root
    |

E501 Line too long (158 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:210:101
    |
210 | …ocs/result.txt", *, actions: list[str] | None = None, risk_tier: str = "T2") -> dict[str, Any]:
    |                                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
211 | …
212 | ….v2", "task_id": task_id,
    |

E501 Line too long (124 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:216:101
    |
214 |         "requested_actions": actions or ["inspect", "local_write"],
215 |         "acceptance_obligation_ids": [f"AC-{task_id[-3:]}"], "writable_paths": [output],
216 |         "validation_commands": [f"python3 -c \"from pathlib import Path; assert Path('{output}').read_text() == 'ok\\n'\""],
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^
217 |         "required_gate_ids": ["GATE-001"], "required_evidence_ids": ["EVID-PLAN"],
218 |         "risk_tier": risk_tier, "remote_mutation": "denied",
    |

E501 Line too long (179 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:238:101
    |
238 | …-001", output: str = "docs/result.txt", actions: list[str] | None = None, risk_tier: str = "T2") -> Path:
    |                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
239 | …k_id, output, actions=actions, risk_tier=risk_tier))
240 | …--file", str(path), "--actor", "operator")
    |

E501 Line too long (126 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:239:101
    |
238 | def register_contract(temp: Path, workspace: Path, *, task_id: str = "TASK-001", output: str = "docs/result.txt", actions: list[str] …
239 |     path = write_json(temp / f"{task_id}.source.json", source_contract(task_id, output, actions=actions, risk_tier=risk_tier))
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
240 |     run_cli("register-contract", task_id, "--workspace", str(workspace), "--file", str(path), "--actor", "operator")
241 |     return path
    |

E501 Line too long (116 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:240:101
    |
238 | def register_contract(temp: Path, workspace: Path, *, task_id: str = "TASK-001", output: str = "docs/result.txt", actions: list[str] …
239 |     path = write_json(temp / f"{task_id}.source.json", source_contract(task_id, output, actions=actions, risk_tier=risk_tier))
240 |     run_cli("register-contract", task_id, "--workspace", str(workspace), "--file", str(path), "--actor", "operator")
    |                                                                                                     ^^^^^^^^^^^^^^^^
241 |     return path
    |

E501 Line too long (196 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:244:101
    |
244 | …put: str = "docs/result.txt", declared_changed: list[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
245 | …
246 | …
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:256:101
    |
254 |     receipt = {
255 |         "schema": "program-execution-controller.attempt-receipt.v2", "task_id": task_id,
256 |         "contract_digest": contract["contract_digest"], "program_digest": contract["program_digest"],
    |                                                                                                     ^
257 |         "base_sha": contract["base_sha"], "candidate_sha": None,
258 |         "changed_files": declared_changed if declared_changed is not None else [output],
    |

E501 Line too long (163 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:259:101
    |
257 | …
258 | …ot None else [output],
259 | …S", "exit_code": 0, "evidence": "worker output"} for command in contract["validation_commands"]],
    |                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
260 | …_status": "completed",
261 | …
    |

E501 Line too long (101 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:263:101
    |
261 |     }
262 |     receipt_path = write_json(temp / f"{task_id}.attempt.json", receipt)
263 |     run_cli("record-attempt", task_id, "--workspace", str(workspace), "--receipt", str(receipt_path))
    |                                                                                                     ^
264 |     return contract, prepared
    |

E501 Line too long (142 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:270:101
    |
268 | …
269 | …
270 | …ee", "remove", "--force", str(worktree)], check=False, capture_output=True, timeout=15)
    |                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
271 | … "prune"], check=False, capture_output=True, timeout=15)
    |

E501 Line too long (111 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/tests/helpers.py:271:101
    |
269 |     if worktree.exists():
270 |         subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)], check=False, capture_output=True, ti…
271 |     subprocess.run(["git", "-C", str(repo), "worktree", "prune"], check=False, capture_output=True, timeout=15)
    |                                                                                                     ^^^^^^^^^^^
    |

E501 Line too long (113 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_approval.py:19:101
   |
17 |             _, _, workspace = bootstrap_repo(temp, risk_tier="T4")
18 |             register_contract(temp, workspace, risk_tier="T4")
19 |             blocked = run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker", expect=2)
   |                                                                                                     ^^^^^^^^^^^^^
20 |             self.assertIn("required_approval_missing_or_invalid", blocked["error"])
21 |             lock = json.loads((workspace / "runtime" / "program-lock.json").read_text())
   |

E501 Line too long (113 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_approval.py:23:101
   |
21 |             lock = json.loads((workspace / "runtime" / "program-lock.json").read_text())
22 |             db = sqlite3.connect(workspace / "runtime" / "state.sqlite")
23 |             base_sha = db.execute("SELECT head_sha FROM repositories WHERE repository_id='repo-a'").fetchone()[0]
   |                                                                                                     ^^^^^^^^^^^^^
24 |             db.close()
25 |             now = dt.datetime.now(dt.UTC).replace(microsecond=0)
   |

E501 Line too long (126 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_approval.py:27:101
   |
25 |             now = dt.datetime.now(dt.UTC).replace(microsecond=0)
26 |             approval = {
27 |                 "schema": "program-execution-controller.approval.v2", "approval_id": "APPROVAL-001", "action": "execute_task",
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
28 |                 "task_id": "TASK-001", "target_id": "TARGET-001", "repository_id": "repo-a",
29 |                 "program_digest": lock["lock_digest"], "base_sha": base_sha, "candidate_sha": None,
   |

E501 Line too long (105 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_approval.py:30:101
   |
28 |                 "task_id": "TASK-001", "target_id": "TARGET-001", "repository_id": "repo-a",
29 |                 "program_digest": lock["lock_digest"], "base_sha": base_sha, "candidate_sha": None,
30 |                 "permits": ["inspect", "local_write"], "forbids": ["push", "merge", "deploy_or_migrate"],
   |                                                                                                     ^^^^^
31 |                 "prerequisite_evidence_ids": ["EVID-PLAN"], "approved_by": "operator",
32 |                 "issued_at": now.isoformat(), "expires_at": (now + dt.timedelta(hours=1)).isoformat(),
   |

E501 Line too long (102 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_approval.py:32:101
   |
30 |                 "permits": ["inspect", "local_write"], "forbids": ["push", "merge", "deploy_or_migrate"],
31 |                 "prerequisite_evidence_ids": ["EVID-PLAN"], "approved_by": "operator",
32 |                 "issued_at": now.isoformat(), "expires_at": (now + dt.timedelta(hours=1)).isoformat(),
   |                                                                                                     ^^
33 |             }
34 |             path = write_json(temp / "approval.json", approval)
   |

E501 Line too long (101 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_approval.py:36:101
   |
34 |             path = write_json(temp / "approval.json", approval)
35 |             run_cli("add-approval", "--workspace", str(workspace), "--file", str(path))
36 |             lease = run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker")
   |                                                                                                     ^
37 |             self.assertEqual(lease["task_id"], "TASK-001")
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_approval.py:39:26
   |
37 |             self.assertEqual(lease["task_id"], "TASK-001")
38 |
39 | if __name__ == "__main__": unittest.main()
   |                          ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_authority_inflation.py:13:27
   |
11 |     def test_source_contract_cannot_widen_blueprint_authority(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw); _,_,workspace=bootstrap_repo(temp)
   |                           ^
14 |             path=write_json(temp/'inflated.json', source_contract(actions=['inspect','local_write','push']))
15 |             result=run_cli('register-contract','TASK-001','--workspace',str(workspace),'--file',str(path),'--actor','operator',expect=…
   |

E501 Line too long (108 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_authority_inflation.py:14:101
   |
12 | …     with TemporaryDirectory() as raw:
13 | …         temp=Path(raw); _,_,workspace=bootstrap_repo(temp)
14 | …         path=write_json(temp/'inflated.json', source_contract(actions=['inspect','local_write','push']))
   |                                                                                                   ^^^^^^^^
15 | …         result=run_cli('register-contract','TASK-001','--workspace',str(workspace),'--file',str(path),'--actor','operator',expect=2)
16 | …         self.assertIn('widens Blueprint authorization ceiling', result['error'])
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_authority_inflation.py:17:24
   |
15 |             result=run_cli('register-contract','TASK-001','--workspace',str(workspace),'--file',str(path),'--actor','operator',expect=…
16 |             self.assertIn('widens Blueprint authorization ceiling', result['error'])
17 | if __name__=='__main__': unittest.main()
   |                        ^
   |

E501 Line too long (126 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_changed_files.py:20:101
   |
18 |             self.assertEqual(verification["verdict"], "FAILED")
19 |             self.assertEqual(verification["gates"]["changed_files_exact"], "FAIL")
20 |             run_cli("release-lease", "TASK-001", "--workspace", str(workspace), "--reason", "test cleanup", "--actor", "test")
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
21 |             cleanup_worktree(repo, workspace)
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_changed_files.py:23:26
   |
21 |             cleanup_worktree(repo, workspace)
22 |
23 | if __name__ == "__main__": unittest.main()
   |                          ^
   |

E501 Line too long (182 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_controller_success.py:20:101
   |
18 | …
19 | …
20 | …(workspace), "--evidence-id", evidence_id, "--method", "independent verification", "--actor", "controller")
   |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 | …"--actor", "operator", "--evidence-id", evidence_id)
22 | …
   |

E501 Line too long (127 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_controller_success.py:21:101
   |
19 | …     evidence_id = verification["evidence_id"]
20 | …     run_cli("evaluate-gate", "GATE-001", "PASS", "--workspace", str(workspace), "--evidence-id", evidence_id, "--method", "independe…
21 | …     run_cli("complete", "TASK-001", "--workspace", str(workspace), "--actor", "operator", "--evidence-id", evidence_id)
   |                                                                                               ^^^^^^^^^^^^^^^^^^^^^^^^^^^
22 | …     output = temp / "handoff.json"
23 | …     receipt = run_cli("export-handoff", "--workspace", str(workspace), "--actor", "operator", "--output", str(output))
   |

E501 Line too long (126 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_controller_success.py:23:101
   |
21 |             run_cli("complete", "TASK-001", "--workspace", str(workspace), "--actor", "operator", "--evidence-id", evidence_id)
22 |             output = temp / "handoff.json"
23 |             receipt = run_cli("export-handoff", "--workspace", str(workspace), "--actor", "operator", "--output", str(output))
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
24 |             self.assertEqual(receipt["recommended_program_verdict"], "CONVERGED")
25 |             self.assertEqual(run_cli("validate", "--workspace", str(workspace))["status"], "PASS")
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_controller_success.py:28:26
   |
26 |             cleanup_worktree(repo, workspace)
27 |
28 | if __name__ == "__main__": unittest.main()
   |                          ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_decision_unknown.py:14:27
   |
12 |     def test_blockers_require_evidence_bound_resolution(self):
13 |         with TemporaryDirectory() as raw:
14 |             temp=Path(raw); _,_,workspace=bootstrap_repo(temp,with_decision_unknown=True); register_contract(temp,workspace)
   |                           ^
15 |             joined=json.dumps(run_cli('next','--workspace',str(workspace)))
16 |             self.assertIn('required_decision_not_accepted:DEC-001',joined); self.assertIn('blocking_unknown:UNK-001',joined)
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_decision_unknown.py:14:90
   |
12 |     def test_blockers_require_evidence_bound_resolution(self):
13 |         with TemporaryDirectory() as raw:
14 |             temp=Path(raw); _,_,workspace=bootstrap_repo(temp,with_decision_unknown=True); register_contract(temp,workspace)
   |                                                                                          ^
15 |             joined=json.dumps(run_cli('next','--workspace',str(workspace)))
16 |             self.assertIn('required_decision_not_accepted:DEC-001',joined); self.assertIn('blocking_unknown:UNK-001',joined)
   |

E501 Line too long (124 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_decision_unknown.py:14:101
   |
12 |     def test_blockers_require_evidence_bound_resolution(self):
13 |         with TemporaryDirectory() as raw:
14 |             temp=Path(raw); _,_,workspace=bootstrap_repo(temp,with_decision_unknown=True); register_contract(temp,workspace)
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^
15 |             joined=json.dumps(run_cli('next','--workspace',str(workspace)))
16 |             self.assertIn('required_decision_not_accepted:DEC-001',joined); self.assertIn('blocking_unknown:UNK-001',joined)
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_decision_unknown.py:16:75
   |
14 |             temp=Path(raw); _,_,workspace=bootstrap_repo(temp,with_decision_unknown=True); register_contract(temp,workspace)
15 |             joined=json.dumps(run_cli('next','--workspace',str(workspace)))
16 |             self.assertIn('required_decision_not_accepted:DEC-001',joined); self.assertIn('blocking_unknown:UNK-001',joined)
   |                                                                           ^
17 |             run_cli('set-decision','DEC-001','accepted','--workspace',str(workspace),'--evidence-id','EVID-PLAN','--actor','operator')
18 |             run_cli('set-unknown','UNK-001','resolved','--workspace',str(workspace),'--evidence-id','EVID-PLAN','--actor','operator')
   |

E501 Line too long (124 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_decision_unknown.py:16:101
   |
14 |             temp=Path(raw); _,_,workspace=bootstrap_repo(temp,with_decision_unknown=True); register_contract(temp,workspace)
15 |             joined=json.dumps(run_cli('next','--workspace',str(workspace)))
16 |             self.assertIn('required_decision_not_accepted:DEC-001',joined); self.assertIn('blocking_unknown:UNK-001',joined)
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^
17 |             run_cli('set-decision','DEC-001','accepted','--workspace',str(workspace),'--evidence-id','EVID-PLAN','--actor','operator')
18 |             run_cli('set-unknown','UNK-001','resolved','--workspace',str(workspace),'--evidence-id','EVID-PLAN','--actor','operator')
   |

E501 Line too long (115 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_decision_unknown.py:19:101
   |
17 |             run_cli('set-decision','DEC-001','accepted','--workspace',str(workspace),'--evidence-id','EVID-PLAN','--actor','operator')
18 |             run_cli('set-unknown','UNK-001','resolved','--workspace',str(workspace),'--evidence-id','EVID-PLAN','--actor','operator')
19 |             self.assertEqual([x['id'] for x in run_cli('next','--workspace',str(workspace))['ready']],['TASK-001'])
   |                                                                                                     ^^^^^^^^^^^^^^^
20 | if __name__=='__main__': unittest.main()
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_decision_unknown.py:20:24
   |
18 |             run_cli('set-unknown','UNK-001','resolved','--workspace',str(workspace),'--evidence-id','EVID-PLAN','--actor','operator')
19 |             self.assertEqual([x['id'] for x in run_cli('next','--workspace',str(workspace))['ready']],['TASK-001'])
20 | if __name__=='__main__': unittest.main()
   |                        ^
   |

E501 Line too long (114 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_leases_and_approval.py:18:101
   |
16 |             register_contract(temp, workspace, task_id="TASK-002", output="docs/second.txt")
17 |             run_cli("claim", "TASK-001", "--workspace", str(workspace), "--holder", "worker-1")
18 |             result = run_cli("claim", "TASK-002", "--workspace", str(workspace), "--holder", "worker-2", expect=2)
   |                                                                                                     ^^^^^^^^^^^^^^
19 |             self.assertIn("active writer lease", result["error"])
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_ledger_tamper.py:13:27
   |
11 |     def test_ledger_tamper_detected(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp); ledger=workspace/'ledger/events.jsonl'; ledger.write_text(ledger.read_t…
   |                           ^
14 |             result=run_cli('validate','--workspace',str(workspace),expect=1)
15 |             self.assertEqual(result['status'],'FAIL'); self.assertTrue(result['errors'])
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_ledger_tamper.py:13:62
   |
11 |     def test_ledger_tamper_detected(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp); ledger=workspace/'ledger/events.jsonl'; ledger.write_text(ledger.read_t…
   |                                                              ^
14 |             result=run_cli('validate','--workspace',str(workspace),expect=1)
15 |             self.assertEqual(result['status'],'FAIL'); self.assertTrue(result['errors'])
   |

E501 Line too long (162 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_ledger_tamper.py:13:101
   |
11 | …
12 | …
13 | …dger=workspace/'ledger/events.jsonl'; ledger.write_text(ledger.read_text()+'{"tampered":true}\n')
   |                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
14 | …),expect=1)
15 | …tTrue(result['errors'])
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_ledger_tamper.py:13:102
   |
11 |     def test_ledger_tamper_detected(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp); ledger=workspace/'ledger/events.jsonl'; ledger.write_text(ledger.read_t…
   |                                                                                                      ^
14 |             result=run_cli('validate','--workspace',str(workspace),expect=1)
15 |             self.assertEqual(result['status'],'FAIL'); self.assertTrue(result['errors'])
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_ledger_tamper.py:15:54
   |
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp); ledger=workspace/'ledger/events.jsonl'; ledger.write_text(ledger.read_t…
14 |             result=run_cli('validate','--workspace',str(workspace),expect=1)
15 |             self.assertEqual(result['status'],'FAIL'); self.assertTrue(result['errors'])
   |                                                      ^
16 | if __name__=='__main__': unittest.main()
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_ledger_tamper.py:16:24
   |
14 |             result=run_cli('validate','--workspace',str(workspace),expect=1)
15 |             self.assertEqual(result['status'],'FAIL'); self.assertTrue(result['errors'])
16 | if __name__=='__main__': unittest.main()
   |                        ^
   |

E501 Line too long (105 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_control.py:10:101
   |
 8 | class ProgramControlTests(unittest.TestCase):
 9 |     def test_program_control_can_complete_only_after_gate_passes(self) -> None:
10 |         # The universal fixture uses repo-local tasks; this test exercises the legal state edge directly.
   |                                                                                                     ^^^^^
11 |         import sys
   |

E501 Line too long (123 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_control.py:20:101
   |
18 |             try:
19 |                 db.upsert_task({
20 |                     "id": "TASK-PC", "title": "lock", "wave_id": "W0", "workstream_id": "WS-01", "target_id": "TARGET-001",
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^
21 |                     "repository_id": None, "execution_kind": "program_control", "objective": "lock", "dependencies": [],
22 |                     "required_decisions": [], "blocking_unknowns": [], "required_evidence": [], "completion_gates": [],
   |

E501 Line too long (120 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_control.py:21:101
   |
19 |                 db.upsert_task({
20 |                     "id": "TASK-PC", "title": "lock", "wave_id": "W0", "workstream_id": "WS-01", "target_id": "TARGET-001",
21 |                     "repository_id": None, "execution_kind": "program_control", "objective": "lock", "dependencies": [],
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^
22 |                     "required_decisions": [], "blocking_unknowns": [], "required_evidence": [], "completion_gates": [],
23 |                     "authorization_ceiling": {"inspect": True}, "required_acceptance": [], "required_validation_commands": [],
   |

E501 Line too long (119 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_control.py:22:101
   |
20 |                     "id": "TASK-PC", "title": "lock", "wave_id": "W0", "workstream_id": "WS-01", "target_id": "TARGET-001",
21 |                     "repository_id": None, "execution_kind": "program_control", "objective": "lock", "dependencies": [],
22 |                     "required_decisions": [], "blocking_unknowns": [], "required_evidence": [], "completion_gates": [],
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^
23 |                     "authorization_ceiling": {"inspect": True}, "required_acceptance": [], "required_validation_commands": [],
24 |                     "risk_tier": "T0", "definition_status": "ready", "source": {},
   |

E501 Line too long (126 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_control.py:23:101
   |
21 |                     "repository_id": None, "execution_kind": "program_control", "objective": "lock", "dependencies": [],
22 |                     "required_decisions": [], "blocking_unknowns": [], "required_evidence": [], "completion_gates": [],
23 |                     "authorization_ceiling": {"inspect": True}, "required_acceptance": [], "required_validation_commands": [],
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^
24 |                     "risk_tier": "T0", "definition_status": "ready", "source": {},
25 |                 })
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_lock_drift.py:13:27
   |
11 |     def test_claim_rejects_blueprint_source_drift_without_manual_validation(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);blueprint,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace)
   |                           ^
14 |             with (blueprint/'PROGRAM.yaml').open('a',encoding='utf-8') as h:h.write('# source drift\n')
15 |             result=run_cli('claim','TASK-001','--workspace',str(workspace),'--holder','worker',expect=2)
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_lock_drift.py:13:70
   |
11 |     def test_claim_rejects_blueprint_source_drift_without_manual_validation(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);blueprint,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace)
   |                                                                      ^
14 |             with (blueprint/'PROGRAM.yaml').open('a',encoding='utf-8') as h:h.write('# source drift\n')
15 |             result=run_cli('claim','TASK-001','--workspace',str(workspace),'--holder','worker',expect=2)
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_lock_drift.py:14:76
   |
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);blueprint,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace)
14 |             with (blueprint/'PROGRAM.yaml').open('a',encoding='utf-8') as h:h.write('# source drift\n')
   |                                                                            ^
15 |             result=run_cli('claim','TASK-001','--workspace',str(workspace),'--holder','worker',expect=2)
16 |             self.assertIn('program_lock_stale_or_invalid',result['error'])
   |

E501 Line too long (103 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_lock_drift.py:14:101
   |
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);blueprint,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace)
14 |             with (blueprint/'PROGRAM.yaml').open('a',encoding='utf-8') as h:h.write('# source drift\n')
   |                                                                                                     ^^^
15 |             result=run_cli('claim','TASK-001','--workspace',str(workspace),'--holder','worker',expect=2)
16 |             self.assertIn('program_lock_stale_or_invalid',result['error'])
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_program_lock_drift.py:17:24
   |
15 |             result=run_cli('claim','TASK-001','--workspace',str(workspace),'--holder','worker',expect=2)
16 |             self.assertIn('program_lock_stale_or_invalid',result['error'])
17 | if __name__=='__main__':unittest.main()
   |                        ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_recovery.py:13:27
   |
11 |     def test_expired_lease_recovered_with_evidence(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace);run_cli('claim','TASK-001','--workspac…
   |                           ^
14 |             result=run_cli('recover','--workspace',str(workspace),'--actor','operator')
15 |             self.assertEqual(result['status'],'RECOVERED'); self.assertEqual(len(result['items']),1); self.assertTrue(any((workspace/'…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_recovery.py:13:62
   |
11 |     def test_expired_lease_recovered_with_evidence(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace);run_cli('claim','TASK-001','--workspac…
   |                                                              ^
14 |             result=run_cli('recover','--workspace',str(workspace),'--actor','operator')
15 |             self.assertEqual(result['status'],'RECOVERED'); self.assertEqual(len(result['items']),1); self.assertTrue(any((workspace/'…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_recovery.py:13:96
   |
11 |     def test_expired_lease_recovered_with_evidence(self):
12 |         with TemporaryDirectory() as raw:
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace);run_cli('claim','TASK-001','--workspac…
   |                                                                                                ^
14 |             result=run_cli('recover','--workspace',str(workspace),'--actor','operator')
15 |             self.assertEqual(result['status'],'RECOVERED'); self.assertEqual(len(result['items']),1); self.assertTrue(any((workspace/'…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_recovery.py:15:59
   |
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace);run_cli('claim','TASK-001','--workspac…
14 |             result=run_cli('recover','--workspace',str(workspace),'--actor','operator')
15 |             self.assertEqual(result['status'],'RECOVERED'); self.assertEqual(len(result['items']),1); self.assertTrue(any((workspace/'…
   |                                                           ^
16 | if __name__=='__main__': unittest.main()
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_recovery.py:15:101
   |
13 |             temp=Path(raw);_,_,workspace=bootstrap_repo(temp);register_contract(temp,workspace);run_cli('claim','TASK-001','--workspac…
14 |             result=run_cli('recover','--workspace',str(workspace),'--actor','operator')
15 |             self.assertEqual(result['status'],'RECOVERED'); self.assertEqual(len(result['items']),1); self.assertTrue(any((workspace/'…
   |                                                                                                     ^
16 | if __name__=='__main__': unittest.main()
   |

E501 Line too long (169 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_recovery.py:15:101
   |
13 | …er_contract(temp,workspace);run_cli('claim','TASK-001','--workspace',str(workspace),'--holder','worker','--ttl-hours','0')
14 | …-actor','operator')
15 | …ertEqual(len(result['items']),1); self.assertTrue(any((workspace/'recovery').rglob('metadata.json')))
   |                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
16 | …
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_recovery.py:16:24
   |
14 |             result=run_cli('recover','--workspace',str(workspace),'--actor','operator')
15 |             self.assertEqual(result['status'],'RECOVERED'); self.assertEqual(len(result['items']),1); self.assertTrue(any((workspace/'…
16 | if __name__=='__main__': unittest.main()
   |                        ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_scope.py:14:67
   |
12 | class ScopeTest(unittest.TestCase):
13 |     def test_scope_fail_closed(self):
14 |         self.assertTrue(path_allowed('docs/result.txt',['docs/']));self.assertFalse(path_allowed('src/result.txt',['docs/']))
   |                                                                   ^
15 |         with self.assertRaises(ContractError): normalize_repo_path('../escape.txt')
16 | if __name__=='__main__': unittest.main()
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_scope.py:15:46
   |
13 |     def test_scope_fail_closed(self):
14 |         self.assertTrue(path_allowed('docs/result.txt',['docs/']));self.assertFalse(path_allowed('src/result.txt',['docs/']))
15 |         with self.assertRaises(ContractError): normalize_repo_path('../escape.txt')
   |                                              ^
16 | if __name__=='__main__': unittest.main()
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_scope.py:16:24
   |
14 |         self.assertTrue(path_allowed('docs/result.txt',['docs/']));self.assertFalse(path_allowed('src/result.txt',['docs/']))
15 |         with self.assertRaises(ContractError): normalize_repo_path('../escape.txt')
16 | if __name__=='__main__': unittest.main()
   |                        ^
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_state_transition.py:20:51
   |
18 |             try:
19 |                 db.upsert_task({'id':'TASK-001','title':'x','wave_id':'W0','workstream_id':'WS','target_id':'T','repository_id':'repo-…
20 |                 with self.assertRaises(ValueError): db.transition_task('TASK-001','COMPLETED')
   |                                                   ^
21 |             finally: db.close()
22 | if __name__=='__main__': unittest.main()
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_state_transition.py:21:20
   |
19 |                 db.upsert_task({'id':'TASK-001','title':'x','wave_id':'W0','workstream_id':'WS','target_id':'T','repository_id':'repo-…
20 |                 with self.assertRaises(ValueError): db.transition_task('TASK-001','COMPLETED')
21 |             finally: db.close()
   |                    ^
22 | if __name__=='__main__': unittest.main()
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_state_transition.py:22:24
   |
20 |                 with self.assertRaises(ValueError): db.transition_task('TASK-001','COMPLETED')
21 |             finally: db.close()
22 | if __name__=='__main__': unittest.main()
   |                        ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:21:27
   |
19 |     def test_explicit_active_evidence_backed_waiver_satisfies_not_applicable_gate(self):
20 |         with TemporaryDirectory() as raw:
21 |             temp=Path(raw);bp=make_blueprint(temp/'blueprint')
   |                           ^
22 |             waivers=yaml.safe_load((bp/'WAIVER_REGISTER.yaml').read_text());waivers['waivers']=[{'id':'WAIVER-001','scope':['GATE-001'…
23 |             gates=yaml.safe_load((bp/'CONVERGENCE_GATES.yaml').read_text());gates['gates'][0]['waiver_allowed']=True;(bp/'CONVERGENCE_…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:22:76
   |
20 | …     with TemporaryDirectory() as raw:
21 | …         temp=Path(raw);bp=make_blueprint(temp/'blueprint')
22 | …         waivers=yaml.safe_load((bp/'WAIVER_REGISTER.yaml').read_text());waivers['waivers']=[{'id':'WAIVER-001','scope':['GATE-001'],…
   |                                                                          ^
23 | …         gates=yaml.safe_load((bp/'CONVERGENCE_GATES.yaml').read_text());gates['gates'][0]['waiver_allowed']=True;(bp/'CONVERGENCE_GA…
24 | …         repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp))…
   |

E501 Line too long (446 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:22:101
   |
20 | …
21 | …
22 | …[{'id':'WAIVER-001','scope':['GATE-001'],'owner':'operator','reason':'fixture exception','compensating_controls':['independent verification'],'evidence_ids':['EVID-PLAN'],'issued_at':'2026-08-01T13:00:00-04:00','expires_at':'2027-08-01T13:00:00-04:00','status':'active'}];(bp/'WAIVER_REGISTER.yaml').write_text(yaml.safe_dump(waivers,sort_keys=False))
   |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
23 | …waiver_allowed']=True;(bp/'CONVERGENCE_GATES.yaml').write_text(yaml.safe_dump(gates,sort_keys=False))
24 | …ce',str(workspace),'--blueprint',str(bp));run_cli('reconcile','--workspace',str(workspace),'--repository',f'repo-a={repo}');register_contract(temp,workspace);prepare_attempt(temp,workspace)
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:22:367
   |
20 | …
21 | …
22 | …4:00','expires_at':'2027-08-01T13:00:00-04:00','status':'active'}];(bp/'WAIVER_REGISTER.yaml').write_text(yaml.safe_dump(waivers,sort…
   |                                                                    ^
23 | …
24 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:23:76
   |
21 | …     temp=Path(raw);bp=make_blueprint(temp/'blueprint')
22 | …     waivers=yaml.safe_load((bp/'WAIVER_REGISTER.yaml').read_text());waivers['waivers']=[{'id':'WAIVER-001','scope':['GATE-001'],'own…
23 | …     gates=yaml.safe_load((bp/'CONVERGENCE_GATES.yaml').read_text());gates['gates'][0]['waiver_allowed']=True;(bp/'CONVERGENCE_GATES.…
   |                                                                      ^
24 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
25 | …     verification=run_cli('verify','TASK-001','--workspace',str(workspace));evidence=verification['evidence_id']
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:23:117
   |
21 | …     temp=Path(raw);bp=make_blueprint(temp/'blueprint')
22 | …     waivers=yaml.safe_load((bp/'WAIVER_REGISTER.yaml').read_text());waivers['waivers']=[{'id':'WAIVER-001','scope':['GATE-001'],'own…
23 | …     gates=yaml.safe_load((bp/'CONVERGENCE_GATES.yaml').read_text());gates['gates'][0]['waiver_allowed']=True;(bp/'CONVERGENCE_GATES.…
   |                                                                                                               ^
24 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
25 | …     verification=run_cli('verify','TASK-001','--workspace',str(workspace));evidence=verification['evidence_id']
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:24:40
   |
22 | …     waivers=yaml.safe_load((bp/'WAIVER_REGISTER.yaml').read_text());waivers['waivers']=[{'id':'WAIVER-001','scope':['GATE-001'],'own…
23 | …     gates=yaml.safe_load((bp/'CONVERGENCE_GATES.yaml').read_text());gates['gates'][0]['waiver_allowed']=True;(bp/'CONVERGENCE_GATES.…
24 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
   |                                  ^
25 | …     verification=run_cli('verify','TASK-001','--workspace',str(workspace));evidence=verification['evidence_id']
26 | …     run_cli('evaluate-gate','GATE-001','NOT_APPLICABLE_WITH_REASON','--workspace',str(workspace),'--evidence-id',evidence,'--method'…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:24:65
   |
22 | …     waivers=yaml.safe_load((bp/'WAIVER_REGISTER.yaml').read_text());waivers['waivers']=[{'id':'WAIVER-001','scope':['GATE-001'],'own…
23 | …     gates=yaml.safe_load((bp/'CONVERGENCE_GATES.yaml').read_text());gates['gates'][0]['waiver_allowed']=True;(bp/'CONVERGENCE_GATES.…
24 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
   |                                                           ^
25 | …     verification=run_cli('verify','TASK-001','--workspace',str(workspace));evidence=verification['evidence_id']
26 | …     run_cli('evaluate-gate','GATE-001','NOT_APPLICABLE_WITH_REASON','--workspace',str(workspace),'--evidence-id',evidence,'--method'…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:24:137
   |
22 | …xt());waivers['waivers']=[{'id':'WAIVER-001','scope':['GATE-001'],'owner':'operator','reason':'fixture exception','compensating_contr…
23 | …xt());gates['gates'][0]['waiver_allowed']=True;(bp/'CONVERGENCE_GATES.yaml').write_text(yaml.safe_dump(gates,sort_keys=False))
24 | …li('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run_cli('reconcile','--workspace',str(workspace),'--repository',f'…
   |                                                                    ^
25 | …(workspace));evidence=verification['evidence_id']
26 | …ASON','--workspace',str(workspace),'--evidence-id',evidence,'--method','explicit fixture waiver','--actor','controller','--waiver-id'…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:24:219
   |
22 | …r','reason':'fixture exception','compensating_controls':['independent verification'],'evidence_ids':['EVID-PLAN'],'issued_at':'2026-0…
23 | …_text(yaml.safe_dump(gates,sort_keys=False))
24 | …ile','--workspace',str(workspace),'--repository',f'repo-a={repo}');register_contract(temp,workspace);prepare_attempt(temp,workspace)
   |                                                                    ^
25 | …
26 | …ixture waiver','--actor','controller','--waiver-id','WAIVER-001')
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:24:253
   |
22 | …ompensating_controls':['independent verification'],'evidence_ids':['EVID-PLAN'],'issued_at':'2026-08-01T13:00:00-04:00','expires_at':…
23 | …ys=False))
24 | …'--repository',f'repo-a={repo}');register_contract(temp,workspace);prepare_attempt(temp,workspace)
   |                                                                    ^
25 | …
26 | …er','--waiver-id','WAIVER-001')
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:25:83
   |
23 | …     gates=yaml.safe_load((bp/'CONVERGENCE_GATES.yaml').read_text());gates['gates'][0]['waiver_allowed']=True;(bp/'CONVERGENCE_GATES.…
24 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
25 | …     verification=run_cli('verify','TASK-001','--workspace',str(workspace));evidence=verification['evidence_id']
   |                                                                             ^
26 | …     run_cli('evaluate-gate','GATE-001','NOT_APPLICABLE_WITH_REASON','--workspace',str(workspace),'--evidence-id',evidence,'--method'…
27 | …     result=run_cli('complete','TASK-001','--workspace',str(workspace),'--actor','operator','--evidence-id',evidence)
   |

E501 Line too long (217 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:26:101
   |
24 | …space',str(workspace),'--blueprint',str(bp));run_cli('reconcile','--workspace',str(workspace),'--repository',f'repo-a={repo}');regist…
25 | …verification['evidence_id']
26 | …r(workspace),'--evidence-id',evidence,'--method','explicit fixture waiver','--actor','controller','--waiver-id','WAIVER-001')
   |          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
27 | …rator','--evidence-id',evidence)
28 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:28:59
   |
26 |             run_cli('evaluate-gate','GATE-001','NOT_APPLICABLE_WITH_REASON','--workspace',str(workspace),'--evidence-id',evidence,'--m…
27 |             result=run_cli('complete','TASK-001','--workspace',str(workspace),'--actor','operator','--evidence-id',evidence)
28 |             self.assertEqual(result['status'],'COMPLETED');cleanup_worktree(repo,workspace)
   |                                                           ^
29 | if __name__=='__main__':unittest.main()
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_waived_gate.py:29:24
   |
27 |             result=run_cli('complete','TASK-001','--workspace',str(workspace),'--actor','operator','--evidence-id',evidence)
28 |             self.assertEqual(result['status'],'COMPLETED');cleanup_worktree(repo,workspace)
29 | if __name__=='__main__':unittest.main()
   |                        ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_wave_dependency.py:14:27
   |
12 |     def test_successor_wave_cannot_start_before_predecessor_completion_and_exit_gate(self):
13 |         with TemporaryDirectory() as raw:
14 |             temp=Path(raw);bp=make_blueprint(temp/'blueprint',two_tasks=True)
   |                           ^
15 |             waves=yaml.safe_load((bp/'EXECUTION_WAVES.yaml').read_text());waves['waves']=[
16 |                 {'id':'W0','name':'first','sequence':0,'depends_on':[],'workstream_ids':['WS-01'],'task_ids':['TASK-001'],'entry_gate_…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_wave_dependency.py:15:74
   |
13 | …     with TemporaryDirectory() as raw:
14 | …         temp=Path(raw);bp=make_blueprint(temp/'blueprint',two_tasks=True)
15 | …         waves=yaml.safe_load((bp/'EXECUTION_WAVES.yaml').read_text());waves['waves']=[
   |                                                                        ^
16 | …             {'id':'W0','name':'first','sequence':0,'depends_on':[],'workstream_ids':['WS-01'],'task_ids':['TASK-001'],'entry_gate_id…
17 | …             {'id':'W1','name':'second','sequence':1,'depends_on':['W0'],'workstream_ids':['WS-01'],'task_ids':['TASK-002'],'entry_ga…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_wave_dependency.py:19:69
   |
17 | …         {'id':'W1','name':'second','sequence':1,'depends_on':['W0'],'workstream_ids':['WS-01'],'task_ids':['TASK-002'],'entry_gate_i…
18 | …     (bp/'EXECUTION_WAVES.yaml').write_text(yaml.safe_dump(waves,sort_keys=False))
19 | …     tasks=yaml.safe_load((bp/'TASK_CARDS.yaml').read_text());tasks['tasks'][1]['wave_id']='W1';(bp/'TASK_CARDS.yaml').write_text(yam…
   |                                                               ^
20 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
21 | …     register_contract(temp,workspace,task_id='TASK-002',output='docs/second.txt')
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_wave_dependency.py:19:103
   |
17 | …         {'id':'W1','name':'second','sequence':1,'depends_on':['W0'],'workstream_ids':['WS-01'],'task_ids':['TASK-002'],'entry_gate_i…
18 | …     (bp/'EXECUTION_WAVES.yaml').write_text(yaml.safe_dump(waves,sort_keys=False))
19 | …     tasks=yaml.safe_load((bp/'TASK_CARDS.yaml').read_text());tasks['tasks'][1]['wave_id']='W1';(bp/'TASK_CARDS.yaml').write_text(yam…
   |                                                                                                 ^
20 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
21 | …     register_contract(temp,workspace,task_id='TASK-002',output='docs/second.txt')
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_wave_dependency.py:20:40
   |
18 | …     (bp/'EXECUTION_WAVES.yaml').write_text(yaml.safe_dump(waves,sort_keys=False))
19 | …     tasks=yaml.safe_load((bp/'TASK_CARDS.yaml').read_text());tasks['tasks'][1]['wave_id']='W1';(bp/'TASK_CARDS.yaml').write_text(yam…
20 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
   |                                  ^
21 | …     register_contract(temp,workspace,task_id='TASK-002',output='docs/second.txt')
22 | …     result=run_cli('claim','TASK-002','--workspace',str(workspace),'--holder','worker',expect=2)
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_wave_dependency.py:20:65
   |
18 | …     (bp/'EXECUTION_WAVES.yaml').write_text(yaml.safe_dump(waves,sort_keys=False))
19 | …     tasks=yaml.safe_load((bp/'TASK_CARDS.yaml').read_text());tasks['tasks'][1]['wave_id']='W1';(bp/'TASK_CARDS.yaml').write_text(yam…
20 | …     repo=make_repo(temp/'repo');workspace=temp/'runtime';run_cli('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run…
   |                                                           ^
21 | …     register_contract(temp,workspace,task_id='TASK-002',output='docs/second.txt')
22 | …     result=run_cli('claim','TASK-002','--workspace',str(workspace),'--holder','worker',expect=2)
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_wave_dependency.py:20:137
   |
18 | …s,sort_keys=False))
19 | …asks['tasks'][1]['wave_id']='W1';(bp/'TASK_CARDS.yaml').write_text(yaml.safe_dump(tasks,sort_keys=False))
20 | …li('bootstrap','--workspace',str(workspace),'--blueprint',str(bp));run_cli('reconcile','--workspace',str(workspace),'--repository',f'…
   |                                                                    ^
21 | …='docs/second.txt')
22 | …ace),'--holder','worker',expect=2)
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/program-execution-controller-template/scripts/tests/test_wave_dependency.py:25:24
   |
23 |             self.assertIn('predecessor_wave_task_not_completed:W0:TASK-001',result['error'])
24 |             self.assertIn('predecessor_wave_exit_gate_not_satisfied:W0:GATE-001',result['error'])
25 | if __name__=='__main__':unittest.main()
   |                        ^
   |

E501 Line too long (105 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:16:101
   |
14 | REQUIRED = [
15 |     "README.md", "ARCHITECTURE.md", "RUNBOOK.md", "INSTANTIATION_GUIDE.md", "SECURITY.md",
16 |     "VALIDATION.md", "DESIGN_RATIONALE.md", "CHANGELOG.md", "CONTROLLER.yaml", "TEMPLATE_VARIABLES.yaml",
   |                                                                                                     ^^^^^
17 |     "policy/authority.yaml", "policy/autonomy.yaml", "policy/evidence.yaml", "policy/parallelism.yaml",
18 |     "policy/remote-actions.yaml", "policy/risk-tiers.yaml", "policy/stop-conditions.yaml", "policy/waivers.yaml",
   |

E501 Line too long (103 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:17:101
   |
15 |     "README.md", "ARCHITECTURE.md", "RUNBOOK.md", "INSTANTIATION_GUIDE.md", "SECURITY.md",
16 |     "VALIDATION.md", "DESIGN_RATIONALE.md", "CHANGELOG.md", "CONTROLLER.yaml", "TEMPLATE_VARIABLES.yaml",
17 |     "policy/authority.yaml", "policy/autonomy.yaml", "policy/evidence.yaml", "policy/parallelism.yaml",
   |                                                                                                     ^^^
18 |     "policy/remote-actions.yaml", "policy/risk-tiers.yaml", "policy/stop-conditions.yaml", "policy/waivers.yaml",
19 |     "references/BLUEPRINT_MAPPING.md", "references/AUTHORITY_AND_RISK.md", "references/STATE_MACHINE.md",
   |

E501 Line too long (113 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:18:101
   |
16 |     "VALIDATION.md", "DESIGN_RATIONALE.md", "CHANGELOG.md", "CONTROLLER.yaml", "TEMPLATE_VARIABLES.yaml",
17 |     "policy/authority.yaml", "policy/autonomy.yaml", "policy/evidence.yaml", "policy/parallelism.yaml",
18 |     "policy/remote-actions.yaml", "policy/risk-tiers.yaml", "policy/stop-conditions.yaml", "policy/waivers.yaml",
   |                                                                                                     ^^^^^^^^^^^^^
19 |     "references/BLUEPRINT_MAPPING.md", "references/AUTHORITY_AND_RISK.md", "references/STATE_MACHINE.md",
20 |     "references/CONTRACTS_AND_SCOPE.md", "references/SCHEDULER_AND_LEASES.md", "references/WORKER_ADAPTER.md",
   |

E501 Line too long (105 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:19:101
   |
17 |     "policy/authority.yaml", "policy/autonomy.yaml", "policy/evidence.yaml", "policy/parallelism.yaml",
18 |     "policy/remote-actions.yaml", "policy/risk-tiers.yaml", "policy/stop-conditions.yaml", "policy/waivers.yaml",
19 |     "references/BLUEPRINT_MAPPING.md", "references/AUTHORITY_AND_RISK.md", "references/STATE_MACHINE.md",
   |                                                                                                     ^^^^^
20 |     "references/CONTRACTS_AND_SCOPE.md", "references/SCHEDULER_AND_LEASES.md", "references/WORKER_ADAPTER.md",
21 |     "references/VERIFICATION_AND_RECEIPTS.md", "references/RECOVERY.md", "references/REMOTE_ACTIONS.md",
   |

E501 Line too long (110 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:20:101
   |
18 |     "policy/remote-actions.yaml", "policy/risk-tiers.yaml", "policy/stop-conditions.yaml", "policy/waivers.yaml",
19 |     "references/BLUEPRINT_MAPPING.md", "references/AUTHORITY_AND_RISK.md", "references/STATE_MACHINE.md",
20 |     "references/CONTRACTS_AND_SCOPE.md", "references/SCHEDULER_AND_LEASES.md", "references/WORKER_ADAPTER.md",
   |                                                                                                     ^^^^^^^^^^
21 |     "references/VERIFICATION_AND_RECEIPTS.md", "references/RECOVERY.md", "references/REMOTE_ACTIONS.md",
22 |     "references/APPROVALS_WAIVERS_AND_HANDOFF.md", "references/NEGATIVE_TEST_MATRIX.md",
   |

E501 Line too long (104 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:21:101
   |
19 |     "references/BLUEPRINT_MAPPING.md", "references/AUTHORITY_AND_RISK.md", "references/STATE_MACHINE.md",
20 |     "references/CONTRACTS_AND_SCOPE.md", "references/SCHEDULER_AND_LEASES.md", "references/WORKER_ADAPTER.md",
21 |     "references/VERIFICATION_AND_RECEIPTS.md", "references/RECOVERY.md", "references/REMOTE_ACTIONS.md",
   |                                                                                                     ^^^^
22 |     "references/APPROVALS_WAIVERS_AND_HANDOFF.md", "references/NEGATIVE_TEST_MATRIX.md",
23 |     "schemas/controller.schema.json", "schemas/program-lock.schema.json", "schemas/source-contract.schema.json",
   |

E501 Line too long (112 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:23:101
   |
21 |     "references/VERIFICATION_AND_RECEIPTS.md", "references/RECOVERY.md", "references/REMOTE_ACTIONS.md",
22 |     "references/APPROVALS_WAIVERS_AND_HANDOFF.md", "references/NEGATIVE_TEST_MATRIX.md",
23 |     "schemas/controller.schema.json", "schemas/program-lock.schema.json", "schemas/source-contract.schema.json",
   |                                                                                                     ^^^^^^^^^^^^
24 |     "schemas/task-contract.schema.json", "schemas/attempt-receipt.schema.json", "schemas/verification-receipt.schema.json",
25 |     "schemas/approval.schema.json", "schemas/gate-evaluation.schema.json", "schemas/handoff-receipt.schema.json",
   |

E501 Line too long (123 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:24:101
   |
22 |     "references/APPROVALS_WAIVERS_AND_HANDOFF.md", "references/NEGATIVE_TEST_MATRIX.md",
23 |     "schemas/controller.schema.json", "schemas/program-lock.schema.json", "schemas/source-contract.schema.json",
24 |     "schemas/task-contract.schema.json", "schemas/attempt-receipt.schema.json", "schemas/verification-receipt.schema.json",
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^
25 |     "schemas/approval.schema.json", "schemas/gate-evaluation.schema.json", "schemas/handoff-receipt.schema.json",
26 |     "schemas/event.schema.json", "schemas/repository-registration.schema.json", "schemas/waiver.schema.json",
   |

E501 Line too long (113 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:25:101
   |
23 |     "schemas/controller.schema.json", "schemas/program-lock.schema.json", "schemas/source-contract.schema.json",
24 |     "schemas/task-contract.schema.json", "schemas/attempt-receipt.schema.json", "schemas/verification-receipt.schema.json",
25 |     "schemas/approval.schema.json", "schemas/gate-evaluation.schema.json", "schemas/handoff-receipt.schema.json",
   |                                                                                                     ^^^^^^^^^^^^^
26 |     "schemas/event.schema.json", "schemas/repository-registration.schema.json", "schemas/waiver.schema.json",
27 |     "scripts/pec.py", "scripts/instantiate.py", "scripts/validate_controller.py", "scripts/run_negative_tests.py",
   |

E501 Line too long (109 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:26:101
   |
24 |     "schemas/task-contract.schema.json", "schemas/attempt-receipt.schema.json", "schemas/verification-receipt.schema.json",
25 |     "schemas/approval.schema.json", "schemas/gate-evaluation.schema.json", "schemas/handoff-receipt.schema.json",
26 |     "schemas/event.schema.json", "schemas/repository-registration.schema.json", "schemas/waiver.schema.json",
   |                                                                                                     ^^^^^^^^^
27 |     "scripts/pec.py", "scripts/instantiate.py", "scripts/validate_controller.py", "scripts/run_negative_tests.py",
28 |     "scripts/pec/__init__.py", "scripts/pec/common.py", "scripts/pec/blueprint.py", "scripts/pec/contracts.py",
   |

E501 Line too long (114 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:27:101
   |
25 |     "schemas/approval.schema.json", "schemas/gate-evaluation.schema.json", "schemas/handoff-receipt.schema.json",
26 |     "schemas/event.schema.json", "schemas/repository-registration.schema.json", "schemas/waiver.schema.json",
27 |     "scripts/pec.py", "scripts/instantiate.py", "scripts/validate_controller.py", "scripts/run_negative_tests.py",
   |                                                                                                     ^^^^^^^^^^^^^^
28 |     "scripts/pec/__init__.py", "scripts/pec/common.py", "scripts/pec/blueprint.py", "scripts/pec/contracts.py",
29 |     "scripts/pec/controller.py", "scripts/pec/ledger.py", "scripts/pec/state.py", "scripts/pec/cli.py",
   |

E501 Line too long (111 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:28:101
   |
26 |     "schemas/event.schema.json", "schemas/repository-registration.schema.json", "schemas/waiver.schema.json",
27 |     "scripts/pec.py", "scripts/instantiate.py", "scripts/validate_controller.py", "scripts/run_negative_tests.py",
28 |     "scripts/pec/__init__.py", "scripts/pec/common.py", "scripts/pec/blueprint.py", "scripts/pec/contracts.py",
   |                                                                                                     ^^^^^^^^^^^
29 |     "scripts/pec/controller.py", "scripts/pec/ledger.py", "scripts/pec/state.py", "scripts/pec/cli.py",
30 | ]
   |

E501 Line too long (103 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:29:101
   |
27 |     "scripts/pec.py", "scripts/instantiate.py", "scripts/validate_controller.py", "scripts/run_negative_tests.py",
28 |     "scripts/pec/__init__.py", "scripts/pec/common.py", "scripts/pec/blueprint.py", "scripts/pec/contracts.py",
29 |     "scripts/pec/controller.py", "scripts/pec/ledger.py", "scripts/pec/state.py", "scripts/pec/cli.py",
   |                                                                                                     ^^^
30 | ]
31 | PLACEHOLDER = re.compile(r"\{\{[A-Z0-9_]+\}\}")
   |

E501 Line too long (102 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:67:101
   |
65 |     try:
66 |         controller = load_yaml(root / "CONTROLLER.yaml")
67 |         schema = json.loads((root / "schemas" / "controller.schema.json").read_text(encoding="utf-8"))
   |                                                                                                     ^^
68 |         for exc in Draft202012Validator(schema).iter_errors(controller):
69 |             loc = ".".join(str(v) for v in exc.path) or "<root>"
   |

E501 Line too long (102 > 100)
  --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:78:101
   |
76 |         }:
77 |             errors.append("CONTROLLER.yaml contract identifiers are not canonical v2 values")
78 |         if mode == "instantiated" and controller["controller"]["definition_status"] != "instantiated":
   |                                                                                                     ^^
79 |             errors.append("instantiated Controller requires definition_status=instantiated")
80 |     except Exception as exc:
   |

E501 Line too long (106 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:98:101
    |
 96 |             errors.append(f"{rel}: policy contract mismatch")
 97 |
 98 |     task_schema = json.loads((root / "schemas" / "task-contract.schema.json").read_text(encoding="utf-8"))
    |                                                                                                     ^^^^^^
 99 |     if task_schema.get("$id") != "program-execution-controller.rendered-contract.v2":
100 |         errors.append("task-contract schema identity mismatch")
    |

E501 Line too long (127 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:101:101
    |
 99 |     if task_schema.get("$id") != "program-execution-controller.rendered-contract.v2":
100 |         errors.append("task-contract schema identity mismatch")
101 |     if task_schema.get("properties", {}).get("schema", {}).get("const") != "program-execution-controller.rendered-contract.v2":
    |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^
102 |         errors.append("task-contract payload schema const mismatch")
    |

E501 Line too long (114 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:105:101
    |
104 |     text_files = [
105 |         p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in {".md", ".yaml", ".yml", ".json", ".py"}
    |                                                                                                     ^^^^^^^^^^^^^^
106 |     ]
107 |     for path in text_files:
    |

E501 Line too long (110 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:112:101
    |
110 |         for forbidden in FORBIDDEN if scan_for_legacy else []:
111 |             if forbidden in content:
112 |                 errors.append(f"{path.relative_to(root)}: forbidden legacy contract/state found: {forbidden}")
    |                                                                                                     ^^^^^^^^^^
113 |         if mode == "instantiated":
114 |             matches = PLACEHOLDER.findall(content)
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:116:101
    |
114 |             matches = PLACEHOLDER.findall(content)
115 |             if matches:
116 |                 errors.append(f"{path.relative_to(root)}: unresolved template variables {sorted(set(matches))}")
    |                                                                                                     ^^^^^^^^^^^^
117 |
118 |     for path in root.rglob("*.md"):
    |

E501 Line too long (114 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:126:101
    |
124 |             if clean and not (path.parent / clean).resolve().exists():
125 |                 # Links to the distribution sibling are valid only in paired layout.
126 |                 if clean.startswith("../shared/") or clean.startswith("../program-execution-blueprint-template/"):
    |                                                                                                     ^^^^^^^^^^^^^^
127 |                     continue
128 |                 errors.append(f"{path.relative_to(root)}: broken link {target}")
    |

E501 Line too long (112 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:147:101
    |
145 |             p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
146 |             for p in root.rglob("*")
147 |             if p.is_file() and p.name != "MANIFEST.yaml" and "__pycache__" not in p.parts and p.suffix != ".pyc"
    |                                                                                                     ^^^^^^^^^^^^
148 |         }
149 |         if set(expected) != set(actual):
    |

E501 Line too long (140 > 100)
   --> environment/program-execution/core/program-execution-controller-template/scripts/validate_controller.py:150:101
    |
148 | …
149 | …
150 | …ssing={sorted(set(actual)-set(expected))}, stale={sorted(set(expected)-set(actual))}")
    |                                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
151 | …:
152 | …
    |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:12:24
   |
11 | def generate(root: Path, schema: str, artifact: str) -> Path:
12 |     root=root.resolve(); files=[]
   |                        ^
13 |     for path in sorted(root.rglob('*')):
14 |         if path.is_file() and path.name != 'MANIFEST.yaml' and '__pycache__' not in path.parts and path.suffix != '.pyc':
   |

E501 Line too long (121 > 100)
  --> environment/program-execution/core/scripts/generate_manifest.py:14:101
   |
12 |     root=root.resolve(); files=[]
13 |     for path in sorted(root.rglob('*')):
14 |         if path.is_file() and path.name != 'MANIFEST.yaml' and '__pycache__' not in path.parts and path.suffix != '.pyc':
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^
15 |             files.append({'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path…
16 |     payload={'schema':schema,'schema_version':'2.0.0','artifact':artifact,'files':files,'integrity':{'algorithm':'sha256','self_exclud…
   |

E501 Line too long (225 > 100)
  --> environment/program-execution/core/scripts/generate_manifest.py:16:101
   |
14 | …and path.suffix != '.pyc':
15 | ….read_bytes()).hexdigest(),'bytes':path.stat().st_size})
16 | …ity':{'algorithm':'sha256','self_excluded':True},'summary':{'file_count':len(files),'total_bytes':sum(x['bytes'] for x in files)}}
   |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
17 | …=120),encoding='utf-8'); return target
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:17:32
   |
15 |             files.append({'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path…
16 |     payload={'schema':schema,'schema_version':'2.0.0','artifact':artifact,'files':files,'integrity':{'algorithm':'sha256','self_exclud…
17 |     target=root/'MANIFEST.yaml'; target.write_text(yaml.safe_dump(payload,sort_keys=False,width=120),encoding='utf-8'); return target
   |                                ^
18 |
19 | def main()->int:
   |

E501 Line too long (133 > 100)
  --> environment/program-execution/core/scripts/generate_manifest.py:17:101
   |
15 | …root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path.stat().st_size})
16 | ….0','artifact':artifact,'files':files,'integrity':{'algorithm':'sha256','self_excluded':True},'summary':{'file_count':len(files),'tot…
17 | …(yaml.safe_dump(payload,sort_keys=False,width=120),encoding='utf-8'); return target
   |                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
18 | …
19 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:17:119
   |
15 |             files.append({'path':path.relative_to(root).as_posix(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'bytes':path…
16 |     payload={'schema':schema,'schema_version':'2.0.0','artifact':artifact,'files':files,'integrity':{'algorithm':'sha256','self_exclud…
17 |     target=root/'MANIFEST.yaml'; target.write_text(yaml.safe_dump(payload,sort_keys=False,width=120),encoding='utf-8'); return target
   |                                                                                                                       ^
18 |
19 | def main()->int:
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:20:32
   |
19 | def main()->int:
20 |     p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--schema',required=True);p.add_argument('--artifact',…
   |                                ^
21 | if __name__=='__main__': raise SystemExit(main())
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:20:65
   |
19 | def main()->int:
20 |     p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--schema',required=True);p.add_argument('--artifact',…
   |                                                                 ^
21 | if __name__=='__main__': raise SystemExit(main())
   |

E501 Line too long (218 > 100)
  --> environment/program-execution/core/scripts/generate_manifest.py:20:101
   |
19 | …
20 | …quired=True);p.add_argument('--artifact',required=True);a=p.parse_args();print(generate(a.root,a.schema,a.artifact));return 0
   |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:20:106
   |
19 | def main()->int:
20 |     p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--schema',required=True);p.add_argument('--artifact',…
   |                                                                                                          ^
21 | if __name__=='__main__': raise SystemExit(main())
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:20:149
   |
19 | …
20 | …-schema',required=True);p.add_argument('--artifact',required=True);a=p.parse_args();print(generate(a.root,a.schema,a.artifact));retur…
   |                                                                    ^
21 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:20:166
   |
19 | …
20 | …=True);p.add_argument('--artifact',required=True);a=p.parse_args();print(generate(a.root,a.schema,a.artifact));return 0
   |                                                                    ^
21 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/generate_manifest.py:20:210
   |
19 | …
20 | …True);a=p.parse_args();print(generate(a.root,a.schema,a.artifact));return 0
   |                                                                    ^
21 | …
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/generate_manifest.py:21:24
   |
19 | def main()->int:
20 |     p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--schema',required=True);p.add_argument('--artifact',…
21 | if __name__=='__main__': raise SystemExit(main())
   |                        ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:15:48
   |
13 | def main()->int:
14 |  p=argparse.ArgumentParser(description='Instantiate aligned Blueprint and Controller siblings')
15 |  p.add_argument('--program-name',required=True);p.add_argument('--program-id',required=True);p.add_argument('--program-version',requir…
   |                                                ^
16 |  p.add_argument('--program-owner',required=True);p.add_argument('--controller-name',required=True);p.add_argument('--controller-id',re…
17 |  p.add_argument('--controller-owner',required=True);p.add_argument('--date',required=True);p.add_argument('--target',required=True,typ…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:15:93
   |
13 | def main()->int:
14 |  p=argparse.ArgumentParser(description='Instantiate aligned Blueprint and Controller siblings')
15 |  p.add_argument('--program-name',required=True);p.add_argument('--program-id',required=True);p.add_argument('--program-version',requir…
   |                                                                                             ^
16 |  p.add_argument('--program-owner',required=True);p.add_argument('--controller-name',required=True);p.add_argument('--controller-id',re…
17 |  p.add_argument('--controller-owner',required=True);p.add_argument('--date',required=True);p.add_argument('--target',required=True,typ…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:16:49
   |
14 |  p=argparse.ArgumentParser(description='Instantiate aligned Blueprint and Controller siblings')
15 |  p.add_argument('--program-name',required=True);p.add_argument('--program-id',required=True);p.add_argument('--program-version',requir…
16 |  p.add_argument('--program-owner',required=True);p.add_argument('--controller-name',required=True);p.add_argument('--controller-id',re…
   |                                                 ^
17 |  p.add_argument('--controller-owner',required=True);p.add_argument('--date',required=True);p.add_argument('--target',required=True,typ…
18 |  a=p.parse_args();target=a.target.resolve()
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:16:99
   |
14 |  p=argparse.ArgumentParser(description='Instantiate aligned Blueprint and Controller siblings')
15 |  p.add_argument('--program-name',required=True);p.add_argument('--program-id',required=True);p.add_argument('--program-version',requir…
16 |  p.add_argument('--program-owner',required=True);p.add_argument('--controller-name',required=True);p.add_argument('--controller-id',re…
   |                                                                                                   ^
17 |  p.add_argument('--controller-owner',required=True);p.add_argument('--date',required=True);p.add_argument('--target',required=True,typ…
18 |  a=p.parse_args();target=a.target.resolve()
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:17:52
   |
15 |  p.add_argument('--program-name',required=True);p.add_argument('--program-id',required=True);p.add_argument('--program-version',requir…
16 |  p.add_argument('--program-owner',required=True);p.add_argument('--controller-name',required=True);p.add_argument('--controller-id',re…
17 |  p.add_argument('--controller-owner',required=True);p.add_argument('--date',required=True);p.add_argument('--target',required=True,typ…
   |                                                    ^
18 |  a=p.parse_args();target=a.target.resolve()
19 |  if target.exists(): raise SystemExit(f'target already exists: {target}')
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:17:91
   |
15 |  p.add_argument('--program-name',required=True);p.add_argument('--program-id',required=True);p.add_argument('--program-version',requir…
16 |  p.add_argument('--program-owner',required=True);p.add_argument('--controller-name',required=True);p.add_argument('--controller-id',re…
17 |  p.add_argument('--controller-owner',required=True);p.add_argument('--date',required=True);p.add_argument('--target',required=True,typ…
   |                                                                                           ^
18 |  a=p.parse_args();target=a.target.resolve()
19 |  if target.exists(): raise SystemExit(f'target already exists: {target}')
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:18:18
   |
16 |  p.add_argument('--program-owner',required=True);p.add_argument('--controller-name',required=True);p.add_argument('--controller-id',re…
17 |  p.add_argument('--controller-owner',required=True);p.add_argument('--date',required=True);p.add_argument('--target',required=True,typ…
18 |  a=p.parse_args();target=a.target.resolve()
   |                  ^
19 |  if target.exists(): raise SystemExit(f'target already exists: {target}')
20 |  target.mkdir(parents=True)
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:19:20
   |
17 |  p.add_argument('--controller-owner',required=True);p.add_argument('--date',required=True);p.add_argument('--target',required=True,typ…
18 |  a=p.parse_args();target=a.target.resolve()
19 |  if target.exists(): raise SystemExit(f'target already exists: {target}')
   |                    ^
20 |  target.mkdir(parents=True)
21 |  bp=target/'program-execution-blueprint';ct=target/'program-execution-controller'
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:21:41
   |
19 |  if target.exists(): raise SystemExit(f'target already exists: {target}')
20 |  target.mkdir(parents=True)
21 |  bp=target/'program-execution-blueprint';ct=target/'program-execution-controller'
   |                                         ^
22 |  run([sys.executable,str(ROOT/'program-execution-blueprint-template/scripts/instantiate.py'),'--name',a.program_name,'--id',a.program_…
23 |  run([sys.executable,str(ROOT/'program-execution-controller-template/scripts/instantiate.py'),'--name',a.controller_name,'--id',a.cont…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:26:15
   |
24 |  pair={'schema':'program-execution-system.pair.v2','pair_contract':'program-execution-system.v2','program_id':a.program_id,'blueprint'…
25 |  (target/'PAIR.yaml').write_text(yaml.safe_dump(pair,sort_keys=False),encoding='utf-8')
26 |  print(target);return 0
   |               ^
27 | if __name__=='__main__': raise SystemExit(main())
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/instantiate_pair.py:27:24
   |
25 |  (target/'PAIR.yaml').write_text(yaml.safe_dump(pair,sort_keys=False),encoding='utf-8')
26 |  print(target);return 0
27 | if __name__=='__main__': raise SystemExit(main())
   |                        ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:14:54
   |
12 | ROOT=Path(__file__).resolve().parents[1]
13 | def manifest_ok(root:Path)->bool:
14 |  m=yaml.safe_load((root/'MANIFEST.yaml').read_text()); expected={x['path']:x['sha256'] for x in m.get('files',[])}
   |                                                      ^
15 |  actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!…
16 |  return expected==actual
   |

E501 Line too long (114 > 100)
  --> environment/program-execution/core/scripts/run_negative_tests.py:14:101
   |
12 | ROOT=Path(__file__).resolve().parents[1]
13 | def manifest_ok(root:Path)->bool:
14 |  m=yaml.safe_load((root/'MANIFEST.yaml').read_text()); expected={x['path']:x['sha256'] for x in m.get('files',[])}
   |                                                                                                     ^^^^^^^^^^^^^^
15 |  actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!…
16 |  return expected==actual
   |

E501 Line too long (205 > 100)
  --> environment/program-execution/core/scripts/run_negative_tests.py:15:101
   |
13 | …
14 | … for x in m.get('files',[])}
15 | … p in root.rglob('*') if p.is_file() and p.name!='MANIFEST.yaml' and '__pycache__' not in p.parts and p.suffix!='.pyc'}
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
16 | …
17 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:18:59
   |
16 |  return expected==actual
17 | def compatible(root:Path)->bool:
18 |  c=yaml.safe_load((root/'COMPATIBILITY.yaml').read_text());p=yaml.safe_load((root/'program-execution-blueprint-template/PROGRAM.yaml')…
   |                                                           ^
19 |  return p['contracts']['blueprint']==c['blueprint_contract'] and p['contracts']['pair']==c['pair_contract'] and r['contracts']=={'cont…
20 | def main()->int:
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:18:159
   |
16 | …
17 | …
18 | …xecution-blueprint-template/PROGRAM.yaml').read_text())['program'];r=yaml.safe_load((root/'program-execution-controller-template/CONT…
   |                                                                    ^
19 | …pair_contract'] and r['contracts']=={'controller':c['controller_contract'],'blueprint':c['blueprint_contract'],'pair':c['pair_contrac…
20 | …
   |

E501 Line too long (229 > 100)
  --> environment/program-execution/core/scripts/run_negative_tests.py:19:101
   |
17 | …
18 | …ution-blueprint-template/PROGRAM.yaml').read_text())['program'];r=yaml.safe_load((root/'program-execution-controller-template/CONTROLLER.ya…
19 | …r_contract'] and r['contracts']=={'controller':c['controller_contract'],'blueprint':c['blueprint_contract'],'pair':c['pair_contract']}
   |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
20 | …
21 | …ed')
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:21:50
   |
19 |  return p['contracts']['blueprint']==c['blueprint_contract'] and p['contracts']['pair']==c['pair_contract'] and r['contracts']=={'cont…
20 | def main()->int:
21 |  if not manifest_ok(ROOT) or not compatible(ROOT): raise SystemExit('positive pair fixture failed')
   |                                                  ^
22 |  with tempfile.TemporaryDirectory() as raw:
23 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));(copy/'README.md').write_text(…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:23:24
   |
21 |  if not manifest_ok(ROOT) or not compatible(ROOT): raise SystemExit('positive pair fixture failed')
22 |  with tempfile.TemporaryDirectory() as raw:
23 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));(copy/'README.md').write_text(…
   |                        ^
24 |   if manifest_ok(copy): raise SystemExit('manifest tamper falsely passed')
25 |  with tempfile.TemporaryDirectory() as raw:
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:23:104
   |
21 |  if not manifest_ok(ROOT) or not compatible(ROOT): raise SystemExit('positive pair fixture failed')
22 |  with tempfile.TemporaryDirectory() as raw:
23 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));(copy/'README.md').write_text(…
   |                                                                                                        ^
24 |   if manifest_ok(copy): raise SystemExit('manifest tamper falsely passed')
25 |  with tempfile.TemporaryDirectory() as raw:
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:24:23
   |
22 |  with tempfile.TemporaryDirectory() as raw:
23 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));(copy/'README.md').write_text(…
24 |   if manifest_ok(copy): raise SystemExit('manifest tamper falsely passed')
   |                       ^
25 |  with tempfile.TemporaryDirectory() as raw:
26 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));path=copy/'COMPATIBILITY.yaml'…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:26:24
   |
24 |   if manifest_ok(copy): raise SystemExit('manifest tamper falsely passed')
25 |  with tempfile.TemporaryDirectory() as raw:
26 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));path=copy/'COMPATIBILITY.yaml'…
   |                        ^
27 |   if compatible(copy): raise SystemExit('contract mismatch falsely passed')
28 |  print(json.dumps({'status':'PASS','fixtures':['positive_pair','root_manifest_tamper','contract_version_mismatch']},indent=2));return 0
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:26:104
   |
24 |   if manifest_ok(copy): raise SystemExit('manifest tamper falsely passed')
25 |  with tempfile.TemporaryDirectory() as raw:
26 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));path=copy/'COMPATIBILITY.yaml'…
   |                                                                                                        ^
27 |   if compatible(copy): raise SystemExit('contract mismatch falsely passed')
28 |  print(json.dumps({'status':'PASS','fixtures':['positive_pair','root_manifest_tamper','contract_version_mismatch']},indent=2));return 0
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:26:135
   |
24 | …ssed')
25 | …
26 | …re_patterns('__pycache__','*.pyc'));path=copy/'COMPATIBILITY.yaml';v=yaml.safe_load(path.read_text());v['controller_contract']='progr…
   |                                                                    ^
27 | …assed')
28 | …_manifest_tamper','contract_version_mismatch']},indent=2));return 0
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:26:170
   |
24 | …
25 | …
26 | …;path=copy/'COMPATIBILITY.yaml';v=yaml.safe_load(path.read_text());v['controller_contract']='program-execution-controller.v99';path.w…
   |                                                                    ^
27 | …
28 | …_mismatch']},indent=2));return 0
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:26:230
   |
24 | …
25 | …
26 | …ext());v['controller_contract']='program-execution-controller.v99';path.write_text(yaml.safe_dump(v,sort_keys=False))
   |                                                                    ^
27 | …
28 | …
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:27:22
   |
25 |  with tempfile.TemporaryDirectory() as raw:
26 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));path=copy/'COMPATIBILITY.yaml'…
27 |   if compatible(copy): raise SystemExit('contract mismatch falsely passed')
   |                      ^
28 |  print(json.dumps({'status':'PASS','fixtures':['positive_pair','root_manifest_tamper','contract_version_mismatch']},indent=2));return 0
29 | if __name__=='__main__':raise SystemExit(main())
   |

E501 Line too long (135 > 100)
  --> environment/program-execution/core/scripts/run_negative_tests.py:28:101
   |
26 | …gnore=shutil.ignore_patterns('__pycache__','*.pyc'));path=copy/'COMPATIBILITY.yaml';v=yaml.safe_load(path.read_text());v['controller_…
27 | …ismatch falsely passed')
28 | …itive_pair','root_manifest_tamper','contract_version_mismatch']},indent=2));return 0
   |                                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
29 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:28:127
   |
26 |   copy=Path(raw)/'pair';shutil.copytree(ROOT,copy,ignore=shutil.ignore_patterns('__pycache__','*.pyc'));path=copy/'COMPATIBILITY.yaml'…
27 |   if compatible(copy): raise SystemExit('contract mismatch falsely passed')
28 |  print(json.dumps({'status':'PASS','fixtures':['positive_pair','root_manifest_tamper','contract_version_mismatch']},indent=2));return 0
   |                                                                                                                               ^
29 | if __name__=='__main__':raise SystemExit(main())
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/run_negative_tests.py:29:24
   |
27 |   if compatible(copy): raise SystemExit('contract mismatch falsely passed')
28 |  print(json.dumps({'status':'PASS','fixtures':['positive_pair','root_manifest_tamper','contract_version_mismatch']},indent=2));return 0
29 | if __name__=='__main__':raise SystemExit(main())
   |                        ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:19:81
   |
17 | def load(path:Path)->Any:return yaml.safe_load(path.read_text(encoding='utf-8'))
18 | def child(command:list[str])->list[str]:
19 |  r=subprocess.run(command,text=True,capture_output=True,check=False,timeout=120);return [] if r.returncode==0 else [line for line in (…
   |                                                                                 ^
20 | def validate(root:Path,mode:str)->list[str]:
21 |  root=root.resolve();errors=[]
   |

E501 Line too long (187 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:19:101
   |
17 | …'))
18 | …
19 | …20);return [] if r.returncode==0 else [line for line in (r.stdout+'\n'+r.stderr).splitlines() if line.strip()]
   |                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
20 | …
21 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:21:21
   |
19 |  r=subprocess.run(command,text=True,capture_output=True,check=False,timeout=120);return [] if r.returncode==0 else [line for line in (…
20 | def validate(root:Path,mode:str)->list[str]:
21 |  root=root.resolve();errors=[]
   |                     ^
22 |  for rel in ROOT_REQUIRED:
23 |   if not (root/rel).is_file(): errors.append(f'missing required file: {rel}')
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:23:30
   |
21 |  root=root.resolve();errors=[]
22 |  for rel in ROOT_REQUIRED:
23 |   if not (root/rel).is_file(): errors.append(f'missing required file: {rel}')
   |                              ^
24 |  if errors:return errors
25 |  compat=load(root/'COMPATIBILITY.yaml');program=load(root/'program-execution-blueprint-template/PROGRAM.yaml')['program'];controller=l…
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:24:11
   |
22 |  for rel in ROOT_REQUIRED:
23 |   if not (root/rel).is_file(): errors.append(f'missing required file: {rel}')
24 |  if errors:return errors
   |           ^
25 |  compat=load(root/'COMPATIBILITY.yaml');program=load(root/'program-execution-blueprint-template/PROGRAM.yaml')['program'];controller=l…
26 |  if compat.get('pair_contract')!='program-execution-system.v2':errors.append('pair contract mismatch')
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:25:40
   |
23 |   if not (root/rel).is_file(): errors.append(f'missing required file: {rel}')
24 |  if errors:return errors
25 |  compat=load(root/'COMPATIBILITY.yaml');program=load(root/'program-execution-blueprint-template/PROGRAM.yaml')['program'];controller=l…
   |                                        ^
26 |  if compat.get('pair_contract')!='program-execution-system.v2':errors.append('pair contract mismatch')
27 |  shared_schemas={
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:25:122
   |
23 |   if not (root/rel).is_file(): errors.append(f'missing required file: {rel}')
24 |  if errors:return errors
25 |  compat=load(root/'COMPATIBILITY.yaml');program=load(root/'program-execution-blueprint-template/PROGRAM.yaml')['program'];controller=l…
   |                                                                                                                          ^
26 |  if compat.get('pair_contract')!='program-execution-system.v2':errors.append('pair contract mismatch')
27 |  shared_schemas={
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:26:63
   |
24 |  if errors:return errors
25 |  compat=load(root/'COMPATIBILITY.yaml');program=load(root/'program-execution-blueprint-template/PROGRAM.yaml')['program'];controller=l…
26 |  if compat.get('pair_contract')!='program-execution-system.v2':errors.append('pair contract mismatch')
   |                                                               ^
27 |  shared_schemas={
28 |   'shared/OWNERSHIP_MATRIX.yaml':'program-execution-system.ownership-matrix.v2',
   |

E501 Line too long (102 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:26:101
   |
24 |  if errors:return errors
25 |  compat=load(root/'COMPATIBILITY.yaml');program=load(root/'program-execution-blueprint-template/PROGRAM.yaml')['program'];controller=l…
26 |  if compat.get('pair_contract')!='program-execution-system.v2':errors.append('pair contract mismatch')
   |                                                                                                     ^^
27 |  shared_schemas={
28 |   'shared/OWNERSHIP_MATRIX.yaml':'program-execution-system.ownership-matrix.v2',
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:37:82
   |
35 |  for rel,expected_schema in shared_schemas.items():
36 |   value=load(root/rel)
37 |   if value.get('schema')!=expected_schema or value.get('schema_version')!='2.0.0':errors.append(f'{rel}: shared contract mismatch')
   |                                                                                  ^
38 |  expected={'blueprint':compat.get('blueprint_contract'),'controller':compat.get('controller_contract'),'pair':compat.get('pair_contrac…
39 |  if program.get('contracts',{}).get('blueprint')!=expected['blueprint'] or program.get('contracts',{}).get('pair')!=expected['pair']:e…
   |

E501 Line too long (131 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:37:101
   |
35 | …):
36 | …
37 | …e.get('schema_version')!='2.0.0':errors.append(f'{rel}: shared contract mismatch')
   |                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
38 | …ract'),'controller':compat.get('controller_contract'),'pair':compat.get('pair_contract')}
39 | …=expected['blueprint'] or program.get('contracts',{}).get('pair')!=expected['pair']:errors.append('Blueprint compatibility mismatch')
   |

E501 Line too long (182 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:39:101
   |
37 | …2.0.0':errors.append(f'{rel}: shared contract mismatch')
38 | ….get('controller_contract'),'pair':compat.get('pair_contract')}
39 | …program.get('contracts',{}).get('pair')!=expected['pair']:errors.append('Blueprint compatibility mismatch')
   |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
40 | …print':expected['blueprint'],'pair':expected['pair']}:errors.append('Controller compatibility mismatch')
41 | …ot/'program-execution-blueprint-template/scripts/validate_blueprint.py'),str(root/'program-execution-blueprint-template'),'--mode',mo…
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:39:133
   |
37 | …sion')!='2.0.0':errors.append(f'{rel}: shared contract mismatch')
38 | …r':compat.get('controller_contract'),'pair':compat.get('pair_contract')}
39 | …int'] or program.get('contracts',{}).get('pair')!=expected['pair']:errors.append('Blueprint compatibility mismatch')
   |                                                                    ^
40 | …r'],'blueprint':expected['blueprint'],'pair':expected['pair']}:errors.append('Controller compatibility mismatch')
41 | …le,str(root/'program-execution-blueprint-template/scripts/validate_blueprint.py'),str(root/'program-execution-blueprint-template'),'-…
   |

E501 Line too long (179 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:40:101
   |
38 | …at.get('controller_contract'),'pair':compat.get('pair_contract')}
39 | …r program.get('contracts',{}).get('pair')!=expected['pair']:errors.append('Blueprint compatibility mismatch')
40 | …ueprint':expected['blueprint'],'pair':expected['pair']}:errors.append('Controller compatibility mismatch')
   |                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
41 | …root/'program-execution-blueprint-template/scripts/validate_blueprint.py'),str(root/'program-execution-blueprint-template'),'--mode',…
42 | …(root/'program-execution-controller-template/scripts/validate_controller.py'),str(root/'program-execution-controller-template'),'--mo…
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:40:129
   |
38 |  expected={'blueprint':compat.get('blueprint_contract'),'controller':compat.get('controller_contract'),'pair':compat.get('pair_contrac…
39 |  if program.get('contracts',{}).get('blueprint')!=expected['blueprint'] or program.get('contracts',{}).get('pair')!=expected['pair']:e…
40 |  if controller.get('contracts')!={'controller':expected['controller'],'blueprint':expected['blueprint'],'pair':expected['pair']}:error…
   |                                                                                                                                 ^
41 |  errors += ['Blueprint validator: '+x for x in child([sys.executable,str(root/'program-execution-blueprint-template/scripts/validate_b…
42 |  errors += ['Controller validator: '+x for x in child([sys.executable,str(root/'program-execution-controller-template/scripts/validate…
   |

E501 Line too long (213 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:41:101
   |
39 | …ntracts',{}).get('pair')!=expected['pair']:errors.append('Blueprint compatibility mismatch')
40 | …['blueprint'],'pair':expected['pair']}:errors.append('Controller compatibility mismatch')
41 | …cution-blueprint-template/scripts/validate_blueprint.py'),str(root/'program-execution-blueprint-template'),'--mode',mode])]
   |            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
42 | …ecution-controller-template/scripts/validate_controller.py'),str(root/'program-execution-controller-template'),'--mode',mode])]
43 | ….get('canonical_owners',{})
   |

E501 Line too long (217 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:42:101
   |
40 | …blueprint'],'pair':expected['pair']}:errors.append('Controller compatibility mismatch')
41 | …tion-blueprint-template/scripts/validate_blueprint.py'),str(root/'program-execution-blueprint-template'),'--mode',mode])]
42 | …ution-controller-template/scripts/validate_controller.py'),str(root/'program-execution-controller-template'),'--mode',mode])]
   |          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
43 | …et('canonical_owners',{})
44 | …E_GATES.yaml','runtime_gate_results':'Program Execution Controller','task_runtime_state':'Program Execution Controller','final_progra…
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:43:78
   |
41 |  errors += ['Blueprint validator: '+x for x in child([sys.executable,str(root/'program-execution-blueprint-template/scripts/validate_b…
42 |  errors += ['Controller validator: '+x for x in child([sys.executable,str(root/'program-execution-controller-template/scripts/validate…
43 |  index=load(root/'program-execution-blueprint-template/EXECUTION_INDEX.yaml');owners=index.get('canonical_owners',{})
   |                                                                              ^
44 |  required_owners={'task_dependencies':'DEPENDENCY_GRAPH.yaml','gate_definitions':'CONVERGENCE_GATES.yaml','runtime_gate_results':'Prog…
45 |  for key,value in required_owners.items():
   |

E501 Line too long (263 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:44:101
   |
42 | …on-controller-template/scripts/validate_controller.py'),str(root/'program-execution-controller-template'),'--mode',mode])]
43 | …'canonical_owners',{})
44 | …ATES.yaml','runtime_gate_results':'Program Execution Controller','task_runtime_state':'Program Execution Controller','final_program_verdict':'program_owner_acceptance'}
   |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
45 | …
46 | …
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:46:28
   |
44 |  required_owners={'task_dependencies':'DEPENDENCY_GRAPH.yaml','gate_definitions':'CONVERGENCE_GATES.yaml','runtime_gate_results':'Prog…
45 |  for key,value in required_owners.items():
46 |   if owners.get(key)!=value:errors.append(f'canonical owner mismatch: {key}')
   |                            ^
47 |  tasks=load(root/'program-execution-blueprint-template/TASK_CARDS.yaml').get('tasks',[])
48 |  for task in tasks:
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:49:73
   |
47 |  tasks=load(root/'program-execution-blueprint-template/TASK_CARDS.yaml').get('tasks',[])
48 |  for task in tasks:
49 |   if 'depends_on' in task or 'runtime_state' in task or 'status' in task:errors.append(f"{task.get('id')}: task contains non-canonical…
   |                                                                         ^
50 |  gates=load(root/'program-execution-blueprint-template/CONVERGENCE_GATES.yaml').get('gates',[])
51 |  for gate in gates:
   |

E501 Line too long (161 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:49:101
   |
47 | …S.yaml').get('tasks',[])
48 | …
49 | … in task:errors.append(f"{task.get('id')}: task contains non-canonical dependency/runtime field")
   |                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
50 | …CE_GATES.yaml').get('gates',[])
51 | …
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:52:42
   |
50 |  gates=load(root/'program-execution-blueprint-template/CONVERGENCE_GATES.yaml').get('gates',[])
51 |  for gate in gates:
52 |   if 'status' in gate or 'result' in gate:errors.append(f"{gate.get('id')}: Blueprint gate contains runtime result")
   |                                          ^
53 |  action_keys={'inspect','local_write','commit','push','pull_request','merge','publish_or_release','deploy_or_migrate','destructive_cha…
54 |  for task in tasks:
   |

E501 Line too long (116 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:52:101
   |
50 |  gates=load(root/'program-execution-blueprint-template/CONVERGENCE_GATES.yaml').get('gates',[])
51 |  for gate in gates:
52 |   if 'status' in gate or 'result' in gate:errors.append(f"{gate.get('id')}: Blueprint gate contains runtime result")
   |                                                                                                     ^^^^^^^^^^^^^^^^
53 |  action_keys={'inspect','local_write','commit','push','pull_request','merge','publish_or_release','deploy_or_migrate','destructive_cha…
54 |  for task in tasks:
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:55:60
   |
53 |  action_keys={'inspect','local_write','commit','push','pull_request','merge','publish_or_release','deploy_or_migrate','destructive_cha…
54 |  for task in tasks:
55 |   if set(task.get('authorization_ceiling',{}))!=action_keys:errors.append(f"{task.get('id')}: authorization ceiling action set mismatc…
   |                                                            ^
56 |  for path in root.rglob('*'):
57 |   if path.name=='__pycache__' or path.suffix=='.pyc':errors.append(f'compiled debris: {path.relative_to(root)}')
   |

E501 Line too long (137 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:55:101
   |
53 | …','pull_request','merge','publish_or_release','deploy_or_migrate','destructive_change','external_message'}
54 | …
55 | …on_keys:errors.append(f"{task.get('id')}: authorization ceiling action set mismatch")
   |                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
56 | …
57 | …:errors.append(f'compiled debris: {path.relative_to(root)}')
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:57:53
   |
55 |   if set(task.get('authorization_ceiling',{}))!=action_keys:errors.append(f"{task.get('id')}: authorization ceiling action set mismatc…
56 |  for path in root.rglob('*'):
57 |   if path.name=='__pycache__' or path.suffix=='.pyc':errors.append(f'compiled debris: {path.relative_to(root)}')
   |                                                     ^
58 |  for path in [*root.rglob('*.md'),*root.rglob('*.yaml'),*root.rglob('*.yml'),*root.rglob('*.json'),*root.rglob('*.py')]:
59 |   if path.resolve()==Path(__file__).resolve() or path.name=='CANONICAL_VOCABULARY.yaml':continue
   |

E501 Line too long (112 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:57:101
   |
55 |   if set(task.get('authorization_ceiling',{}))!=action_keys:errors.append(f"{task.get('id')}: authorization ceiling action set mismatc…
56 |  for path in root.rglob('*'):
57 |   if path.name=='__pycache__' or path.suffix=='.pyc':errors.append(f'compiled debris: {path.relative_to(root)}')
   |                                                                                                     ^^^^^^^^^^^^
58 |  for path in [*root.rglob('*.md'),*root.rglob('*.yaml'),*root.rglob('*.yml'),*root.rglob('*.json'),*root.rglob('*.py')]:
59 |   if path.resolve()==Path(__file__).resolve() or path.name=='CANONICAL_VOCABULARY.yaml':continue
   |

E501 Line too long (120 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:58:101
   |
56 |  for path in root.rglob('*'):
57 |   if path.name=='__pycache__' or path.suffix=='.pyc':errors.append(f'compiled debris: {path.relative_to(root)}')
58 |  for path in [*root.rglob('*.md'),*root.rglob('*.yaml'),*root.rglob('*.yml'),*root.rglob('*.json'),*root.rglob('*.py')]:
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^
59 |   if path.resolve()==Path(__file__).resolve() or path.name=='CANONICAL_VOCABULARY.yaml':continue
60 |   text=path.read_text(encoding='utf-8',errors='ignore')
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:59:88
   |
57 |   if path.name=='__pycache__' or path.suffix=='.pyc':errors.append(f'compiled debris: {path.relative_to(root)}')
58 |  for path in [*root.rglob('*.md'),*root.rglob('*.yaml'),*root.rglob('*.yml'),*root.rglob('*.json'),*root.rglob('*.py')]:
59 |   if path.resolve()==Path(__file__).resolve() or path.name=='CANONICAL_VOCABULARY.yaml':continue
   |                                                                                        ^
60 |   text=path.read_text(encoding='utf-8',errors='ignore')
61 |   for pattern in LEGACY:
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:62:35
   |
60 |   text=path.read_text(encoding='utf-8',errors='ignore')
61 |   for pattern in LEGACY:
62 |    if re.search(pattern,text,re.I):errors.append(f'{path.relative_to(root)}: forbidden legacy vocabulary {pattern}')
   |                                   ^
63 |  link_pattern=re.compile(r'\[[^\]]+\]\(([^)]+)\)')
64 |  for path in root.glob('*.md'):
   |

E501 Line too long (116 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:62:101
   |
60 |   text=path.read_text(encoding='utf-8',errors='ignore')
61 |   for pattern in LEGACY:
62 |    if re.search(pattern,text,re.I):errors.append(f'{path.relative_to(root)}: forbidden legacy vocabulary {pattern}')
   |                                                                                                     ^^^^^^^^^^^^^^^^
63 |  link_pattern=re.compile(r'\[[^\]]+\]\(([^)]+)\)')
64 |  for path in root.glob('*.md'):
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:66:62
   |
64 |  for path in root.glob('*.md'):
65 |   for target in link_pattern.findall(path.read_text(encoding='utf-8')):
66 |    if target.startswith(('http://','https://','#','mailto:')):continue
   |                                                              ^
67 |    clean=target.split('#',1)[0]
68 |    if clean and not (path.parent/clean).resolve().exists():errors.append(f'{path.relative_to(root)}: broken link {target}')
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:68:59
   |
66 |    if target.startswith(('http://','https://','#','mailto:')):continue
67 |    clean=target.split('#',1)[0]
68 |    if clean and not (path.parent/clean).resolve().exists():errors.append(f'{path.relative_to(root)}: broken link {target}')
   |                                                           ^
69 |  for path in root.rglob('*.py'):
70 |   try:compile(path.read_text(encoding='utf-8'),str(path),'exec')
   |

E501 Line too long (123 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:68:101
   |
66 |    if target.startswith(('http://','https://','#','mailto:')):continue
67 |    clean=target.split('#',1)[0]
68 |    if clean and not (path.parent/clean).resolve().exists():errors.append(f'{path.relative_to(root)}: broken link {target}')
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^
69 |  for path in root.rglob('*.py'):
70 |   try:compile(path.read_text(encoding='utf-8'),str(path),'exec')
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:70:6
   |
68 |    if clean and not (path.parent/clean).resolve().exists():errors.append(f'{path.relative_to(root)}: broken link {target}')
69 |  for path in root.rglob('*.py'):
70 |   try:compile(path.read_text(encoding='utf-8'),str(path),'exec')
   |      ^
71 |   except Exception as exc:errors.append(f'{path.relative_to(root)}: Python compile failed: {exc}')
72 |  controller_handoff=json.loads((root/'program-execution-controller-template/schemas/handoff-receipt.schema.json').read_text())
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:71:26
   |
69 |  for path in root.rglob('*.py'):
70 |   try:compile(path.read_text(encoding='utf-8'),str(path),'exec')
71 |   except Exception as exc:errors.append(f'{path.relative_to(root)}: Python compile failed: {exc}')
   |                          ^
72 |  controller_handoff=json.loads((root/'program-execution-controller-template/schemas/handoff-receipt.schema.json').read_text())
73 |  shared_handoff=json.loads((root/'shared/schemas/handoff-receipt.schema.json').read_text())
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:74:61
   |
72 |  controller_handoff=json.loads((root/'program-execution-controller-template/schemas/handoff-receipt.schema.json').read_text())
73 |  shared_handoff=json.loads((root/'shared/schemas/handoff-receipt.schema.json').read_text())
74 |  if controller_handoff.get('$id')!=shared_handoff.get('$id'):errors.append('shared and Controller handoff schema identity mismatch')
   |                                                             ^
75 |  manifest=load(root/'MANIFEST.yaml')
76 |  if manifest.get('schema')!='program-execution-system.manifest.v2':errors.append('root manifest schema mismatch')
   |

E501 Line too long (132 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:74:101
   |
72 |  controller_handoff=json.loads((root/'program-execution-controller-template/schemas/handoff-receipt.schema.json').read_text())
73 |  shared_handoff=json.loads((root/'shared/schemas/handoff-receipt.schema.json').read_text())
74 |  if controller_handoff.get('$id')!=shared_handoff.get('$id'):errors.append('shared and Controller handoff schema identity mismatch')
   |                                                                                                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
75 |  manifest=load(root/'MANIFEST.yaml')
76 |  if manifest.get('schema')!='program-execution-system.manifest.v2':errors.append('root manifest schema mismatch')
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:76:67
   |
74 |  if controller_handoff.get('$id')!=shared_handoff.get('$id'):errors.append('shared and Controller handoff schema identity mismatch')
75 |  manifest=load(root/'MANIFEST.yaml')
76 |  if manifest.get('schema')!='program-execution-system.manifest.v2':errors.append('root manifest schema mismatch')
   |                                                                   ^
77 |  expected_paths={x['path']:x['sha256'] for x in manifest.get('files',[])}
78 |  actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!…
   |

E501 Line too long (113 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:76:101
   |
74 |  if controller_handoff.get('$id')!=shared_handoff.get('$id'):errors.append('shared and Controller handoff schema identity mismatch')
75 |  manifest=load(root/'MANIFEST.yaml')
76 |  if manifest.get('schema')!='program-execution-system.manifest.v2':errors.append('root manifest schema mismatch')
   |                                                                                                     ^^^^^^^^^^^^^
77 |  expected_paths={x['path']:x['sha256'] for x in manifest.get('files',[])}
78 |  actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!…
   |

E501 Line too long (205 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:78:101
   |
76 | … manifest schema mismatch')
77 | …
78 | … p in root.rglob('*') if p.is_file() and p.name!='MANIFEST.yaml' and '__pycache__' not in p.parts and p.suffix!='.pyc'}
   |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
79 | …ing={sorted(set(actual)-set(expected_paths))}, stale={sorted(set(expected_paths)-set(actual))}')
80 | …
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:79:37
   |
77 |  expected_paths={x['path']:x['sha256'] for x in manifest.get('files',[])}
78 |  actual={p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and p.name!…
79 |  if set(expected_paths)!=set(actual):errors.append(f'root manifest path mismatch: missing={sorted(set(actual)-set(expected_paths))}, s…
   |                                     ^
80 |  for rel in set(expected_paths)&set(actual):
81 |   if expected_paths[rel]!=actual[rel]:errors.append(f'root manifest digest mismatch: {rel}')
   |

E501 Line too long (182 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:79:101
   |
77 | …
78 | …igest() for p in root.rglob('*') if p.is_file() and p.name!='MANIFEST.yaml' and '__pycache__' not in p.parts and p.suffix!='.pyc'}
79 | …match: missing={sorted(set(actual)-set(expected_paths))}, stale={sorted(set(expected_paths)-set(actual))}')
   |                           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
80 | …
81 | …mismatch: {rel}')
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:81:38
   |
79 |  if set(expected_paths)!=set(actual):errors.append(f'root manifest path mismatch: missing={sorted(set(actual)-set(expected_paths))}, s…
80 |  for rel in set(expected_paths)&set(actual):
81 |   if expected_paths[rel]!=actual[rel]:errors.append(f'root manifest digest mismatch: {rel}')
   |                                      ^
82 |  return errors
83 | def main()->int:
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:84:29
   |
82 |  return errors
83 | def main()->int:
84 |  p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--mode',choices=['template','instantiated'],default='tem…
   |                             ^
85 |  print(json.dumps({'status':'PASS' if not e else 'FAIL','mode':a.mode,'errors':e},indent=2));return 0 if not e else 1
86 | if __name__=='__main__':raise SystemExit(main())
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:84:62
   |
82 |  return errors
83 | def main()->int:
84 |  p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--mode',choices=['template','instantiated'],default='tem…
   |                                                              ^
85 |  print(json.dumps({'status':'PASS' if not e else 'FAIL','mode':a.mode,'errors':e},indent=2));return 0 if not e else 1
86 | if __name__=='__main__':raise SystemExit(main())
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:84:142
   |
82 | …
83 | …
84 | …t('--mode',choices=['template','instantiated'],default='template');a=p.parse_args();e=validate(a.root,a.mode)
   |                                                                    ^
85 | …rs':e},indent=2));return 0 if not e else 1
86 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:84:159
   |
82 | …
83 | …
84 | …s=['template','instantiated'],default='template');a=p.parse_args();e=validate(a.root,a.mode)
   |                                                                    ^
85 | …;return 0 if not e else 1
86 | …
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/scripts/validate_pair.py:85:93
   |
83 | def main()->int:
84 |  p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--mode',choices=['template','instantiated'],default='tem…
85 |  print(json.dumps({'status':'PASS' if not e else 'FAIL','mode':a.mode,'errors':e},indent=2));return 0 if not e else 1
   |                                                                                             ^
86 | if __name__=='__main__':raise SystemExit(main())
   |

E501 Line too long (117 > 100)
  --> environment/program-execution/core/scripts/validate_pair.py:85:101
   |
83 | def main()->int:
84 |  p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--mode',choices=['template','instantiated'],default='tem…
85 |  print(json.dumps({'status':'PASS' if not e else 'FAIL','mode':a.mode,'errors':e},indent=2));return 0 if not e else 1
   |                                                                                                     ^^^^^^^^^^^^^^^^^
86 | if __name__=='__main__':raise SystemExit(main())
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/scripts/validate_pair.py:86:24
   |
84 |  p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--mode',choices=['template','instantiated'],default='tem…
85 |  print(json.dumps({'status':'PASS' if not e else 'FAIL','mode':a.mode,'errors':e},indent=2));return 0 if not e else 1
86 | if __name__=='__main__':raise SystemExit(main())
   |                        ^
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/tests/test_pair_alignment.py:14:73
   |
12 |   p=yaml.safe_load((ROOT/'program-execution-blueprint-template/PROGRAM.yaml').read_text())['program']
13 |   c=yaml.safe_load((ROOT/'program-execution-controller-template/CONTROLLER.yaml').read_text())['controller']
14 |   self.assertEqual(p['contracts']['pair'],'program-execution-system.v2');self.assertEqual(c['contracts']['pair'],'program-execution-sy…
   |                                                                         ^
15 |   self.assertEqual(c['contracts']['blueprint'],p['contracts']['blueprint'])
16 |  def test_runtime_fields_do_not_leak_into_blueprint(self):
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/tests/test_pair_alignment.py:19:92
   |
17 |   tasks=yaml.safe_load((ROOT/'program-execution-blueprint-template/TASK_CARDS.yaml').read_text())['tasks']
18 |   gates=yaml.safe_load((ROOT/'program-execution-blueprint-template/CONVERGENCE_GATES.yaml').read_text())['gates']
19 |   self.assertTrue(all(not ({'status','runtime_state','depends_on'}&set(t)) for t in tasks));self.assertTrue(all(not ({'status','result…
   |                                                                                            ^
20 |  def test_rendered_contract_schema_identity(self):
21 |   s=json.loads((ROOT/'program-execution-controller-template/schemas/task-contract.schema.json').read_text())
   |

E501 Line too long (161 > 100)
  --> environment/program-execution/core/tests/test_pair_alignment.py:19:101
   |
17 | …te/TASK_CARDS.yaml').read_text())['tasks']
18 | …te/CONVERGENCE_GATES.yaml').read_text())['gates']
19 | …'}&set(t)) for t in tasks));self.assertTrue(all(not ({'status','result'}&set(g)) for g in gates))
   |                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
20 | …
21 | …mas/task-contract.schema.json').read_text())
   |

E702 Multiple statements on one line (semicolon)
  --> environment/program-execution/core/tests/test_pair_alignment.py:22:81
   |
20 |  def test_rendered_contract_schema_identity(self):
21 |   s=json.loads((ROOT/'program-execution-controller-template/schemas/task-contract.schema.json').read_text())
22 |   self.assertEqual(s['$id'],'program-execution-controller.rendered-contract.v2');self.assertEqual(s['properties']['schema']['const'],s…
   |                                                                                 ^
23 | if __name__=='__main__':unittest.main()
   |

E701 Multiple statements on one line (colon)
  --> environment/program-execution/core/tests/test_pair_alignment.py:23:24
   |
21 |   s=json.loads((ROOT/'program-execution-controller-template/schemas/task-contract.schema.json').read_text())
22 |   self.assertEqual(s['$id'],'program-execution-controller.rendered-contract.v2');self.assertEqual(s['properties']['schema']['const'],s…
23 | if __name__=='__main__':unittest.main()
   |                        ^
   |

Found 527 errors (46 fixed, 481 remaining).

ruff format..............................................................................Passed

[This shell is producing too much output to stream. The command will still run.]
make: *** [pr] Error 1
