# ledger-explorer
Navigate any hierarchical ledger graphically, all the way down to individual transactions.  The special thing here is moving quickly from a graphical view of aggregate data, like a pie chart or bar chart, to a list of specific transactions.  This seems like a really obvious feature but has been surprisingly (in my limited experienc) rare in off-the-shelf F/OSS tools.  The Plotly Dashboard works very well for this purpose.


![Screenshot](https://github.com/saufrecht/ledger-explorer/raw/master/screenshot.png?s=600)

# Installation

## get the code

`git clone https://github.com/saufrecht/ledger-explorer.git`
`cd ledger-explorer`

## Make a virtual environment

`python3 -m venv ~/.venv_le`

The path `~/.venv_le` is completely arbitrary and your naming conventions may vary.  This is a best practice, not a requirement for running this program.  See [Python documentation on Virtual Environments](https://docs.python.org/3/tutorial/venv.html) for more information.

`source ~/.venv_le/bin/activate`

`pip install -r requirements.txt`

### Export data from Gnucash

1. `File` → `Export` → `Export Transactions to CSV …`
2. `Next`
3. `Select All`, `Next`
4. Enter filename, for example, `transactions.csv`

#### Publish your data
Ledger Explorer loads data from a URL.  So, if you want to load your Gnucash export, which is a local file, you have to publish that file on a webserver that your browser can access.  On Ubuntu, this can be done with:

`sudo apt install nginx`

`sudo cp sample_data.csv /var/www/html/transactions.csv`

### Run program
1. `python ledger_explorer/index.py`
1. Browse to http://localhost:8050


### Usage

#### Data Source tab

This tab determines which data the program uses.  It reads Transaction CSV exports from GnuCash, and can read any csv file with these properties:
* one row is one ledger entry.  That is, either an full entry in single-entry bookkeeping or either the credit or the debit from double-entry.
* The following columns are present and labelled exactly:
** Required: *Account Name*
** Optional: *Description* and/or *Notes*.  Any blanks in these fields get filled with the closest previous entry.
** Optional: *Memo*.  Not filled.  Combined with 'Description' and 'Notes' to make a single 'description' field.
** Required: *Full Account Name*.  An ordered list of the account tree, delimited by colons.  For example: "Assets:Short-Term:North Korean Energy Bonds"
** Required: *Date* Entry date.
** Required: *Amount Num* Value of the transaction.  Ledger Explorer assumes all values are the same currency.

If installed as described above, this tab will load the provided sample transaction file automatically.

#### Cash Flow

##### Features
# A time series of all transactions in Expenses and Income, grouped by Year, Quarter, or Month
# A sunburst view of all transactions in the selected time series bar or bars.
# A transaction table showing all transactions in the selected sunburst pie slice (account) and its child accounts.

##### Controls
* Click or draw a selection box on the time series to narrow down the data selection.
* Click on a pie slice in the sunburst to select transactions to load.
* Click Era/Year/Quarter/Month button to change the grouping period of data.
* Monthly/Annualized toggle.  Click to show Annualized values, i.e., Monthly values times twelve.
* transaction table supports sorting and filtering for any field …

#### Balance Sheet

##### Features
* Time series of cumulative value of all Assets, Liabilities, and Equity.  Grouped by Year, Quarter, or Month.
* A transaction table showing all transactions, and cumulative total, for selected accounts up to the point of selection.

# Known Bugs

# If no era file is present, clicking the Era selector will cause an error.
