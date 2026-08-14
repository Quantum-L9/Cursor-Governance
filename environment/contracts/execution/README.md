# Execution contracts

This directory is the first-class SSOT for L9 execution architecture law and
registered execution templates.

## Binding law

`PEER_EXECUTION_THIN_ADAPTER_LAW.yaml` requires:

```text
Program Controller
-> Peer Runtime Binding
-> Execution Profile
-> Peer Execution Core
-> Shared Transport
-> Thin Provider
-> Provider / Host
```

The accepted decisions implementing that law live under `adr/`.

## Execution template

`templates/canonical.template.executable_plan.v1.plan.md` remains the canonical
executable-plan template.

## Law

- This directory is repo SSOT for registered execution contracts/templates.
- Provider adapters MUST remain thin.
- Peer identity MUST resolve from `PEER_RUNTIME_BINDINGS.yaml`, never a provider.
- Shared execution behavior MUST move upstream rather than be copied.
- Program Execution remains the sole Program-state authority.
