package mergequeue
deny[msg] { node := input.nodes[_]; node.state == "merged"; dep := node.depends_on[_]; dep_node := input.nodes[_]; dep_node.id == dep; dep_node.state != "merged"; msg := sprintf("%v is merged but dependency %v is not", [node.id, dep]) }
