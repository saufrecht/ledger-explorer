from urllib.parse import quote

from dash import dcc, html

owid_co2_url = quote(
    "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/CO2%20emissions%20(Aggregate%20dataset%20(2020))/CO2%20emissions%20(Aggregate%20dataset%20(2020)).csv"
)  # NOQA


layout = html.Div(
    className="layout_box presentation",
    children=[
        dcc.Markdown(
            f"""# Ledger Explorer (ALPHA RELEASE)

Quickly navigate through flow and balance charts as line charts, drill down into account rollups, and get from annual totals to individual records in a register all on one page.  Import CSV from files or URLs, match the columns, handling tens of thousands of records quickly.  Chart any data that comprises individual transactions, each with a time, amount, and category/account.

## Try an example

* **Example #1:** [Personal accounting sample data (Gnucash format)](/pe/?transu=https://ledge.uprightconsulting.com/s/sample_transaction_data.csv&atreeu=https://ledge.uprightconsulting.com/s/sample_transaction_account_tree.csv&erasu=https://ledge.uprightconsulting.com/s/sample_transaction_eras.csv&init_time_res=quarter&pe_roots=Income,Expenses&cu_roots=Assets,Liabilities,Equity)
   * Loads data from a [sample Gnucash export file](https://ledge.uprightconsulting.com/s/sample_transaction_data.csv)
   * ![Screenshot](/assets/screenshot_cash_flow_transdata.png)

* **Example #2:** [Greenhouse Gas emissions by country over time](/bs/?transu={owid_co2_url}&atreeu=https://ledge.uprightconsulting.com/s/co2_test_tree_full.csv&account_label=entity&amount_label=Annual%20CO2%20emissions&date_label=year&desc_label=entity&fan_label=entity&init_time_res=year&init_time_span=annual&ds_data_title=Annual_CO₂_Emissions&ds_label=Our%20World%20In%20Data:%20CO₂&cu_label=Cumulative&pe_label=Annual&ex_roots=root&bs_roots=root&unit=Mt·CO₂)
   * loads data directly from external source [Our World in Data](https://ourworldindata.org/co2-and-other-greenhouse-gas-emissions)
   * [Custom account tree](https://ledge.uprightconsulting.com/s/co2_test_tree_parent.csv)
   * ![Screenshot](/assets/screenshot_balance_sheet_co2data.png)

## Try it yourself

* Try your own data: [click "Files"](/ds/)
  * [Instructions](https://github.com/saufrecht/ledger-explorer/blob/master/docs/USAGE.md)
* You can also [run it on your own computer](https://github.com/saufrecht/ledger-explorer/blob/master/docs/INSTALL.md)

### About, Privacy, and Security
Ledger Explorer is a Free Software product and service, built with [Dash](https://plotly.com/dash/) and other free/open source software.  Ledger Explorer is provided free of cost, with no warranty.  It collects no personal data, uses no tracking technologies, and has no commercial relationships.  It retains normal web traffic logs, which include your [IP address](https://ssd.eff.org/en/glossary/ip-address) and the time and address of the pages you access on this site.  No other information is collected or retained.  Reloading your browser should remove all data from your browser and this site's server.  The data you provide to the site in order to use its features is not inspected or retained, but its privacy and security cannot be guaranteed, so please don't provide anything sensitive.

© 2020 Joel Aufrecht.
## More information
* [Ledger Explorer on Github](https://github.com/saufrecht/ledger-explorer/)
* [Upright Consulting](https://uprightconsulting.com)"""
        )
    ],
)
