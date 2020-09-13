import logging

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output

from app import app
from apps import balance_sheet, data_source, explorer, settings


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
                 value='ds',
                 className='custom-tabs-container',
                 children=[dcc.Tab(label='Data Source', id='ds_tab', value='ds'),
                           dcc.Tab(label='Flow', id='ex_tab', value='ex'),
                           dcc.Tab(label='Balance Sheet', id='bs_tab', value='bs'),
                           dcc.Tab(label='Settings', id='se_tab', value='se')]
                 ),
        html.Div(id='tab-content'),
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


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S %z')
    app.run_server(debug=True, host='0.0.0.0')
