"""Autonomy test namespace.

`stacked_repo` is intentionally declared in the repository-root ``conftest.py``.
The scoped publication runner selects test files across multiple top-level roots;
the root fixture remains available to that composite selection while this local
module stays free of a duplicate fixture definition.
"""
