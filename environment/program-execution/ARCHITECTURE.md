# Adapter-Layer Architecture

The Controller renders a digest-bound contract. A router selects a fresh,
conformant adapter whose capabilities and authority cover the request. The
adapter returns lifecycle receipts and a canonical terminal receipt. Independent
verification remains a separate adapter and the Controller alone advances
program state.

```text
Controller -> router -> adapter -> provider -> host
     ^           |          |          |
     +--- canonical receipts + lifecycle evidence
```

Existing runtime providers are invoked through bridges. Their schedulers,
leases, identities, and memory transports are never copied into this tree.
