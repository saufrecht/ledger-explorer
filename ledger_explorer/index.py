import logging

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from app import app
from apps import balance_sheet, cash_flow, data_source, explorer


app.layout = html.Div(
    id='page-content',
    className='page_content',
    children=[
        html.Div(id='data_store',
                 style={'display': 'none'}),
        dcc.Tabs(id='tabs',
                 value='ds',
                 className='custom-tabs-container',
                 children=[dcc.Tab(label='Data Source', id='ds_tab', value='ds'),
                           dcc.Tab(label='Explorer', id='ex_tab', value='ex'),
                           dcc.Tab(label='Cash Flow', id='cf_tab', value='cf'),
                           dcc.Tab(label='Balance Sheet', id='bs_tab', value='bs')]
                 ),
        html.Div(id='tab-content'),
    ])


@app.callback(Output('tab-content', 'children'),
              [Input('tabs', 'value')])
def change_tab(selected_tab: str):
    if selected_tab == 'bs':
        layout = balance_sheet.layout
    elif selected_tab == 'cf':
        layout = cash_flow.layout
    elif selected_tab == 'ex':
        layout = explorer.layout
    else:
        layout = data_source.layout

    return layout


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %z')
    app.run_server(debug=True, host='0.0.0.0')
