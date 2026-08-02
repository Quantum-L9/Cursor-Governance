# Contracts and Scope

A Source Contract must be a strict subset of the Task Card:

- same task and target identity;
- requested actions cannot exceed the Blueprint authorization ceiling;
- risk tier cannot be lower than the Blueprint tier;
- writable paths are repository-relative and non-empty for mutating repository tasks;
- acceptance and validation obligations may be strengthened but not removed;
- required gates, decisions, Unknowns, and evidence cannot be omitted;
- remote mutation is denied in the universal core.

The Rendered Contract adds Program Lock digest, exact base SHA, branch, worktree, lease, attempt number, receipt path, and final contract digest.
