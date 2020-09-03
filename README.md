# ledger-explorer
Navigate a hierarchical ledger graphically, all the way down to individual transactions.  This tool's purpose is enabling quick navigation through a graphical view of aggregate data in a pie chart or bar chart, representing tens of thousands of records, to a list of specific transactions.  This seems like a really obvious feature but has been surprisingly (in my limited experienc) rare in off-the-shelf F/OSS interactive visualization tools.  The Plotly Dashboard works very well for this purpose.

![Screenshot](https://raw.githubusercontent.com/saufrecht/ledger-explorer/master/docs/montage.jpg?s=820x838)

# Installation

## get the code

`git clone https://github.com/saufrecht/ledger-explorer.git`

`cd ledger-explorer`

## Confirm Python version 3.8 or higher

Use `python --version` to confirm your version of Python.  It must be version 3.8.0 or higher.

* This version is included in Ubuntu 20.04.
* [Windows Download](https://www.python.org/downloads/windows/)

## Make and activate a virtual environment

The path for your virtual environment should not be inside the source-controlled ledger-explorer directory; if it is, you'll need to modify `.gitignore` to ignore it.  The ideal place for this directory depends on your local configuration.  One reasonable and safe choice on Mac/Linux is `~/.venv_le`.  On Windows, best practice is unclear (or unknown to your humble but lazy documenter).  Using a virtual environment is technically optional but a very very good idea. See [Python documentation on Virtual Environments](https://docs.python.org/3/tutorial/venv.html) for more information.

You will need to activate the virtual environment every time you open a new shell to run Ledger Explorer.

### Mac and Linux

1. `python3 -m venv /path/to/myenv`
2. `source /path/to/myenv/bin/activate`

### Windows

1. `c:\>c:\Python38\python -m venv c:\path\to\myenv`
2. .\path\to\myenv\Scripts\activate

### Install prerequisite Python modules

`pip install -r requirements.txt`

## Prepare data

### Export data from Gnucash

1. `File` → `Export` → `Export Transactions to CSV …`
2. `Next`
3. `Select All`, `Next`
4. Enter filename, for example, `transactions.csv`

## Run program
1. `python ledger_explorer/index.py`
1. Browse to http://localhost:8050.
1. In the *Load File* » *Transaction File* » "Drag and Drop or Select Files" box, either
  1. Drop transactions.csv into the box from another window,
  1. Or, click 'Select Files' and select transactions.csv
1. If everything works, you should see something similar to the screenshot.

### Warnings
1. This is the development mode for Dash; do not deploy this on the web or otherwise use in a production environment.
1. Anyone on your local network, for example anyone on the same wifi, may be able to access this site.

# Usage

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

# Known Bugs

1. If no era file is present, clicking the Era selector will cause an error.

# Roadmap

1. Complete unit testing
1. Verify running in gunicorn
1. Publish somewhere as a free service
1. Implement night mode using Dash's native commands
1. Add ability to import at least 1 public data set, maybe national budget?
1. Improve navigation and charting tools

# Contributing

Yes, please.  Questions, requests, better documentation, and patches welcome.
