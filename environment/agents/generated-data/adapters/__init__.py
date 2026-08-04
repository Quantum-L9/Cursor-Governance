"""
Destination and repository-class adapters for L9 subagent-generated data.
Adapters do not decide whether a unit is eligible for promotion. They receive
already evaluated promotion results and translate approved units into
destination-specific envelopes.
Authority remains with:
- the routing engine;
- the promotion gate;
- the destination system;
- and designated human or canonical authorities where required.
"""

__version__ = "1.0.0"
