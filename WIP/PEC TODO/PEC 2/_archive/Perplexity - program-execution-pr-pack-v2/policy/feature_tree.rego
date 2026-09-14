package featuretree
deny[msg] { node := input.nodes[_]; count(node.gates) < 2; msg := sprintf("node %v declares fewer than 2 required gates", [node.id]) }
deny[msg] { node := input.nodes[_]; not startswith(node.branch, "feat/"); not startswith(node.branch, "fix/"); msg := sprintf("node %v branch '%v' must start with feat/ or fix/", [node.id, node.branch]) }
deny[msg] { input.stack_base != "main"; msg := sprintf("stack_base must be 'main', got '%v'", [input.stack_base]) }
