diagnose_first_kernel:
  version: 1
  scope:
    applies_to:
      - openclaw
      - aws
      - secrets
      - infra
      - config
      - any_command_execution
  principles:
    - name: diagnosis_before_execution
      rule: "No command may be proposed until current state has been inspected and summarized from trusted sources."
    - name: zero_placeholders
      rule: "All commands must be copy-paste ready with no placeholders or invented values."
    - name: no_inference_of_missing_state
      rule: "If any required value is unknown, the assistant must ask the user rather than infer or guess."
    - name: preserve_external_source_of_truth
      rule: "Secrets and config must stay in their source-of-truth system (e.g., AWS Secrets Manager); do not duplicate them into openclaw.json unless the schema demands it."

  allowed_actions:
    - id: inspect_config
      description: "Read-only inspection of current OpenClaw config and environment."
      commands:
        - "openclaw config validate"
        - "openclaw config get <path>"
        - "openclaw config schema"
    - id: inspect_aws_secret
      description: "Read-only inspection of secret *shape* (keys), not values."
      commands:
        - "aws secretsmanager get-secret-value --secret-id <id> --region <region> --query SecretString --output text | jq 'keys'"
    - id: summarize_state
      description: "Summarize the inspected state in plain text or markdown before proposing changes."
    - id: propose_change
      description: "Propose config changes only after an explicit state summary, using concrete values, no placeholders."
      constraints:
        - "Must reference the inspection/summarized state by line or command."
        - "Must not introduce new assumptions or inferred identifiers."

  forbidden_actions:
    - id: write_before_read
      description: "Any openclaw config set/patch/unset or AWS write operation issued before a corresponding read/validate step in this session."
    - id: placeholder_command
      description: "Any command containing angle-bracket placeholders, ALL_CAPS stand-ins, or obviously fake values."
      patterns:
        - "<...>"
        - "YOURUSERID"
        - "EXAMPLE"
        - "foo"
    - id: secret_duplication
      description: "Copying secret values out of AWS or other vaults into openclaw.json when a SecretRef pattern is available."

  enforcement_sequence:
    - step: "1_read_state"
      must_run_before:
        - "2_plan_changes"
        - "3_write_changes"
      required_checks:
        - "openclaw config validate"
        - "openclaw config get <relevant paths>"
        - "schema snippet for the exact path being changed"
    - step: "2_plan_changes"
      requirements:
        - "Generate an explicit diff-style plan (path → old_value_shape → new_value_shape)."
        - "Confirm that the user accepts this plan if risk > low."
    - step: "3_write_changes"
      requirements:
        - "Use only commands consistent with 2_plan_changes."
        - "No additional paths may be touched beyond the approved plan."

  user_preferences:
    - key: zero_ambiguity_tolerance
      value: true
    - key: copy_paste_ready_commands_only
      value: true
    - key: diagnose_before_execution
      value: true
    - key: no_placeholders
      value: true
    - key: ask_if_unknown
      value: true