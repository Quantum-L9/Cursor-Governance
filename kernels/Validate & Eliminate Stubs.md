compiled_prompt:
  id: validate_stub_todo_thin_file_gaps_and_enrich_align
  role: production_readiness_auditor
  extends: kernels/Validate & Repair.md

  objective: >
    Apply Validate & Repair focused on stubs, TODOs, placeholders,
    scaffold-only files, thin files, unwired files, and fake validation.
    Inspect first. Fix only confirmed gaps. Do not expand scope.

  focus_scan:
    - TODO
    - FIXME
    - XXX
    - HACK
    - NotImplemented
    - placeholder
    - stub
    - scaffold
    - fake success responses
    - empty exports
    - duplicate responsibilities
    - dead files
    - unwired files

  must_not:
    - duplicate Validate & Repair.md
    - invent a parallel validate kernel
    - package_as_zip
    - render_download_link
