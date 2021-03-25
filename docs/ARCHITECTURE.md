# Page and code layout

## index.py
Everything starts with ```index.py``` (all paths start from ```ledger-explorer/ledgex``` in the git structure unless otherwise noted), which does three things:

### Start the webserver and Dash application

```server = app.server``` points to ```app.py```, which creates the Dash application that everything runs in.  If ```index.py``` is run as a python module (```python ledegx/index.py```), this will invoke a Flask app which will run as a webserver.  If run from gunicorn (or other python app server), it will … probably still run as Flask, I guess?, but then that will be wrapped by the application server.

### Define the page and shared data

```app.layout``` is the parent for everything visible on the screen, as well as for any non-displayed information that needs to be available on all tabs, which is everything with ```className="hidden"```.

### Handle the GUI fundament

The callbacks cover:
1. parsing and applying any URL parameters.
1. Managing switching between tabs
1. (Re)generating the reporting data whenever any of the data inputs change.  Putting this in the file that contains the entire tab structure allows incoming URLs to go directly to a specific tab view, with the data and parameters specified in the URL.  It also causes lots of extra processing, so TODO it would benefit from being tuned to be much more conservative about running.


## custom classes and other code

All shared code in the application lives in the other files in the base code directory.  Worth noting:

1. The ```Datastore``` class is used to get data in and out of the special datastore persistent variable, which is used to share data easily between different Dash callbacks and layouts.

## Tabs
Each tab in the GUI is one-to-one with a file in ```/tabs```.  These hold the tab-specific layout and the callbacks for any controls in that layout.  The size of code in these files should be kept as small as possible (by moving it to classes) because it's much easier to test gui-less code.  Each tab has a two-letter ID, used as a quasi-namespace to keep each tab's stuff separate.  That is, all callback names on that tab should start with ```??_```, as well as any layout objects defined only on that tab.


# Data Structure

## Trans, ATree, and Eras
The three main custom data structures for the application.  Each of them can be specified as an external file.
1. **Trans** subclasses ```pandas.DataFrame```, and is a frame (table) of all individual transactions.  This is required; it's the source of all data to be shown.  The master copy in the datastore should stay intact unless the input parameters change.  For each use of the data, try to shrink it (by filtering or grouping) as early as the GUI path allows, to improve performance.  
1. **ATree**, short for "Account Tree", subclasses ```treelib.Tree```.  This is the hierarchical structure of accounts used for grouping and rollup.  It can be derived from appropriate transaction data.  When provided as a second input file, it allows custom recategorizing, re-structuring, and account-level filtering of the source data without requiring changes to the source transaction file.
1. **Eras** is optional data defining custom reporting periods.


## Going from parsed data to graphs
Each tab has a primary graph that always reloads on tab activation, pulls data from the data store for display.  Guarantee this by adding a ```??_dummy``` input to the callback that outputs the primary graph, where ```??``` is the tab prefix.  All other graphs on the tab could have an Input that is an Output of the primary graph—in this arrangement, any change to the primary graph updates everything else on the page.  Or, an Output from the primary graph could go to an Input of a secondary graph, which in turn would Output to an input of a tertiary graph, and so forth.


## Import
Ledger Explorer imports trans, atree, and eras files as csv data.  This can be in the form of uploaded files.  More interestingly, Dash can pull from URLs, so a custom configuration that pulls from a third-party data source and manipulates and displays the data can itself be saved as a URL.  So party A (you) can make a link to your Ledger Explorer server that any random party B can click on, which will pull fresh data from party C and automatically parse and display it.


## Export
The only form of export in Ledger Explorer is creating a permalink, which saves all current parameters into a new URL.