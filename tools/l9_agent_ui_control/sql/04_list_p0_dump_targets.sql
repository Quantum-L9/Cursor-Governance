SET NOCOUNT ON;
/*
  P0 dump candidates for PlasticOS unlock:
  - counterparties / addresses / contacts / reps
  - payment / AR / AP / invoice / worksheet detail heuristics
*/
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    SUM(p.rows) AS approx_row_count
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
INNER JOIN sys.partitions AS p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
WHERE t.is_ms_shipped = 0
  AND (
        t.name LIKE '%Cust%'
     OR t.name LIKE '%Supp%'
     OR t.name LIKE '%Vendor%'
     OR t.name LIKE '%Address%'
     OR t.name LIKE '%Contact%'
     OR t.name LIKE '%Agent%'
     OR t.name LIKE '%Rep%'
     OR t.name LIKE '%Salesperson%'
     OR t.name LIKE '%Counterparty%'
     OR t.name LIKE '%Company%'
     OR t.name LIKE '%Pay%'
     OR t.name LIKE '%Cash%'
     OR t.name LIKE '%AR%'
     OR t.name LIKE '%AP%'
     OR t.name LIKE '%Receipt%'
     OR t.name LIKE '%Check%'
     OR t.name LIKE '%Cheque%'
     OR t.name LIKE '%Invoice%'
     OR t.name LIKE '%Payment%'
     OR t.name LIKE '%Remit%'
     OR t.name LIKE '%Ledger%'
     OR t.name LIKE '%Apply%'
     OR t.name LIKE '%Settle%'
     OR t.name LIKE '%Aging%'
     OR t.name LIKE '%OpenItem%'
     OR t.name LIKE '%Wks%'
     OR t.name LIKE '%Detail%'
     OR t.name LIKE '%Grade%'
     OR t.name LIKE '%Material%'
  )
GROUP BY s.name, t.name
ORDER BY approx_row_count DESC, s.name, t.name;
