# KPI Scorecard

## Corpus integrity
- artifact coverage ratio
- unexplained coverage gaps
- exact duplicate precision
- unresolved explicit-reference rate
- topology validation pass rate
- stale-current-fact defects after delta runs

## Retrieval quality
- REQUIRED artifact precision/recall against expert gold set
- context compression ratio = selected context / connected corpus candidates
- dependency recall
- blocker recall
- supersession noise reduction
- conflict/Unknown miss rate
- downstream clarification count

## Planning quality
- expert agreement on top leverage class
- dependency-order violations
- parallelism captured
- unlock fan-out prediction accuracy
- WorkUnit churn between unchanged runs
- plan revision stability under irrelevant corpus changes

## Execution outcome feedback
- planned vs actual effort class
- planned vs actual blockers
- WorkUnit completion rate
- discovered hidden dependency rate
- first-pass CI success
- number of user interruptions caused by missing context
