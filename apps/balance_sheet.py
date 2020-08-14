import dash_core_components as dcc
import dash_html_components as html
from utils import TIME_RES_OPTIONS, TIME_SPAN_OPTIONS, trans_table


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            id='time_series_control_bar',
            className="control_bar dashbox",
            children=[
                dcc.Slider(
                    className='resolution-slider',
                    id='time_series_resolution',
                    min=0,
                    max=4,
                    step=1,
                    marks=TIME_RES_OPTIONS,
                    value=1
                ),
                dcc.Slider(
                    className='span-slider',
                    id='time_series_span',
                    min=0,
                    max=1,
                    step=1,
                    marks=TIME_SPAN_OPTIONS,
                    value=1
                )
            ]),
        html.Div(
            id='detail_control_bar',
            className="control_bar dashbox",
            children=[
                html.H2(
                    id='selected_account_display',
                    children=['Account']),
                html.H2(
                    id='burst_selected_account_display',
                    children=[]),
                html.H2(
                    id='selected_date_range_display',
                    children=['All Dates']),
                dcc.Store(id='detail_store',
                          storage_type='memory')
            ]),
        html.Div(
            className='account_burst dashbox',
            children=[
                dcc.Graph(
                    id='account_burst')
            ]),
        html.Div(
            className='master_time_series dashbox',
            children=[
                dcc.Graph(
                    id='master_time_series')
            ]),
        html.Div(
            className="trans_table dashbox",
            children=[
                trans_table
            ]),
        html.Div(
            className='transaction_time_series dashbox',
            children=[
                dcc.Graph(
                    id='transaction_time_series')
            ]),
    ])


balance_sheet = html.Div(
    className="layout_box",
    children=[
        html.Div(
            id='time_series_control_bar',
            className="control_bar dashbox",
            children=[
                dcc.Slider(
                    className='resolution-slider',
                    id='time_series_resolution',
                    min=0,
                    max=4,
                    step=1,
                    marks=TIME_RES_OPTIONS,
                    value=1
                ),
                dcc.Slider(
                    className='span-slider',
                    id='time_series_span',
                    min=0,
                    max=1,
                    step=1,
                    marks=TIME_SPAN_OPTIONS,
                    value=1
                )
            ]),
        html.Div(
            id='detail_control_bar',
            className="control_bar dashbox",
            children=[
                html.H2(
                    id='selected_account_display',
                    children=['Account']),
                html.H2(
                    id='burst_selected_account_display',
                    children=[]),
                html.H2(
                    id='selected_date_range_display',
                    children=['All Dates']),
                dcc.Store(id='detail_store',
                          storage_type='memory')
            ]),
        html.Div(
            className='account_burst dashbox',
            children=[
                dcc.Graph(
                    id='account_burst')
            ]),
        html.Div(
            className='master_time_series dashbox',
            children=[
                dcc.Graph(
                    id='master_time_series')
            ]),
        html.Div(
            className="trans_table dashbox",
            children=[
                trans_table
            ]),
        html.Div(
            className='transaction_time_series dashbox',
            children=[
                dcc.Graph(
                    id='transaction_time_series')
            ]),
    ])
