# Local Development Server

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
2. `.\path\to\myenv\Scripts\activate`

### Install prerequisite Python modules

`pip install -r docs/requirements.txt`

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


# Production Server (Linux)
A production-ready setup, using Nginx and GUnicorn.  As above for development server, except:

## Install server software

1. `pip install gunicorn flask`


