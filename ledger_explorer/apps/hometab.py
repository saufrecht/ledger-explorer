import dash_core_components as dcc
import dash_html_components as html

layout = html.Div(
    className="layout_box presentation",
    children=[
        dcc.Markdown('''

# Ledger Explorer

Quick navigation through a graphical view of aggregate data in a pie chart or bar chart, representing tens of thousands of records, to a list of specific transactions. 

## Try an example

* [Personal accounting sample data (Gnucash format)](/?tab=ex&trans=/s/sample_transaction_data.csv)

  * ![Screenshot](/assets/cash_flow_1.jpg)

* [Greenhouse Gas emissions by country over time](/?tab=ex&trans=/s/sample_transaction_data.csv)

* [US Federal Budget Data](/?tab=ex&trans=/s/sample_transaction_data.csv)

* [To load your own data, click "Files"](/?tab=ds)

### Disclaimers, Privacy, and such
Ledger Explorer is a Free Software product, built on Plotly Dash and other free/open source software.  This site is provided free of cost, with no warranty.  This product contains no tracking or sponsorship.  Web traffic data, such as your IP address and the time and address of the pages you access on this site, are retained permanently.  No other information is collected or retained.  Reloading your browser should remove all data from your browser and this site's server.  Data that you upload to the site is probably not completely insecure, and nobody looks at it.  But there's really nothing stopping the site host, or any competent intruder, from viewing your data.  So please don't upload anything sensitive.  If you really want to use this software with sensitive data, you may have more privacy if you downloading and install it on your own computer.

  © 2020 Joel Aufrecht.
## More information
* [Run it yourself](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/INSTALL.md)
* [Instructions](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/USAGE.md)
* [Ledger Explorer on Github](https://github.com/saufrecht/ledger-explorer/)

'''
    )])
