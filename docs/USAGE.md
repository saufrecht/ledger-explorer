# Ledger Explorer User Manual

## Data Source tab

![Screenshot](https://raw.githubusercontent.com/saufrecht/ledger-explorer/master/docs/data_source.png?s=820x838)

### Features
This tab determines which data the program uses.  It reads Transaction CSV exports from GnuCash, and can read any csv file with these properties:
* one row is one ledger entry.  That is, either an full entry in single-entry bookkeeping or either the credit or the debit from double-entry.
* The following columns are present and labelled exactly:
  * **Account Name**.
  * **Description** and/or **Notes** *(optional)*.  Any blanks in these fields get filled with the closest previous entry.
  * **Memo** *(optional)*  Not filled.  Combined with 'Description' and 'Notes' to make a single 'description' field.
  * **Full Account Name**.  An ordered list of the account tree, delimited by colons.  For example: "Assets:Short-Term:North Korean Energy Bonds"
  * **Date**. Entry date.
  * **Amount Num**. Value of the transaction.  Ledger Explorer assumes all values are the same currency.

### Usage

1. If installed as described above, this tab will load the provided sample transaction file automatically.
1. To load other data, enter the file name and click *reload*.

## Cash Flow

![Screenshot](https://raw.githubusercontent.com/saufrecht/ledger-explorer/master/docs/cash_flow_2.png?s=820x838)

### Features

1. A time series of all transactions in Expenses and Income, grouped by Year, Quarter, or Month
1. A sunburst view of all transactions in the selected time series bar or bars.
1. A transaction table showing all transactions in the selected sunburst pie slice (account) and its child accounts.

### Controls

1. Click or draw a selection box on the time series to narrow down the data selection.
1. Click on a pie slice in the sunburst to select transactions to load.
1. Click Era/Year/Quarter/Month button to change the grouping period of data.
1. Monthly/Annualized toggle.  Click to show Annualized values, i.e., Monthly values times twelve.
1. transaction table supports sorting and filtering for any field …

## Balance Sheet

![Screenshot](https://raw.githubusercontent.com/saufrecht/ledger-explorer/master/docs/balance_sheet.png?s=820x838)

### Features
1. Time series of cumulative value of all Assets, Liabilities, and Equity.  Grouped by Year, Quarter, or Month.
1. A transaction table showing all transactions, and cumulative total, for selected accounts up to the point of selection.
