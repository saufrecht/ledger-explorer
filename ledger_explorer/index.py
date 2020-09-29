import json
import logging
from urllib.parse import parse_qs
import pandas as pd

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate


from app import app
from apps import balance_sheet, data_source, explorer, settings, hometab

from params import CONST, Params
from loading import LoadError, convert_raw_data, load_input_file


server = app.server

app.title = 'Ledger Explorer'


app.layout = html.Div(
    id='page-content',
    className='tabs_container',
    children=[
        dcc.Location(id='url_reader',
                     refresh=False),
        html.Div(id='control_node',
                 className='hidden'),
        html.Div(id='control_urlnode',
                 className='hidden'),
        html.Div(id='data_store',
                 className='hidden'),
        html.Div(id='control_store',
                 className='hidden'),
        html.Div(id='trans_file_node',
                 className='hidden'),
        html.Div(id='atree_file_node',
                 className='hidden'),
        html.Div(id='eras_file_node',
                 className='hidden'),
        html.Div(id='trans_urlfile_node',
                 className='hidden'),
        html.Div(id='atree_urlfile_node',
                 className='hidden'),
        html.Div(id='eras_urlfile_node',
                 className='hidden'),
        html.Div(id='tab_draw_trigger',
                 className='hidden'),
        html.Div(className='custom_tabbar_container',
                 children=[
                     dcc.Tabs(id='tabs',
                              value='le',
                              vertical=True,
                              children=[dcc.Tab(label='Home', id='le_tab', value='le'),
                                        dcc.Tab(label=CONST['ex_label'], id='ex_tab', value='ex'),
                                        dcc.Tab(label=CONST['bs_label'], id='bs_tab', value='bs'),
                                        dcc.Tab(label='Settings', id='se_tab', value='se'),
                                        dcc.Tab(label=CONST['ds_label'], id='ds_tab', value='ds')]),
                     html.Div(id='files_status',
                              children=[])]),
        html.Div(id='tab-content',
                 className='tab_content'),
    ])


app.validation_layout = html.Div(children=[
    app.layout,
    balance_sheet.layout,
    data_source.layout,
    explorer.layout,
    hometab.layout,
    settings.layout,
])


@app.callback([Output('tabs', 'value')],
              [Input('url_reader', 'pathname')])
def parse_url_path(path: str):
    """ IF the URL path comprises a two-character string, set the tabs value,
    which will trigger a switching of tabs """
    if isinstance(path, str):
        tab = path.strip('/')
        if len(tab) == 2:
            return [tab]

    raise PreventUpdate


@app.callback([Output('tab-content', 'children')],
              [Input('tabs', 'value')])
def change_tab(selected_tab: str):
    """ From a click on the tabbar, change the tab. """
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
    """ If the setttings have any renaming for tab labels, apply them """
    if not control_data:
        raise PreventUpdate

    cd = json.loads(control_data)
    ex_label = cd.get('ex_label', None)
    bs_label = cd.get('bs_label', None)
    ds_label = cd.get('ds_label', None)

    if not ex_label:
        ex_label = CONST['ex_label']
    if not ds_label:
        ds_label = CONST['ds_label']
    if not bs_label:
        bs_label = CONST['bs_label']

    return [ex_label, bs_label, ds_label]


@app.callback([Output('control_urlnode', 'children'),
               Output('trans_urlfile_node', 'children'),
               Output('atree_urlfile_node', 'children'),
               Output('eras_urlfile_node', 'children')],
              [Input('url_reader', 'search')])
def parse_url_search(search: str):
    """ Process the search portion of any input URL and store it to an intermediate location """
    if not search or not isinstance(search, str) or not len(search) > 0:
        raise PreventUpdate
    search = search.lstrip('?')
    inputs = parse_qs(search)

    c_data = {}
    for key, value in vars(Params()).items():
        try:
            input_list: list = inputs.get(key, [])
            input_value: str = input_list[0]
            if input_value and len(input_value) > 0 and isinstance(input_value, str):
                if key in ['ex_account_filter', 'bs_account_filter']:
                    input_value = Params.parse_account_string(input_value)
                c_data[key] = input_value
        except (IndexError, TypeError):
            pass
        except Exception as E:
            app.logger.warning(f'failed to parse url input key: {key}, value: {value}.  Error {E}')

    control = Params(**c_data).to_json()

    raw_trans = None
    trans_input = inputs.get('transu', None)
    if trans_input:
        try:
            transu = trans_input[0]
            if isinstance(transu, str):
                filename, t_data, text = load_input_file(None, transu, None)
                if len(t_data) > 0:
                    raw_trans = t_data.to_json()
        except Exception as E:
            app.logger.warning(f'Failed to load {transu} because {E}')

    raw_atree = None
    atree_input = inputs.get('atreeu', None)
    if atree_input:
        atreeu = atree_input[0]
        if isinstance(atreeu, str):
            filename, t_data, text = load_input_file(None, atreeu, None)
            if len(t_data) > 0:
                raw_atree = t_data.to_json()

    raw_eras = None
    eras_input = inputs.get('erasu', None)
    if eras_input:
        erasu = eras_input[0]
        if isinstance(erasu, str):
            filename, t_data, text = load_input_file(None, erasu, None)
            if len(t_data) > 0:
                raw_eras = t_data.to_json()

    return [control, raw_trans, raw_atree, raw_eras]


