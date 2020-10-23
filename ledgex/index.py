import json
import logging
from urllib.parse import parse_qs

import dash
import dash_core_components as dcc
import dash_html_components as html
import pandas as pd
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

from ledgex.app import app
from ledgex.apps import balance_sheet, data_source, explorer, hometab
from ledgex.loading import LoadError, convert_raw_data, load_input_file
from ledgex.params import CONST, Params
from ledgex.utils import require_or_raise

server = app.server

app.title = "Ledger Explorer"


app.layout = html.Div(
    id="page-content",
    className="tabs_container",
    children=[
        dcc.Location(id="url_reader", refresh=False),
        html.Div(id="change_tabs_node", className="hidden"),
        html.Div(id="param_node", className="hidden"),
        html.Div(id="param_urlnode", className="hidden"),
        html.Div(id="data_store", className="hidden"),
        html.Div(id="param_store", className="hidden"),
        html.Div(id="param_store_for_tab_labels", className="hidden"),
        html.Div(id="ex_tab_trigger", className="hidden"),
        html.Div(id="trans_file_node", className="hidden"),
        html.Div(id="atree_file_node", className="hidden"),
        html.Div(id="eras_file_node", className="hidden"),
        html.Div(id="trans_urlfile_node", className="hidden"),
        html.Div(id="atree_urlfile_node", className="hidden"),
        html.Div(id="eras_urlfile_node", className="hidden"),
        html.Div(id="tab_draw_trigger", className="hidden"),
        html.Div(
            className="custom_tabbar_container",
            children=[
                dcc.Tabs(
                    id="tabs",
                    value="le",
                    vertical=True,
                    children=[
                        dcc.Tab(label="Home", id="le_tab", value="le"),
                        dcc.Tab(label=CONST["ex_label"], id="ex_tab", value="ex"),
                        dcc.Tab(label=CONST["bs_label"], id="bs_tab", value="bs"),
                        dcc.Tab(label=CONST["ds_label"], id="ds_tab", value="ds"),
                    ],
                ),
                html.Div(id="files_status", children=[]),
                html.Div(
                    id="infodex",
                    children=[
                        dcc.Markdown(CONST["bug_report_md"]),
                    ],
                ),
            ],
        ),
        html.Div(id="tab-content", className="tab_content"),
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
    [Output("tab-content", "children")],
    [Input("tabs", "value"), Input("change_tabs_node", "children")],
)
def change_tab(clicked_tab: str, node_tab: str) -> list:
    """From a click on the tabbar, or a change
    in the intermediate node, change the currently shown tab."""

    desired_tab = "le"  # default to home tab
    ctx = dash.callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id == "tabs":
            desired_tab = clicked_tab
        elif trigger_id == "change_tabs_node":
            desired_tab = node_tab
        else:
            app.logger.warning(
                f"change_tab callback was triggered, but by {trigger_id}, which is unexpected."
            )
    if desired_tab and len(desired_tab) > 0 and isinstance(desired_tab, str):
        if desired_tab == "bs":
            return [balance_sheet.layout]
        elif desired_tab == "ex":
            return [explorer.layout]
        elif desired_tab == "ds":
            return [data_source.layout]
        elif desired_tab == "le":
            return [hometab.layout]
        else:
            app.logger.warning(
                f"attempted to change tab to {desired_tab}, which is not a valid choice."
            )
    raise PreventUpdate


@app.callback(
    [Output("ex_tab", "label"), Output("bs_tab", "label"), Output("ds_tab", "label")],
    [Input("param_store_for_tab_labels", "children")],
)
def relabel_tab(param_store: str):
    """ If the setttings have any renaming for tab labels, apply them """
    require_or_raise(param_store)
    params = Params(**json.loads(param_store))
    return [params.ex_label, params.bs_label, params.ds_label]


@app.callback(
    [
        Output("param_urlnode", "children"),
        Output("trans_urlfile_node", "children"),
        Output("atree_urlfile_node", "children"),
        Output("eras_urlfile_node", "children"),
    ],
    [Input("url_reader", "search")],
)
def parse_url_search(search: str):
    """ Process the search portion of any input URL and store it to an intermediate location """
    if not search or not isinstance(search, str) or not len(search) > 0:
        raise PreventUpdate
    search = search.lstrip("?")
    inputs = parse_qs(search)
    c_data = {}
    for key, value in vars(Params()).items():
        try:
            input_list: list = inputs.get(key, [])
            input_value: str = input_list[0]
            if input_value and len(input_value) > 0 and isinstance(input_value, str):
                if key in ["ex_account_filter", "bs_account_filter"]:
                    input_value = Params.parse_account_string(input_value)
                c_data[key] = input_value
        except (IndexError, TypeError):
            pass
        except Exception as E:
            app.logger.warning(
                f"failed to parse url input key: {key}, value: {value}.  Error {E}"
            )
    params_j = Params(**c_data).to_json()
    trans_j = None
    trans_input = inputs.get("transu", None)
    if trans_input:
        try:
            transu = trans_input[0]
            if isinstance(transu, str):
                filename, t_data, text = load_input_file("", transu, "")
                if len(t_data) > 0:
                    trans_j = t_data.to_json()
        except Exception as E:
            app.logger.warning(f"Failed to load {transu} because {E}")
    atree_j = None
    atree_input = inputs.get("atreeu", None)
    if atree_input:
        atreeu = atree_input[0]
        if isinstance(atreeu, str):
            filename, t_data, text = load_input_file("", atreeu, "")
            if len(t_data) > 0:
                atree_j = t_data.to_json()
    eras_j = None
    eras_input = inputs.get("erasu", None)
    if eras_input:
        erasu = eras_input[0]
        if isinstance(erasu, str):
            filename, t_data, text = load_input_file("", erasu, "")
            if len(t_data) > 0:
                eras_j = t_data.to_json()
    return [params_j, trans_j, atree_j, eras_j]


@app.callback(
    [
        Output("data_store", "children"),
        Output("param_store", "children"),
        Output("param_store_for_tab_labels", "children"),
        Output("files_status", "children"),
        Output("ex_tab_trigger", "children"),
    ],
    [
        Input("trans_file_node", "children"),
        Input("atree_file_node", "children"),
        Input("eras_file_node", "children"),
        Input("trans_urlfile_node", "children"),
        Input("atree_urlfile_node", "children"),
        Input("eras_urlfile_node", "children"),
        Input("param_urlnode", "children"),
        Input("param_node", "children")]
)
def load_and_transform(
    trans_file_node: str,
    atree_file_node: str,
    eras_file_node: str,
    trans_urlfile_node: str,
    atree_urlfile_node: str,
    eras_urlfile_node: str,
    param_urlnode: str,
    param_node: str,
):
    """When any of the input files changes in interim storage, reload
    all the data."""
    ctx = dash.callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    else:
        trigger_id = None
    # look for fresh input, then file upload, then url upload.  This
    # way, user uploads by file or url will override anything loaded
    # from the Ledger Explorer url.
    data: str = ""
    params_j: str = ""
    status: str = ""
    t_source: str = ""
    if trigger_id == "trans_file_node":
        t_source = trans_file_node
    elif trigger_id == "trans_urlfile_node":
        t_source = trans_urlfile_node
    elif trans_file_node and len(trans_file_node) > 0:
        t_source = trans_file_node
    elif trans_urlfile_node and len(trans_urlfile_node) > 0:
        t_source = trans_urlfile_node
    else:
        status = "No transaction data loaded."
    if t_source and len(t_source) > 0:
        try:
            trans_data = pd.read_json(t_source)
            atree_data: pd.DataFrame = pd.DataFrame()
            a_source = None
            if trigger_id == "atree_file_node":
                a_source = atree_file_node
            elif trigger_id == "atree_urlfile_node":
                a_source = atree_urlfile_node
            elif atree_file_node and len(atree_file_node) > 0:
                a_source = atree_file_node
            elif atree_urlfile_node and len(atree_urlfile_node) > 0:
                a_source = atree_urlfile_node
            if a_source:
                atree_data = pd.read_json(a_source)
            eras_data: pd.DataFrame = pd.DataFrame()
            e_source = None
            if trigger_id == "eras_file_node":
                e_source = eras_file_node
            elif trigger_id == "eras_urlfile_node":
                e_source = eras_urlfile_node
            elif eras_file_node and len(eras_file_node) > 0:
                e_source = eras_file_node
            elif eras_urlfile_node and len(eras_urlfile_node) > 0:
                e_source = eras_urlfile_node
            if e_source:
                eras_data = pd.read_json(e_source)
            if param_node and len(param_node) > 0:
                c_source = json.loads(param_node)
            elif param_urlnode and len(param_urlnode) > 0:
                c_source = json.loads(param_urlnode)
            else:
                c_source = None
            params = Params(**c_source)
            trans, atree, eras = convert_raw_data(
                trans_data, atree_data, eras_data, params
            )
            data = json.dumps(
                {
                    "trans": trans.to_json(),
                    "eras": eras.to_json(),
                }
            )
            params_j = params.to_json()
            # Generate status info.  TODO: clean up this hack with a Jinja2 template, or at least another function
            status = html.Div(
                children=[
                    f"{len(trans)} transactions, {len(atree)} accounts, {len(eras)} reporting eras"
                ]
            )
        except LoadError as LE:
            status = f"Error loading transaction data: {LE.message}"
    return [data, params_j, params_j, status, 'True']


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
