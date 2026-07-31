# Ecosystem Adapters

Select the adapter already used by the repository. Do not migrate ecosystems to make the CLI easier to build.

## Python

- Entry point: `[project.scripts]` in `pyproject.toml` or the repository's established equivalent.
- Preserve the existing build backend and dependency manager.
- Prefer `argparse`, Click, Typer, or the existing framework already present.
- Validate wheel/sdist build when the project publishes packages.
- Smoke with an isolated install or the repository's native environment command.

## Node.js and TypeScript

- Entry point: `package.json` `bin` mapped to a built executable file with a shebang.
- Preserve ESM/CommonJS and package-manager conventions.
- Ensure build output is included in package files.
- Validate package packing and run the packed binary, not only source execution.

## Go

- Entry point: `cmd/<name>/main.go` or the repository's existing command layout.
- Prefer a single static binary unless project requirements differ.
- Validate supported target build, `go test ./...`, and installed binary smoke.
- Record version injection mechanism if used.

## Rust

- Entry point: `[[bin]]` or `src/bin/<name>.rs` under existing Cargo conventions.
- Preserve feature flags and MSRV.
- Validate `cargo test`, lint/format gates, release build, and binary smoke.

## Other ecosystems

Inspect the repository's package and release files. Derive an explicit adapter with entrypoint, build, install, test, publish, and rollback commands. Mark unsupported assumptions `UNKNOWN` instead of forcing one of the adapters above.
