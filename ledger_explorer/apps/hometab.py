import dash_core_components as dcc
import dash_html_components as html

layout = html.Div(
    className="layout_box presentation",
    children=[
        dcc.Markdown('''

# Ledger Explorer (ALPHA RELEASE)

Quickly navigate through flow and balance charts as line charts, drill down into account rollups, and get from annual totals to individual records in a register all on one page.  Import CSV from files or URLs, match the columns, handling tens of thousands of records quickly.  Chart any data that comprises individual transactions, each with a time, amount, and category/account.  

## Try an example

* [Personal accounting sample data (Gnucash format)](https://ledge.uprightconsulting.com/ex/?transu=https://ledge.uprightconsulting.com/s/sample_transaction_data.csv&atreeu=https://ledge.uprightconsulting.com/s/sample_transaction_account_tree.csv&etreeu=https://ledge.uprightconsulting.com/s/sample_transaction_account_eras.csv&init_time_res=5)  # NOQA
   * Loads data from a [sample Gnucash export file](https://ledge.uprightconsulting.com/s/sample_transaction_data.csv)
   * ![Screenshot](/assets/cash_flow_1.jpg)

* [Greenhouse Gas emissions by country over time](https://ledge.uprightconsulting.com/ex?transu=https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/CO2%20emissions%20(Aggregate%20dataset%20(2020))/CO2%20emissions%20(Aggregate%20dataset%20(2020)).csv&atreeu=https://ledge.uprightconsulting.com/s/co2_test_tree_parent.csv)
   * loads data directly from external source [Our World in Data](value="https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/CO2%20emissions%20(Aggregate%20dataset%20(2020))/CO2%20emissions%20(Aggregate%20dataset%20(2020)).csv)
   * [Custom account tree](https://ledge.uprightconsulting.com/s/co2_test_tree_parent.csv)

*[US Federal Budget Data FORTHCOMING

* [To load your own data, click "Files"](/?tab=ds)

### Disclaimers, Privacy, and such
Ledger Explorer is a Free Software product, built on Plotly Dash and other free/open source software.  This site is provided free of cost, with no warranty.  This product contains no tracking or sponsorship.  Web traffic data, such as your IP address and the time and address of the pages you access on this site, are retained permanently.  No other information is collected or retained.  Reloading your browser should remove all data from your browser and this site's server.  Data that you upload to the site is probably not completely insecure, and nobody looks at it.  But there's really nothing stopping the site host, or any competent intruder, from viewing your data.  So please don't upload anything sensitive.  If you really want to use this software with sensitive data, you may have more privacy if you downloading and install it on your own computer.

  © 2020 Joel Aufrecht.
## More information
* [Run it yourself](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/INSTALL.md)
* [Instructions](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/USAGE.md)
* [Ledger Explorer on Github](https://github.com/saufrecht/ledger-explorer/)''')
    ]
)
