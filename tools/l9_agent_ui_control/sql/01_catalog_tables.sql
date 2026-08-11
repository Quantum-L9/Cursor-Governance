SET NOCOUNT ON;
SELECT
    s.name AS schema_name,
    t.name AS table_name,
    SUM(p.rows) AS approx_row_count
FROM sys.tables AS t
INNER JOIN sys.schemas AS s ON s.schema_id = t.schema_id
INNER JOIN sys.partitions AS p ON p.object_id = t.object_id AND p.index_id IN (0, 1)
WHERE t.is_ms_shipped = 0
GROUP BY s.name, t.name
ORDER BY s.name, t.name;
