package environmentlease
deny[msg] { a := input.leases[i]; b := input.leases[j]; i != j; a.state == "active"; b.state == "active"; a.resources.db_branch == b.resources.db_branch; msg := sprintf("leases %v and %v share db_branch %v", [a.node_id, b.node_id, a.resources.db_branch]) }
