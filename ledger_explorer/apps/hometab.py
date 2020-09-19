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

### Privacy
No.  

## More information
* [Get your own copy](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/INSTALL.md)
* [Instructions](https://github.com/saufrecht/ledger-explorer/blob/gunicorn/docs/USAGE.md)
* [Ledger Explorer on Github](https://github.com/saufrecht/ledger-explorer/)

'''
    )])
