import dash_core_components as dcc
import dash_html_components as html
import dash_table
from utils import TIME_RES_OPTIONS, TIME_SPAN_OPTIONS


trans_table = dash_table.DataTable(
    id='trans_table',
    columns=[dict(id='date', name='Date'),
             dict(id='account', name='Account'),
             dict(id='description', name='Description'),
             dict(id='amount', name='Amount')],
    style_header={'font-family': 'IBM Plex Sans, Verdana, sans',
                  'font-size=': '1.1rem',
                  'text-align': 'center'},
    style_cell={'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'maxWidth': 0,
                'backgroundColor': 'var(--bg-more)'},
    style_cell_conditional=[
        {'if': {'column_id': 'date'},
         'textAlign': 'left',
         'padding': '0px 10px',
         'width': '18%'},
        {'if': {'column_id': 'account'},
         'textAlign': 'left',
         'padding': '0px px',
         'width': '20%'},
        {'if': {'column_id': 'description'},
         'textAlign': 'left',
         'padding': 'px 2px 0px 3px'},
        {'if': {'column_id': 'amount'},
         'padding': '0px 12px 0px 0px',
         'width': '13%'}],
    data=[],
    sort_action='native',
    page_action='native',
    filter_action='native',
    style_as_list_view=True,
    page_size=20)


cash_flow = html.Div(
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
