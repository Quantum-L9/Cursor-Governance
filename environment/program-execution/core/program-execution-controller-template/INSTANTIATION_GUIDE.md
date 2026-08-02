# Instantiation Guide

Inputs:

- an instantiated `program-execution-blueprint.v2` Blueprint;
- Controller name, ID, owner, and creation timestamp;
- local repository mappings or explicit external adapters;
- optional worker-host and remote-action adapters.

The Controller expects every source in the Blueprint `EXECUTION_INDEX.yaml`, validates them, records all SHA-256 digests, and refuses unknown or mismatched contract versions.

Domain or host behavior belongs in adapters. Do not alter universal authority, evidence, state-transition, or recovery laws for convenience.
