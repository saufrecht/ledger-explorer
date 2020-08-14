import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import logging

from app import app
from apps import balance_sheet, cashflow
import callbacks
import layouts



#######################################################################
# Load Data
#######################################################################

# this could come from a URL; simpler now to get from a local file
# crash if the load fails, as nothing is going to work



app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content')
])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == 'balance_sheet':
        return balance_sheet.layout(**kwargs)
    else:
        return cashflow.layout()


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
