# Quick Start

## Export data from Gnucash

1. `File` → `Export` → `Export Transactions to CSV …`
2. `Next`
3. `Select All`, `Next`
4. Enter filename, for example, `transactions.csv`

## Load it into Ledger Explorer demo site
1. Browse to [https://ledge.uprightconsulting.com/ds](https://ledge.uprightconsulting.com/ds)
2. Under Transactions, click `Select a file`
3. Select the Gnucash CSV file you just created.
4. Click the Cash Flow and Balance Sheet tabs to see your data.

# User Manual

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

## Data Source tab

![Screenshot](https://raw.githubusercontent.com/saufrecht/ledger-explorer/master/docs/data_source.png?s=820x838)

### Features
* Load transaction file from URL or upload
* Load Account Tree (optional)
* Load Custom Reporting Periods (optional)
* Adjust parameters
* Make a bookmark

### Instructions
This tab determines which data the program uses.  It can read Transaction CSV exports from GnuCash.  It can also read any csv file with these properties:
* one row is one ledger entry.  That is, either an full entry in single-entry bookkeeping or one entry (debit or credit) out of a double-entry system.
* The following columns are present and labelled exactly:
  * **Account Name**.
  * **Description** and/or **Notes** *(optional)*.  Any blanks in these fields get filled with the closest previous entry.
  * **Memo** *(optional)*  Not filled.  Combined with 'Description' and 'Notes' to make a single 'description' field.
  * **Full Account Name**.  An ordered list of the account tree, delimited by colons.  For example: "Assets:Short-Term:North Korean Energy Bonds"
  * **Date**. Entry date.
  * **Amount Num**. Value of the transaction.  Ledger Explorer assumes all values are the same currency.


Read a CSV or XLS file, one row per transaction.


* If column names in the source data don't match the Fields listed, enter new column names.  Matching and renaming ignores capitalization
* Date: required.  parsable date, or YYYY.
* Label for each individual transaction (if importing Gnucash, Notes and Memo added automatically)
* Used to determine account tree.  Full path of account, e.g., Assets:Tools:Wheelbarrow.
* Alternative method for account tree
* Account tree is derived from tree source file if present, or transaction source if not.  Within each source, full account name is preferred over parent.
* Delimiter: If Full Account Names are used to generate the path, use this delimiter between each account name.
* Unit: For data not in dollars.  E.g., in $000s, or another unit altogether.
* Alternate label for Cash Flow, e.g., Examining cumulative data by account
* Alternate label for Balance Sheet, e.g., Examining transactions as flows by account and time
