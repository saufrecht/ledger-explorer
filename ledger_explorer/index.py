import logging
import json

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from dash import Dash  # production only


from app import app
# production only: from app_prod import app
from apps import balance_sheet, data_source, explorer, settings

# production only:
# external_stylesheets = ['https://ledge.uprightconsulting.com/dash_layout.css']
# app = Dash(__name__, external_stylesheets=external_stylesheets)
# server = app.server

app.title = 'Ledger Explorer'

app.layout = html.Div(
    id='page-content',
    className='page_content',
    children=[
        html.Div(id='data_store',
                 children='',
                 className='hidden'),
        html.Div(id='control_store',
                 className='hidden'),
        dcc.Tabs(id='tabs',
                 value='ex',
                 className='custom-tabs-container',
                 children=[dcc.Tab(label='Cash Flow', id='ex_tab', value='ex'),
                           dcc.Tab(label='Balance Sheet', id='bs_tab', value='bs'),
                           dcc.Tab(label='Data Source', id='ds_tab', value='ds'),
                           dcc.Tab(label='Settings', id='se_tab', value='se')]
                 ),
        html.Div(id='tab-content'),
        html.Div(id='tab-debugging')
    ])


@app.callback(Output('tab-content', 'children'),
              [Input('tabs', 'value')])
def change_tab(selected_tab: str):
    if selected_tab == 'bs':
        layout = balance_sheet.layout
    elif selected_tab == 'ex':
        layout = explorer.layout
    elif selected_tab == 'se':
        layout = settings.layout
    else:
        layout = data_source.layout

    return layout


@app.callback([Output('ex_tab', 'label'),
               Output('bs_tab', 'label'),
               Output('ds_tab', 'label')],
              [Input('control_store', 'children')])
def relabel_tab(control_data: str):
    """ Update tab labels from settings"""
    if not control_data:
        raise PreventUpdate

    cd = json.loads(control_data)
    ex_label = cd.get('ex_label', None)
    bs_label = cd.get('bs_label', None)
    ds_label = cd.get('ds_label', None)
    return [ex_label, bs_label, ds_label]


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %z')
    app.run_server(debug=False, host='0.0.0.0')
