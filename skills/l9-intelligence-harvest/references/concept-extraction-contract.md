# Concept Extraction Contract

Extract semantic concepts from reconstructed donor behavior. Do not copy donor implementation merely because it exists.

## Concept shape

For each candidate identify:

- stable problem solved;
- semantic contract, expressed independently of donor-specific implementation;
- supporting evidence IDs;
- donor-specific assumptions and infrastructure weight;
- likely beneficiary destination;
- risks;
- candidate disposition.

A concept remains a concept until deterministic qualification closes it as a nugget.

## Semantic portability test

A portable candidate must remain meaningful after removing donor-specific:

- identity and naming;
- execution authority;
- infrastructure/runtime machinery;
- incidental implementation detail.

If donor runtime is genuinely required, represent it as an explicit external dependency. Do not smuggle implementation ownership into a semantic transfer.
