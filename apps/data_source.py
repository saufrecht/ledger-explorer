import dash_core_components as dcc
import dash_html_components as html
import json

from dash.dependencies import Input, Output, State
from utils import load_eras, load_transactions


from app import app


layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            id='data_tab_body',
            className="control_bar dashbox",
            children=[
                html.Fieldset([
                    html.Div([
                        html.Label(
                            htmlFor='transactions_url',
                            children='Transaction Source URL'),
                        dcc.Input(
                            id='transactions_url',
                            type='url',
                            value='http://localhost/transactions.csv',
                            placeholder='URL for transaction csv file'
                        )]),
                    html.Div([
                        html.Label(
                            htmlFor='eras_url',
                            children='Eras source URL (optional)'),
                        dcc.Input(
                            id='eras_url',
                            type='url',
                            value='http://localhost/eras.csv',
                            placeholder='URL for eras csv file'
                        )]),
                    html.Button('Load', id='data_load_button')
                ]),
            ]),
        html.Div(id='meta_data',
                 children=[
                 ]),
        html.Div(id='top_records',
                 children=[
                 ]),
        html.Div(id='bottom_records',
                 children=[
                 ])
    ])


@app.callback(
    [Output('data_store', 'children'),
     Output('meta_data', 'children'),
     Output('top_records', 'children'),
     Output('bottom_records', 'children')],
    [Input('data_load_button', 'n_clicks')],
    state=[State('transactions_url', 'value'),
           State('eras_url', 'value')])
def load_data(n_clicks, transactions_url, eras_url):
    trans = load_transactions(transactions_url)
    earliest_trans = trans['date'].min()
    latest_trans = trans['date'].max()
    eras = load_eras(eras_url, earliest_trans, latest_trans)
    data = dict(trans=trans.to_json(orient='split'),
                eras=eras.to_json(orient='split', date_format='iso'))

    meta_info = [f'Data loaded: {len(trans)} records',
                 f'Earliest record: {earliest_trans}',
                 f'Latest record: {latest_trans}',
                 f'Eras loaded: {len(eras)}']
    meta_html = [html.Div(children=x) for x in meta_info]

    top_html = ['first 5 records'] + trans.head(n=5).values.tolist()
    bottom_html = ['last 5 records'] + trans.tail(n=5).values.tolist()

    top_html = [html.Div(children=x) for x in top_html]
    bottom_html = [html.Div(children=x) for x in bottom_html]

    return [json.dumps(data), meta_html, top_html, bottom_html]
