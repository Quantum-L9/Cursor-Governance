"""
Wave 3 IDE adapter layer.
Adapters are untrusted orchestration clients. They cannot authorize work.
They may only:
1. register and pass conformance,
2. request a runnable action,
3. receive a scoped lease and agent contract,
4. acknowledge exact capabilities,
5. mediate tool calls through the capability gateway,
6. submit typed artifacts,
7. report status.
Direct mutation, autonomous merge, invented topology, and gateway bypass are
not valid adapter operations.
"""
__version__ = "1.0.0"
