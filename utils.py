import pandas as pd
import plotly.express as px
import urllib
import treelib


disc_colors = px.colors.qualitative.D3

big_font = dict(
    family='IBM Plex Sans Medium',
    size=24)

medium_font = dict(
    family='IBM Plex Sans Light',
    size=20)

small_font = dict(
    family='IBM Plex Light',
    size=12)

time_series_layout = dict(
    legend={'x': 0, 'y': 1},
    font=small_font,
    paper_bgcolor='var(--bg)',
    titlefont=medium_font)


chart_fig_layout = dict(
    clickmode='event+select',
    dragmode='select',
    margin=dict(
        l=10,  # NOQA
        r=10,
        t=10,
        b=10),
    height=350,
    paper_bgcolor='var(--bg)',
    showlegend=False,
    title=dict(
            font=big_font,
            x=0.1,
            y=0.9),
    hoverlabel=dict(
        bgcolor='var(--bg)',
        font_color='var(--fg)',
        font=medium_font))

TIME_RES_LOOKUP = {
    0: {'label': 'All', 'abbrev': 'all'},
    1: {'label': 'Era', 'abbrev': 'era'},
    2: {'label': 'Year', 'abbrev': 'Y', 'resample_keyword': 'A', 'months': 12},
    3: {'label': 'Quarter', 'abbrev': 'Q', 'resample_keyword': 'Q', 'months': 3},
    4: {'label': 'Month', 'abbrev': 'Mo', 'resample_keyword': 'M', 'months': 1}}

TIME_RES_OPTIONS = {key: value['label'] for key, value in TIME_RES_LOOKUP.items()}

TIME_SPAN_LOOKUP = {
    0: {'label': 'Annual', 'abbrev': ' ⁄y', 'months': 12},
    1: {'label': 'Monthly', 'abbrev': ' ⁄mo', 'months': 1}}

TIME_SPAN_OPTIONS = {key: value['label'] for key, value in TIME_SPAN_LOOKUP.items()}


def load_eras(source, earliest_date, latest_date):
    """
    If era data file is available, use it to construct
    arbitrary bins
    """

    try:
        data = pd.read_csv(source)
    except urllib.error.HTTPError:
        return None

    data = data.astype({'start_date': 'datetime64'})
    data = data.astype({'end_date': 'datetime64'})

    data = data.sort_values(by=['start_date'], ascending=False)
    data = data.reset_index(drop=True).set_index('name')

    if pd.isnull(data.iloc[0].end_date):
        data.iloc[0].end_date = latest_date
    if pd.isnull(data.iloc[-1].start_date):
        data.iloc[-1].start_date = earliest_date

    return data


def load_transactions(source):
    """
    Load a csv matching the transaction export format from Gnucash.
    Uses columns 'Account Name', 'Description', 'Memo', Notes', 'Full Account Name', 'Date', 'Amount Num.'
    """

    def convert(s):  # not fast
        dates = {date: pd.to_datetime(date) for date in s.unique()}
        return s.map(dates)
    data = pd.read_csv(source, thousands=',')
    data.columns = [x.lower() for x in data.columns]
    data['date'] = data['date'].astype({'date': 'datetime64'})

    # Gnucash doesn't include the date, description, or notes for transaction splits.  Fill them in.
    data['date'] = data['date'].fillna(method='ffill')
    data['description'] = data['description'].fillna(method='ffill')
    data['notes'] = data['notes'].fillna(method='ffill')

    # data['date'] = convert(data['date']) # supposedly faster, but not actually much faster, and broken
    data = data.rename(columns={'amount num.': 'amount', 'account name': 'account'})

    data['amount'] = data['amount'].replace(to_replace=',', value='')
    data['amount'] = data['amount'].astype(float).round(decimals=0).astype(int)

    data.fillna('', inplace=True)  # Any remaining fields with invalid numerical data should be text fields
    data.where(data.notnull(), None)

    data['memo'] = data['memo'].astype(str)
    data['description'] = data['description'].astype(str)
    data['notes'] = data['notes'].astype(str)

    data['description'] = (data['description'] + ' ' + data['memo'] + ' ' + data['notes']).str.strip()
    trans = data[['date', 'description', 'amount', 'account', 'full account name']]
    account_tree = make_account_tree_from_trans(trans)
    return trans, account_tree


def make_account_tree_from_trans(trans):
    """ extract all accounts from a list of Gnucash account paths

    Each account name is a full path.  Parent accounts with no
    transactions will be missing from the data, so reconstruct the
    complete tree implied by the transaction data.

    As long as the accounts are sorted hierarchically, the algorithm
    should never encounter a missing parent except the first node.

    If there are multiple heads in the data, they will all belong to
    root, so the tree will still be a DAG
    """

    tree = treelib.Tree()
    tree.create_node(tag='All', identifier='root')
    accounts = trans['full account name'].unique()

    for account in accounts:
        branches = account.split(':')  # example: Foo:Bar:Baz
        for i, branch in enumerate(branches):
            name = branch
            if i == 0:
                parent = 'root'
            else:
                parent = branches[i-1]
            if not tree.get_node(name):
                tree.create_node(tag=name,
                                 identifier=name,
                                 parent=parent)

    tree = trim_excess_root(tree)
    return tree


def trim_excess_root(tree):
    # If the input tree's root has no branches, trim the superfluous node and return a shorter tree
    root_id = tree.root
    root_kids = tree.children(root_id)
    if len(root_kids) == 1:
        tree.update_node(root_kids[0].identifier, parent=None, bpointer=None)
        new_tree = tree.subtree(root_kids[0].identifier)
        return new_tree
    else:
        return tree


import dash_table

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


