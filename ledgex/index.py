import json
import logging
from urllib.parse import parse_qs, urlencode

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from ledgex.app import app
from ledgex.apps import balance_sheet, data_source, explorer, hometab
from ledgex.loading import LoadError, convert_raw_data, load_input_file
from ledgex.params import CONST, Params
from ledgex.utils import preventupdate_if_empty

server = app.server

app.title = "Ledger Explorer"


app.layout = html.Div(
    id="page-content",
    className="tabs_container",
    children=[
        html.Div(
            className="custom_tabbar_container",
            children=[
                dcc.Tabs(
                    id="tabs",
                    value="le",
                    vertical=True,
                    children=[
                        dcc.Tab(label=CONST["ex_label"], id="ex_tab", value="ex"),
                        dcc.Tab(label=CONST["bs_label"], id="bs_tab", value="bs"),
                        dcc.Tab(label=CONST["ds_label"], id="ds_tab", value="ds"),
                        dcc.Tab(label="About", id="le_tab", value="le"),
                    ],
                ),
                html.Div(
                    id="infodex",
                    children=[
                        html.Div(id="files_status", children=[]),
                        dcc.Markdown(CONST["bug_report_md"]),
                        dcc.Location(id="url_reader", refresh=False),
                        dcc.Location(id="url_writer", refresh=False),
                        html.Div(id="ui_inputs", className="hidden"),
                        html.Div(id="api_inputs", className="hidden"),
                        html.Div(id="ex_tab_trigger", className="hidden"),
                        html.Div(id="ui_trans_node", className="hidden"),
                        html.Div(id="ui_atree_node", className="hidden"),
                        html.Div(id="ui_eras_node", className="hidden"),
                        html.Div(id="api_trans_node", className="hidden"),
                        html.Div(id="api_atree_node", className="hidden"),
                        html.Div(id="api_eras_node", className="hidden"),
                        html.Div(id="data_store", className="hidden"),
                        html.Div(id="param_store", className="hidden"),
                        html.Div(id="tab_store", className="hidden"),
                        html.Div(id="tab_node", className="hidden"),
                    ],
                ),
            ],
        ),
        html.Div(id="tab_content", className="tab_content"),
    ],
)


app.validation_layout = html.Div(
    children=[
        app.layout,
        balance_sheet.layout,
        data_source.layout,
        explorer.layout,
        hometab.layout,
    ]
)


@app.callback([Output("tabs", "value")], [Input("url_reader", "pathname")])
def parse_url_path(path: str):
    """Handle the path portion of the URL by which the page was reached.
    If the URL path comprises a two-character string, set the tabs value,
    which will in turn trigger a switching of tabs"""
    if isinstance(path, str):
        tab = path.strip("/")
        if len(tab) == 2:
            return [tab]
    raise PreventUpdate


@app.callback(
    [Output("tab_content", "children"),
     Output("tab_node", "children")],
    [Input("tabs", "value")],
)
def change_tab(clicked_tab: str) -> list:
    """From a click on the tabbar, or a change
    from the url, change the currently shown tab."""
    if clicked_tab == "bs":
        return [balance_sheet.layout, "bs"]
    elif clicked_tab == "ex":
        return [explorer.layout, "ex"]
    elif clicked_tab == "ds":
        return [data_source.layout, "ds"]
    elif clicked_tab == "le":
        return [hometab.layout, "le"]
    else:
        app.logger.warning(
            f"attempted to change tab to {clicked_tab}, which is not a valid choice."
        )
    raise PreventUpdate


@app.callback(
    [Output("ex_tab", "label"),
     Output("bs_tab", "label"),
     Output("ds_tab", "label")],
    [Input("tab_store", "children")],
)
def relabel_tab(tab_store: str):
    """ If the setttings have any renaming for tab labels, apply them """
    preventupdate_if_empty(tab_store)
    params = Params(**json.loads(tab_store))
    params.fill_defaults()

    return [params.ex_label, params.bs_label, params.ds_label]


@app.callback(
    [Output("api_trans_node", "children"),
     Output("api_atree_node", "children"),
     Output("api_eras_node", "children"),
     Output("api_inputs", "children")],
    [Input("url_reader", "search")],
)
def parse_url_search(search: str):
    preventupdate_if_empty(search)
    """ Process the search portion of any input URL and store it to an
    intermediate location.  If one or more data source URLs are
    provided via the input URL, load them here in the index.
    Otherwise, incoming links that provide data source URLs wouldn't
    work until after the user browsed to the Data Source tab.  """

    search = search.lstrip("?")
    if not search or not isinstance(search, str) or not len(search) > 0:
        raise PreventUpdate
    inputs = parse_qs(search, keep_blank_values=True, max_num_fields=50)  # 50 is arbitrary, for DoS prevention
    trans_j = None
    atree_j = None
    eras_j = None
    api_input_j = json.dumps(inputs)
    trans_input = inputs.get("transu", None)
    if trans_input:
        filename, t_data, text = load_input_file(url=trans_input[0])
        if len(t_data) > 0:
            trans_j = t_data.to_json()

    atree_input = inputs.get("atreeu", None)
    if atree_input:
        filename, a_data, text = load_input_file(url=atree_input[0])
        if len(t_data) > 0:
            atree_j = t_data.to_json()

    eras_input = inputs.get("erasu", None)
    if eras_input:
        filename, a_data, text = load_input_file(url=eras_input[0])
        if len(t_data) > 0:
            eras_j = t_data.to_json()

    return [trans_j, atree_j, eras_j, api_input_j]

    #     try:
    #         input_list: list = inputs.get(key, [])
    #         input_value: str = input_list[0]
    #         if input_value and len(input_value) > 0 and isinstance(input_value, str):
    #             c_data[key] = input_value
    #     except (IndexError, TypeError):
    #         pass


