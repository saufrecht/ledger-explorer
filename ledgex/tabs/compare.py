import logging

from dash import dcc, html
import pandas as pd
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate
from app import app
from atree import ATree
from params import CONST, Params
from utils import make_cum_area, preventupdate_if_empty
from datastore import Datastore

layout: html = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className="time_series_box",
            children=[
                html.H2("Stub for comparing two different things side by side"),
                html.Div(id="comparison", className="flex_down"),
            ],
        ),
    ],
)
