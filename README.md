# ledger-explorer
Navigate any hierarchical ledger graphically, all the way down to individual transactions.

![Screenshot](https://github.com/saufrecht/ledger-explorer/ledger_explorer.png | width=600)

# Installation

## get the code

`git clone https://github.com/saufrecht/ledger-explorer.git`
`cd ledger-explorer`

## Make a virtual environment

`python3 -m venv ~/.venv_le`

`source ~/.venv_le/bin/activate`

`pip install -r requirements.txt`

### Export data from Gnucash

1. `File` → `Export` → `Export Transactions to CSV …`
2. `Next`
3. `Select All`, `Next`
4. Enter filename, for example, `transactions.csv`

### Set up local webserver
In Ubuntu, `sudo apt install nginx` should be enough.
TODO: permissions to allow publishing files as user

#### Publish style sheet to local webserver
`sudo cp dash_layout.css /var/www/html`

#### Publish transaction data to local webserver
`sudo cp sample_data.csv /var/www/html/transactions.csv`

### Run program
1. `python ledger_explorer.py`
1. Browse to http://localhost:8050

# Known Bugs
yes