@app.callback([Output('data_store', 'children'),
               Output('control_store', 'children'),
               Output('files_status', 'children'),
               Output('tab_draw_trigger', 'children')],
              [Input('trans_file_node', 'children'),
               Input('atree_file_node', 'children'),
               Input('eras_file_node', 'children'),
               Input('trans_urlfile_node', 'children'),
               Input('atree_urlfile_node', 'children'),
               Input('eras_urlfile_node', 'children')],
              state=[State('control_urlnode', 'children'),
                     State('control_node', 'children')])
def load_and_transform(trans_file_node: str,
                       atree_file_node: str,
                       eras_file_node: str,
                       trans_urlfile_node: str,
                       atree_urlfile_node: str,
                       eras_urlfile_node: str,
                       control_urlnode: str,
                       control_node: str):
    """When any of the input files changes in interim storage, reload all
    the data.  Because control store is a state input, the control
    data has to be loaded before the files to have an effect; changing
    the control data after loading will not re-trigger this.  it is implemented this way
    because control data is already an Input for something else.  If that
    turns out to be annoying, split the control_store into a params
    portion and a tab-name portion?

    """
    ctx = dash.callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    else:
        trigger_id = None
    # look for fresh input, then file upload, then url upload.  This
    # way, user uploads by file or url will override anything loaded
    # from the ledger_explorer url.

    data: str = ''
    controls: Params = None
    trigger: bool = False
    status: str = ''
    t_source: str = ''
    if trigger_id == 'trans_file_node':
        t_source = trans_file_node
    elif trigger_id == 'trans_urlfile_node':
        t_source = trans_urlfile_node
    elif trans_file_node and len(trans_file_node) > 0:
        t_source = trans_file_node
    elif trans_urlfile_node and len(trans_urlfile_node) > 0:
        t_source = trans_urlfile_node
    else:
        status = 'No transaction data loaded.'

    if t_source and len(t_source) > 0:
        try:
            trans_data = pd.read_json(t_source)
            atree_data: pd.DataFrame = pd.DataFrame()
            a_source = None
            if trigger_id == 'atree_file_node':
                a_source = atree_file_node
            elif trigger_id == 'atree_urlfile_node':
                a_source = atree_urlfile_node
            elif atree_file_node and len(atree_file_node) > 0:
                a_source = atree_file_node
            elif atree_urlfile_node and len(atree_urlfile_node) > 0:
                a_source = atree_urlfile_node
            if a_source:
                atree_data = pd.read_json(a_source)

            eras_data: pd.DataFrame = pd.DataFrame()
            e_source = None
            if trigger_id == 'eras_file_node':
                e_source = eras_file_node
            elif trigger_id == 'eras_urlfile_node':
                e_source = eras_urlfile_node
            elif eras_file_node and len(eras_file_node) > 0:
                e_source = eras_file_node
            elif eras_urlfile_node and len(eras_urlfile_node) > 0:
                e_source = eras_urlfile_node
            if e_source:
                eras_data = pd.read_json(e_source)

            if control_node and len(control_node) > 0:
                c_source = json.loads(control_node)
            elif control_urlnode and len(control_urlnode) > 0:
                c_source = json.loads(control_urlnode)
            else:
                c_source = None

            controls = Params(**c_source)
            trans, atree, eras = convert_raw_data(trans_data, atree_data, eras_data, controls)

            data = json.dumps({'trans': trans.to_json(),
                               'eras': eras.to_json()})
            controls = controls.to_json()

            # Generate status info.  TODO: clean up this hack with a Jinja2 template, or at least another function
            status = f'{len(trans)} transactions, {len(atree)} accounts, {len(eras)} reporting eras.'
            trigger = True
        except LoadError as LE:
            status = f'Error loading transaction data: {LE.message}'

    return [data, controls, status, trigger]


if __name__ == '__main__':
    # logging.basicConfig(
    #     level=logging.DEBUG,
    #     format='%(asctime)s %(levelname)-8s %(message)s',
    #     datefmt='%Y-%m-%d %H:%M:%S %z')
    app.config['suppress_callback_exceptions'] = True
    app.run_server(debug=True, host='0.0.0.0', port='8081')


if __name__ != '__main__':
    # Logging flows all the way to gunicorn.
    # (from https://trstringer.com/logging-flask-gunicorn-the-manageable-way/)
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    external_stylesheets = ['https://ledge.uprightconsulting.com/s/dash_layout.css']
