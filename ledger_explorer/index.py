import json
import logging

import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate


from app import app
from apps import balance_sheet, data_source, explorer, settings, hometab

server = app.server

app.title = 'Ledger Explorer'

dummy_layout = html.Div(children=[
    html.Div(id='trans_parsed_meta'),
    html.Div(id='atree_parsed_meta'),
    html.Div(id='eras_parsed_meta'),
    html.Div(id='trans_status'),
    html.Div(id='atree_status'),
    html.Div(id='eras_status'),
    html.Div(id='trans_filename'),
])

EX_LABEL = 'Cash Flow'
BS_LABEL = 'Balance Sheet'
DS_LABEL = 'Files'

app.layout = html.Div(
    id='page-content',
    className='tabs_container',
    children=[
        html.Div(id='data_store',
                 children='',
                 className='hidden'),
        html.Div(id='control_store',
                 className='hidden'),
        html.Div(id='trans_file_store',
                 className='hidden'),
        html.Div(id='atree_file_store',
                 className='hidden'),
        html.Div(id='eras_file_store',
                 className='hidden'),
        html.Div(id='loading_workaround',
                 className='hidden',
                 children=dummy_layout),
        html.Div(className='custom_tabbar_container',
                 children=[
                     dcc.Tabs(id='tabs',
                              value='le',
                              vertical=True,
                              children=[dcc.Tab(label='Home', id='le_tab', value='le'),
                                        dcc.Tab(label=EX_LABEL, id='ex_tab', value='ex'),
                                        dcc.Tab(label=BS_LABEL, id='bs_tab', value='bs'),
                                        dcc.Tab(label='Settings', id='se_tab', value='se'),
                                        dcc.Tab(label=DS_LABEL, id='ds_tab', value='ds')]),
                     html.Div(id='files_status',
                              children=[])]),
        html.Div(id='tab-content',
                 className='tab_content'),
    ])


@app.callback([Output('tab-content', 'children')],
              [Input('tabs', 'value')])
def change_tab(selected_tab: str):
    if selected_tab == 'bs':
        return [balance_sheet.layout]
    elif selected_tab == 'ex':
        return [explorer.layout]
    elif selected_tab == 'se':
        return [settings.layout]
    elif selected_tab == 'ds':
        return [data_source.layout]
    else:
        return [hometab.layout]


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

    if not ex_label:
        ex_label = EX_LABEL
    if not ds_label:
        ds_label = DS_LABEL
    if not bs_label:
        bs_label = BS_LABEL

    return [ex_label, bs_label, ds_label]


if __name__ == '__main__':
    # logging.basicConfig(
    #     level=logging.DEBUG,
    #     format='%(asctime)s %(levelname)-8s %(message)s',
    #     datefmt='%Y-%m-%d %H:%M:%S %z')
    app.config['suppress_callback_exceptions'] = True
    app.run_server(debug=True, host='0.0.0.0', port='8081')


if __name__ != '__main__':
    # Get logging to flow all the way to gunicorn.
    # from https://trstringer.com/logging-flask-gunicorn-the-manageable-way/
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    external_stylesheets = ['https://ledge.uprightconsulting.com/s/dash_layout.css']
