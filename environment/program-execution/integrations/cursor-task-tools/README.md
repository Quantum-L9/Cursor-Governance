# Cursor Task Transports

The transports write digest-bound task requests into the Program runtime. A
Cursor host consumes the request and writes a typed result beside it. No second
Cursor scheduler, rule set, plugin, or Background Agents API is introduced.
