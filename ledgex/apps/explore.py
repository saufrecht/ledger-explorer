import json

import dash_core_components as dcc
import dash_html_components as html
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from ledgex.app import app
from ledgex.atree import ATree
from ledgex.params import CONST, Params
from ledgex.utils import (
    chart_fig_layout,
    ex_trans_table,
    make_bar,
    trans_to_burst,
    preventupdate_if_empty,
    LError,
)
from ledgex.data_store import Datastore


layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                html.Div(id="explore_chart", className="flex_down"),
            ],
        ),
    ],
)
