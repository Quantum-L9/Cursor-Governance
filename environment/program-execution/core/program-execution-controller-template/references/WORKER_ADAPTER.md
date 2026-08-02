# Worker Adapter Contract

A worker adapter may connect Cursor, Claude Code, ChatGPT, a local agent, CI runner, or human engineer. It receives one Rendered Contract and one isolated execution context, exposes only required permissions, withholds remote credentials by default, preserves contract identity, writes the required Attempt Receipt, and never verifies its own work.
