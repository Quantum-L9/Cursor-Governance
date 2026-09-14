package semanticconflict
deny[msg] { input.verdict == "FAIL"; msg := sprintf("semantic merge probe failed: %v", [input.reason]) }
