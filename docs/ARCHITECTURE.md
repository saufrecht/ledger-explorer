# Fundamental decisions

Several needs drive Ledger Explorer's design choices:

**As a data analyst, I graph data published on the internet, so that I can get new information with little time investment.**

  * detail: tabular data, CSV format, where each tuple includes a date, account, and amount.

**As an analyst of dynamic data, my charting tool refresh third-party data automatically, so that I always have current information automatically.**

**Analyzing data with thousands of records, I navigate between summations and individual records instantly, so that I can analyze at several levels of abstraction simultaneously.**

Therefore:
1. Ledger Explorer downloads data from URLs.
1. Ledger Explorer can perform rudimentary ETL, to match column names to required fields.
1. Ledger Explorer uses Plotly to generate and display dynamic charts and graphs in the browser
1. Ledger Explorer stores the complete transaction dataset in the browser
1. Ledger Explorer stores configuration as URL parameters, so that a report can be saved by bookmarking and shared by sending a URL.
1. A Ledger Explorer webserver performs data loading, modifies data as needed upstream from specific Plotly functions, and publishes the GUI as a Single-Page Application.

# Code structure

The root of the github filetree, by default ```ledger-explorer```, holds several configuration files.  It should **not** be served publically.

The ```/ledgex/``` directory holds all program code; this is the directory to publish on an application server.
The ```/tests/``` directory holds code and data required to automatically test the program code.
The ```/docs/``` directory holds documentation—written in Github Markdown—and related images.

## index.py
The entry point to code execution is ```index.py``` (all paths start from ```ledger-explorer/ledgex``` in the git structure unless otherwise noted).  It does three things:

### Start the webserver and Dash application

```server = app.server``` points to ```app.py```, which creates the Dash application that everything runs in.  If ```index.py``` is run as a python module (```python ledegx/index.py```), this will invoke a Flask app which will run as a webserver.  If run from gunicorn (or other python app server), it will … probably still run as Flask, I guess?, but then that will be wrapped by the application server.

### Define the page and shared data

```app.layout``` is the parent for everything visible on the screen, as well as for any non-displayed information that needs to be available on all tabs, which is everything with ```className="hidden"```.

### Handle GUI interactions, i.e., Dash callbacks, that exist on all tabs.

The callbacks cover:
1. parsing and applying any URL parameters.
1. Managing switching between tabs
1. (Re)generating the reporting data whenever any of the data inputs change.  Putting this in the file that contains the entire tab structure allows incoming URLs to go directly to a specific tab view, with the data and parameters specified in the URL.  It also causes lots of extra processing, so TODO it would benefit from being tuned to be much more conservative about running.


## Custom classes and other code

All shared code in the application lives in the other files in the base code directory.  Worth noting:

1. The ```Datastore``` class is used to get data in and out of the special datastore persistent variable, which is used to share data easily between different Dash callbacks and layouts.

## Tabs
Each tab in the GUI is one-to-one with a file in ```/tabs```.  These hold the tab-specific layout and the callbacks for any controls in that layout.  The size of code in these files should be kept as small as possible (by moving it to classes) because it's much easier to test gui-less code.  Each tab has a two-letter ID, used as a quasi-namespace to keep each tab's stuff separate.  That is, all callback names on that tab should start with ```??_```, as well as any layout objects defined only on that tab.


# Data Structure

## Trans, ATree, and Eras
The three main custom data structures for the application.  Each of them can be specified as an external file.
1. **Trans** subclasses ```pandas.DataFrame```, and is a frame (table) of all individual transactions.  This is required; it's the source of all data to be shown.  The master copy in the datastore should stay intact unless the input parameters change.  For each use of the data, try to shrink it (by filtering or grouping) as early as the GUI path allows, to improve performance.  
1. **ATree**, short for "Account Tree", subclasses ```treelib.Tree```.  This is the hierarchical structure of accounts used for grouping and rollup.  By default it is derived from parent relationships in the transaction data file: Gnucash provides a complete account path in each record.  If there is no parent information in transactions, every account will be a first-level node in the account tree.  An Atree source file, if provided, takes precedence over a derived tree.  This allows custom recategorizing, re-structuring, and account-level filtering of the source data without requiring changes to the source transaction file.
1. **Eras** is optional data defining custom reporting periods.


## Import
Ledger Explorer imports trans, atree, and eras csv files.  These can be uploaded, or provided as URLs.  This data is stored in the ```datastore``` object in ```index.py```, so that it is accessible to all callbacks on all tabs.

## Going from parsed data to graphs
Each tab has a primary graph that always reloads on tab activation, pulls data from the data store for display.  Guarantee this by adding a ```??_dummy``` input to the callback that outputs the primary graph, where ```??``` is the tab prefix.  The rest of the GUI elements could go in either a star or cascade design.  In a star, all other graphs on the tab have an Input that is an Output of the primary graph.  In this arrangement, any change to the primary graph updates everything else on the page.  In a cascade arrangement, every graph has an Input that connects to an Output of a graph closer to the primary, in an unbroken chain.  Either way, note that one Output can trigger Inputs in any number of callbacks.  These designs can be mixed, at peril of mass confusion.

## Export
The only form of export in Ledger Explorer is creating a permalink, which saves all current parameters into a new URL.