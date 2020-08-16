import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import logging

from app import app
from apps import balance_sheet, cashflow


app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    logging.debug('url callback')
    if pathname == 'balance_sheet':
        return balance_sheet.layout
    else:
        return cashflow.layout


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %z')
    app.run_server(debug=True, host='0.0.0.0')
