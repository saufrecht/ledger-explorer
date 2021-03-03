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
from ledgex.tabs import compare, cumulative, data_source, explore, periodic, hometab, sankey
from ledgex.errors import LoadError
from ledgex.loading import convert_raw_data, load_input_file
from ledgex.params import CONST, Params
from ledgex.utils import preventupdate_if_empty

server = app.server

app.title = "Ledger Periodic"


# TODO: document/clarify/figure out what _trigger, _node, and _store are intending to mean
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
                        dcc.Tab(label=CONST["pe_label"], id="pe_tab", value="pe"),
                        dcc.Tab(label=CONST["cu_label"], id="cu_tab", value="cu"),
                        dcc.Tab(label=CONST["sa_label"], id="sa_tab", value="sa"),
                        dcc.Tab(label=CONST["co_label"], id="co_tab", value="co"),
                        dcc.Tab(label=CONST["ds_label"], id="ds_tab", value="ds"),
                        dcc.Tab(label="About", id="le_tab", value="le"),
                    ],
                ),
                html.Div(
                    id="infodex",
                    children=[
                        html.Div(id="files_status", children=[]),
                        html.A("Permalink", id="permalink", href=""),
                        dcc.Markdown(CONST["bug_report_md"]),
                        dcc.Location(id="url_reader", refresh=False),
                        html.Div(id="ui_node", className="hidden"),
                        html.Div(id="api_node", className="hidden"),
                        html.Div(id="api_inputs", className="hidden"),
                        html.Div(id="pe_tab_trigger", className="hidden"),
                        html.Div(id="ex_tab_trigger", className="hidden"),
                        html.Div(id="ui_trans_node", className="hidden"),
                        html.Div(id="ui_atree_node", className="hidden"),
                        html.Div(id="ui_eras_node", className="hidden"),
                        html.Div(id="api_trans_node", className="hidden"),
                        html.Div(id="api_atree_node", className="hidden"),
                        html.Div(id="api_eras_node", className="hidden"),
                        html.Div(id="data_store", className="hidden"),
                        html.Div(id="param_store", className="hidden"),
                        html.Div(id="tab_label_store", className="hidden"),
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
        cumulative.layout,
        data_source.layout,
        periodic.layout,
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
    [Output("tab_content", "children"), Output("tab_node", "children")],
    [Input("tabs", "value")],
)
def change_tab(clicked_tab: str) -> list:
    """From a click on the tabbar, or a change
    from the url, change the currently shown tab."""
    if clicked_tab == "co":
        return [compare.layout, "co"]
    elif clicked_tab == "cu":
        return [cumulative.layout, "cu"]
    elif clicked_tab == "ds":
        return [data_source.layout, "ds"]
    elif clicked_tab == "ex":
        return [explore.layout, "ex"]
    elif clicked_tab == "pe":
        return [periodic.layout, "pe"]
    elif clicked_tab == "sa":
        return [sankey.layout, "sa"]
    elif clicked_tab == "le":
        return [hometab.layout, "le"]
    else:
        app.logger.warning(
            f"attempted to change tab to {clicked_tab}, which is not a valid choice."
        )
    raise PreventUpdate


@app.callback(
    [
        Output("co_tab", "label"),
        Output("cu_tab", "label"),
        Output("ds_tab", "label"),
        Output("ex_tab", "label"),
        Output("pe_tab", "label"),
        Output("sa_tab", "label"),
    ],
    [Input("tab_label_store", "children")],
)
def relabel_tab(tab_label_store: str):
    """ If the setttings have any renaming for tab labels, apply them """
    preventupdate_if_empty(tab_label_store)
    params = Params(**json.loads(tab_label_store))
    params.fill_defaults()

    return [
        params.co_label,
        params.cu_label,
        params.ds_label,
        params.ex_label,
        params.pe_label,
        params.sa_label,
    ]


@app.callback(
    [
        Output("api_trans_node", "children"),
        Output("api_atree_node", "children"),
        Output("api_eras_node", "children"),
        Output("api_node", "children"),
        Output("api_inputs", "children"),
    ],
    [Input("url_reader", "search")],
)
def parse_url_search(search: str):
    """Process the search portion of any input URL and store it to an
    intermediate location.  If one or more data source URLs are
    provided via the input URL, load them here in the index.
    This is necessary in order for incoming links that provide data source URLs
    to load everything; otherwise they wouldn't work right until after
    the user browsed to the Data Source tab."""

    preventupdate_if_empty(search)

    def le_parse_qs(search: str):
        """Do some extra cleanup on url string over and above what the
        built-in parser does.  Specifically:
        1. Parser returns x=1,2 as {'x': '1, 2'}, but we want {'x': ['1', '2']}"""
        parsed_params = {}
        raw_qs = parse_qs(
            search, max_num_fields=50
        )  # 50 is arbitrary, for DoS prevention
        for key, value_list in raw_qs.items():
            key_list = []

            for value in value_list:
                if (not isinstance(value, str)) or (not len(value) > 0):
                    pass
                if "," in value:
                    for sub_val in value.split(","):
                        if isinstance(sub_val, str) and len(sub_val) > 0:
                            key_list.append(sub_val)
                else:
                    key_list.append(value)
            parsed_params[key] = key_list
        return parsed_params

    search = search.lstrip("?")
    if not search or not isinstance(search, str) or not len(search) > 0:
        raise PreventUpdate
    inputs = le_parse_qs(search)
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
        if len(a_data) > 0:
            atree_j = a_data.to_json()

    eras_input = inputs.get("erasu", None)
    if eras_input:
        filename, e_data, text = load_input_file(url=eras_input[0])
        if len(e_data) > 0:
            eras_j = e_data.to_json()

    return [trans_j, atree_j, eras_j, api_input_j, api_input_j]


@app.callback(
    [
        Output("data_store", "children"),
        Output("param_store", "children"),
        Output("tab_label_store", "children"),
        Output("files_status", "children"),
        Output("pe_tab_trigger", "children"),
        Output("ex_tab_trigger", "children"),
        Output("permalink", "href"),
    ],
    [
        Input("ui_trans_node", "children"),
        Input("ui_atree_node", "children"),
        Input("ui_eras_node", "children"),
        Input("api_trans_node", "children"),
        Input("api_atree_node", "children"),
        Input("api_eras_node", "children"),
        Input("ui_node", "children"),
        Input("api_node", "children"),
    ],
    state=[State("tab_node", "children")],
)
def load_and_transform(
    ui_trans_node: str,
    ui_atree_node: str,
    ui_eras_node: str,
    api_trans_node: str,
    api_atree_node: str,
    api_eras_node: str,
    ui_node: str,
    api_node: str,
    tab_node: str,
):
    """When any of the parameters or input files changes, reload
    all the data.
    The api_*_nodes will contain data loaded directly from the API (i.e.,
    from URL search parameters), and the ui_*_nodes will contain data
    loaded from the data_source tab, so ui should trump api.
    """
    ctx = dash.callback_context
    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    else:
        trigger_id = None
    # Work through the possible triggers to make sure that behavior is as expected:
    #   1. If on the data_source tab, and UI input was the trigger, use UI. Else:
    #   2. If the API was the trigger, use API. Else:
    #   3. If UI is present, use UI.  Else:
    #   4. If API is present, use it.
    #   This order ensures that user input will always trump paths in the URL
    data: str = ""
    params_j: str = ""
    status: str = ""
    t_source: str = ""
    if tab_node == "ds" and trigger_id == "ui_trans_node":
        t_source = ui_trans_node
    elif trigger_id == "api_trans_node":
        t_source = api_trans_node
    elif ui_trans_node and len(ui_trans_node) > 0:
        t_source = ui_trans_node
    elif api_trans_node and len(api_trans_node) > 0:
        t_source = api_trans_node
    else:
        status = "No transaction data loaded."
    ui_source = {}
    if tab_node == "ds" and ui_node and len(ui_node) > 0:
        ui_source = json.loads(ui_node)
    api_source = {}
    if api_node and len(api_node) > 0:
        api_source = json.loads(api_node)
    # combine api_source and ui_source, with ui_source having
    # precedence
    merged_source = {**api_source, **ui_source}
    # and strip params back down to simple strings;
    # otherwise, each round through will add another layer of []s
    params = Params.from_dict(merged_source)
    params.fill_defaults()
    params_j = params.to_json()
    for key, value in merged_source.items():
        if isinstance(value, list):
            merged_source[key] = ','.join(value)

    permalink = urlencode(merged_source)

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
    return [data, params_j, params_j, status, "True", "True", f"/{tab_node}?{permalink}"]


if __name__ == "__main__":
    # This block runs when index.py is called from the command line, i.e., in development mode
    app.config["suppress_callback_exceptions"] = True
    app.logger.setLevel(logging.DEBUG)
    app.run_server(debug=True, host="0.0.0.0", port="8200")

else:
    # This block runs when index.py is called from gunicorn.  Logging
    # is passed on to gunicorn logger, whatever that may be, instead of the console.
    # (from https://trstringer.com/logging-flask-gunicorn-the-manageable-way/)
    gunicorn_logger = logging.getLogger("gunicorn.error")
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
    external_stylesheets = ["https://ledge.uprightconsulting.com/s/dash_layout.css"]
