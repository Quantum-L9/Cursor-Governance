SET NOCOUNT ON;
-- cieTrade_SM_EXPORT — sample rows for PlasticOS field mapping

SELECT TOP (10)
  PayableID, BuySellNo, ItemID, CpID, Amount, InvoiceNo, InvoiceDt, RcvDt,
  Posted, CurrencyCd, FxAmount, IsCheck, CheckNo, APBatchNo, Reference_Date
FROM dbo.Payables
ORDER BY InvoiceDt DESC;

SELECT TOP (10)
  ReceiptID, BuySellNo, Amount, CheckNo, PaymentDt, EntryDt, DiscountAmt,
  LedgerID, PostingType, Reference, CurrencyCd, FxAmount, DepositDate, ARBatchNo
FROM dbo.Receipt
ORDER BY PaymentDt DESC;

SELECT TOP (10)
  LedgerID, TradeDt, BuySellNo, Source, Sale, Cost, GrossProfit, Commission,
  AdjCpID, AdjType, AdjFxAmount, APBatchNo, ARBatchNo, ReferenceID
FROM dbo.GPLedger
ORDER BY TradeDt DESC;

SELECT TOP (10)
  CpID, CompanyNm, Role, ActiveStatus, MasterAccountID, OurCustNo, Terms, TermsCode,
  APEMail, PaymentDays, CurrCode, OnHold, CreditLimit
FROM dbo.CounterParty
ORDER BY CompanyNm;

SELECT TOP (10)
  AddressID, CpID, Type, Addr1, Addr2, City, Region, PostalCd, Country,
  Telephone, Email, InvoiceAddr, RemitToAddress, isBillingAddressOnly
FROM dbo.Address
ORDER BY CpID;

SELECT TOP (10)
  CT_ID, CpID, ContactNm, CompanyNm, Email, PhoneBusiness, PhoneMobile, IsActive, Location
FROM dbo.Contact
WHERE IsActive IN ('Y', 'N') OR IsActive IS NULL
ORDER BY CpID;
