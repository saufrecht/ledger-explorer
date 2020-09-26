import dash_core_components as dcc
import dash_html_components as html
from urllib.parse import quote


owid_co2_url = quote('https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/CO2%20emissions%20(Aggregate%20dataset%20(2020))/CO2%20emissions%20(Aggregate%20dataset%20(2020)).csv')


layout = html.Div(
    className="layout_box presentation",
    children=[
        dcc.Markdown(f'''# Ledger Explorer (ALPHA RELEASE)

Quickly navigate through flow and balance charts as line charts, drill down into account rollups, and get from annual totals to individual records in a register all on one page.  Import CSV from files or URLs, match the columns, handling tens of thousands of records quickly.  Chart any data that comprises individual transactions, each with a time, amount, and category/account.

## Try an example

* [Personal accounting sample data (Gnucash format)](/ex/?transu=https://ledge.uprightconsulting.com/s/sample_transaction_data.csv&atreeu=https://ledge.uprightconsulting.com/s/sample_transaction_account_tree.csv&etreeu=https://ledge.uprightconsulting.com/s/sample_transaction_eras.csv&init_time_res=5&ex_account_filter=('Income','Expenses')&bs_account_filter=('Assets','Liabilities','Equity'))
   * Loads data from a [sample Gnucash export file](https://ledge.uprightconsulting.com/s/sample_transaction_data.csv)
   * ![Screenshot](/assets/cash_flow_1.jpg)

* [Greenhouse Gas emissions by country over time](/ex/?transu={owid_co2_url}&atreeu=https://ledge.uprightconsulting.com/s/co2_test_tree_parent.csv&account_label=entity&amount_label=Annual%20CO2%20emissions&date_label=year&desc_label=entity&fan_label=entity&init_time_res=2)
   * loads data directly from external source [Our World in Data]({owid_co2_url})
   * [Custom account tree](https://ledge.uprightconsulting.com/s/co2_test_tree_parent.csv)
   * ![Screenshot](/assets/co2_1.jpg)

## Try it yourself

* Try your own data: [click "Files"](/ds/)
* [Instructions](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/USAGE.md)
* [Install and run it yourself](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/INSTALL.md)

### About, Privacy, and Security
Ledger Explorer is a Free Software product and service, built with [Dash](https://plotly.com/dash/) and other free/open source software.  Ledger Explorer is provided free of cost, with no warranty.  It collects no personal data, uses no tracking technologies, and has no commercial relationships.  It retains normal web traffic logs, which include your [IP address](https://ssd.eff.org/en/glossary/ip-address) and the time and address of the pages you access on this site.  No other information is collected or retained.  Reloading your browser should remove all data from your browser and this site's server.  The data you provide to the site in order to use its features is not inspected or retained, but its privacy and security cannot be guaranteed, so please don't provide anything sensitive.

  © 2020 Joel Aufrecht.
## More information
* [Ledger Explorer on Github](https://github.com/saufrecht/ledger-explorer/)
* [Upright Consulting](https://uprightconsulting.com)''')])
