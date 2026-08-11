SET NOCOUNT ON;
/* Probe TOP (N) on high-value cieTrade_SM candidates — agent-authored. */
SELECT TOP (20) 'Payables' AS src, * FROM dbo.Payables;
SELECT TOP (20) 'Receipt' AS src, * FROM dbo.Receipt;
SELECT TOP (20) 'AccountingPayment' AS src, * FROM dbo.AccountingPayment;
SELECT TOP (20) 'Checks' AS src, * FROM dbo.Checks;
SELECT TOP (20) 'CounterParty' AS src, * FROM dbo.CounterParty;
SELECT TOP (20) 'Address' AS src, * FROM dbo.Address;
SELECT TOP (20) 'WKSDetail' AS src, * FROM dbo.WKSDetail;