@app.callback(
    [
        Output("data_store", "children"),
        Output("param_store", "children"),
        Output("files_status", "children"),
        Output("ex_tab_trigger", "children"),
        Output("url_writer", "pathname"),
    ],
    [
        Input("ui_trans_node", "children"),
        Input("ui_atree_node", "children"),
        Input("ui_eras_node", "children"),
        Input("api_trans_node", "children"),
        Input("api_atree_node", "children"),
        Input("api_eras_node", "children"),
        Input("ui_inputs", "children"),
        Input("api_inputs", "children"),
        Input("tab_node", "children"),
    ],
)
def load_and_transform(
    ui_trans_node: str,
    ui_atree_node: str,
    ui_eras_node: str,
    api_trans_node: str,
    api_atree_node: str,
    api_eras_node: str,
    ui_inputs: str,
    api_inputs: str,
    tab_node: str,
):
    """When any of the parameters or input files changes, reload
    all the data and refresh the page url.
    The api_*_nodes will contain data loaded directly from the API (i.e.,
    from URL search parameters), and the ui_*_nodes will contain data
    loaded from the data_source tab, so ui should trump api.
    """
    ctx = dash.callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    else:
        trigger_id = None
    # look for UI input, then file upload, then url upload.  This
    # way, user uploads by file or url will override anything loaded
    # from the Ledger Explorer url.
    data: str = ""
    params_j: str = ""
    status: str = ""
    t_source: str = ""
    permalink: str = ""
    if trigger_id == "ui_trans_node":
        t_source = ui_trans_node
    elif trigger_id == "api_trans_node":
        t_source = api_trans_node
    elif ui_trans_node and len(ui_trans_node) > 0:
        t_source = ui_trans_node
    elif api_trans_node and len(api_trans_node) > 0:
        t_source = api_trans_node
    else:
        status = "No transaction data loaded."
    if ui_inputs and len(ui_inputs) > 0:
        ui_source = json.loads(ui_inputs)
    else:
        ui_source = {}

    # ui_source is for stuff the user has explicitly input, so it may
    # be very sparse. params is for the full set of possible
    # parameters, with defaults if necessary. Be careful not to reify
    # the defaults by putting them into the UI or the URL
    params = Params.from_dict(ui_source)
    params.fill_defaults()
    params_j = params.to_json()

    if t_source and len(t_source) > 0:
        try:
            trans_data = pd.read_json(t_source)
            atree_data: pd.DataFrame = pd.DataFrame()
            a_source = None
            if trigger_id == "ui_atree_node":
                a_source = ui_atree_node
            elif trigger_id == "api_atree_node":
                a_source = api_atree_node
            elif ui_atree_node and len(ui_atree_node) > 0:
                a_source = ui_atree_node
            elif api_atree_node and len(api_atree_node) > 0:
                a_source = api_atree_node
            if a_source:
                atree_data = pd.read_json(a_source)
            eras_data: pd.DataFrame = pd.DataFrame()
            e_source = None
            if trigger_id == "ui_eras_node":
                e_source = ui_eras_node
            elif trigger_id == "api_eras_node":
                e_source = api_eras_node
            elif ui_eras_node and len(ui_eras_node) > 0:
                e_source = ui_eras_node
            elif api_eras_node and len(api_eras_node) > 0:
                e_source = api_eras_node
            if e_source:
                eras_data = pd.read_json(e_source)
            trans, atree, eras = convert_raw_data(
                trans_data, atree_data, eras_data, params
            )
            data = json.dumps(
                {
                    "trans": trans.to_json(),
                    "eras": eras.to_json(),
                }
            )
            # Generate status info.  TODO: clean up this hack with a Jinja2 template, or at least another function
            status = html.Div(
                children=[
                    f"{len(trans)} transactions, {len(atree)} accounts, {len(eras)} reporting eras"
                ]
            )
        except LoadError as LE:
            status = f"Error loading transaction data: {LE.message}"

    if tab_node:
        permalink = f'/{tab_node}/'
    if ui_source:
        permalink = f'{permalink}?{urlencode(ui_source)}'
    return [data, params_j, status, 'True', permalink]


if __name__ == "__main__":
    app.config["suppress_callback_exceptions"] = True
    app.run_server(debug=True, host="0.0.0.0", port="8081")
else:
    # Logging flows all the way to gunicorn.
    # (from https://trstringer.com/logging-flask-gunicorn-the-manageable-way/)
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    external_stylesheets = ["https://ledge.uprightconsulting.com/s/dash_layout.css"]

#TODO: daily and weekly
#TODO: make the tab labels work
#TODO: change the $

