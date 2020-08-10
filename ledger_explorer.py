# -*- coding: utf-8 -*-
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import logging
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import treelib
import urllib


# TODO
# - Show Era labels
# - make the LOOKUPs use constants, not numbers
#   - related: swap out the LOOKUP sliders for something more like a pushbutton selector
# - show more info in scatter label and hovertext
# - apply better colors, including fixing dark mode
# - Improve the status bar so it shows dates in more readable format, e.g., 2020·Q1
# - re-arrange areas so that controls are in the same plane as things they control
# - show loading icon when doing longer operations
# - have option for "Other" to collect smaller accounts, with depth control knob
# - make the ledger entries prettier (bigger fonts, less grid fluff, smaller date, shorter description w/full in hover)
# - put per month/per year into sunburst labels

#######################################################################
# Function definitions except for callbacks
#######################################################################


def color_variant(hex_color, brightness_offset=1):
    """ takes a color like #87c95f and produces a lighter or darker variant
    from https://chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html """

    rgb_hex = [hex_color[x:x+2] for x in [1, 3, 5]]
    new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
    new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]  # make sure new values are between 0 and 2x55
    return '#' + ''.join([hex(i)[2:] for i in new_rgb_int])


def get_children(account_id, account_tree):
    """
    Return a list of tags of all direct child accounts of the input account.
    """
    return [x.tag for x in account_tree.children(account_id)]


def get_descendents(account_id, account_tree):
    """
    Return a list of tags of all descendent accounts of the input account.
    """

    descendent_nodes = account_tree.subtree(account_id).all_nodes()
    return [x.tag for x in descendent_nodes]


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


def make_bar(account, color_num=0, time_resolution=0, time_span=1, deep=False):
    """ returns a go.Bar object with total by time_resolution period for
    the selected account.  If deep, include total for all descendent accounts. """

    if deep:
        tba = trans[trans['account'].isin(get_descendents(account, account_tree))]
    else:
        tba = trans[trans['account'] == account]

    tba = tba.set_index('date')

    tr = TIME_RES_LOOKUP[time_resolution]
    tr_hover = tr.get('abbrev')      # e.g., "Q"
    tr_label = tr.get('label')       # e.g., "Quarter"
    tr_months = tr.get('months')     # e.g., 3

    ts = TIME_SPAN_LOOKUP[time_span]
    ts_hover = ts.get('abbrev')      # e.g., "y"
    ts_months = ts.get('months')     # e.g., 12

    if tr_label == 'All':
        total = tba['amount'].sum()
        bin_amounts = pd.DataFrame({'date': latest_trans, 'value': total}, index=[earliest_trans])
        bin_amounts = bin_amounts.append({'date': earliest_trans, 'value': 0}, ignore_index=True)
        all_months = ((latest_trans - earliest_trans) / np.timedelta64(1, 'M'))
        factor = ts_months / all_months
        bin_amounts['value'] = bin_amounts['value'] * factor
        bin_amounts['text'] = f'{tr_hover}'
    elif tr_label == 'Era':
        latest_tba = tba.index.max()
        # convert the era dates to a series that can be used for grouping
        bins = eras.start_date.sort_values()
        bin_boundary_dates = bins.tolist()
        bin_labels = bins.index.tolist()
        # there must be one more bin boundary than label, so:
        if bin_boundary_dates[-1] <= latest_tba:
            # if there's going to be any data in the last bin, add a final boundary
            bin_boundary_dates = bin_boundary_dates + [latest_tba]
        else:
            # otherwise, lose its label, leaving its start as the final boundary of the previous
            bin_labels = bin_labels[0:-1]

        tba['bin'] = pd.cut(x=tba.index, bins=bin_boundary_dates, labels=bin_labels, duplicates='drop')
        bin_amounts = pd.DataFrame({'date': bin_boundary_dates[0:-1],
                                    'value': tba.groupby('bin')['amount'].sum()})
        bin_amounts['start_date'] = bin_boundary_dates[0:-1]
        bin_amounts['end_date'] = bin_boundary_dates[1:]
        bin_amounts['delta'] = bin_amounts['end_date'] - bin_amounts['start_date']
        bin_amounts['width'] = bin_amounts['delta'] / np.timedelta64(1, 'ms')
        bin_amounts['midpoint'] = bin_amounts['start_date'] + bin_amounts['delta'] / 2
        bin_amounts['delta'] = bin_amounts['end_date'] - bin_amounts['start_date']
        bin_amounts['months'] = bin_amounts['delta'] / np.timedelta64(1, 'M')
        bin_amounts['value'] = bin_amounts['value'] * (ts_months / bin_amounts['months'])
        bin_amounts['text'] = bin_amounts.index.astype(str)

    elif tr_label in ['Year', 'Quarter', 'Month']:
        resample_keyword = tr['resample_keyword']
        bin_amounts = tba.resample(resample_keyword).\
            sum()['amount'].\
            to_frame(name='value')
        factor = ts_months / tr_months
        bin_amounts['date'] = bin_amounts.index
        bin_amounts['value'] = bin_amounts['value'] * factor
        bin_amounts['text'] = f'{tr_hover}'
    else:
        # bad input data
        return None

    try:
        marker_color = disc_colors[color_num]
    except IndexError:
        # don't ever run out of colors
        marker_color = 'var(--Cyan)'

    bin_amounts['customdata'] = account
    bin_amounts['texttemplate'] = '%{customdata}'  # workaround for passing variables through layers of plotly

    if tr_label == 'Era':
        bar = go.Bar(
            name=account,
            x=bin_amounts.midpoint,
            width=bin_amounts.width,
            y=bin_amounts.value,
            customdata=bin_amounts.customdata,
            text=bin_amounts.text,
            texttemplate=bin_amounts.texttemplate,
            textposition='auto',
            hovertemplate='%{customdata}: %{y:$,.0f}<br>%{text}<extra></extra>',
            marker_color=marker_color)
    else:
        bar = go.Bar(
            name=account,
            x=bin_amounts.date,
            y=bin_amounts.value,
            customdata=bin_amounts.customdata,
            text=bin_amounts.text,
            texttemplate=bin_amounts.texttemplate,
            textposition='auto',
            hovertemplate='%{customdata}: %{y:$,.0f}<br>%{text}<br>starting %{x}<extra></extra>',
            marker_color=marker_color)

    return bar


def make_scatter(account, trans, color_num=0):
    """ returns scatter trace of input transactions
    """

    trace = go.Scatter(
        name=account,
        x=trans['date'],
        y=trans['amount'],
        text=trans['account'],
        ids=trans.index,
        mode='markers',
        marker=dict(
            symbol='circle'))
    return trace


def make_sunburst(trans, start_date=None, end_date=None, SUBTOTAL_SUFFIX=None):
    """
    Using a tree of accounts and a DataFrame of transactions,
    generate a figure for a sunburst, where each node is an account
    in the tree, and the value of each node is the subtotal of all
    transactions for that node and any subtree, filtered by date.
    """

    #######################################################################
    # Set up a new tree with totals based on date-filtered transactions
    #######################################################################
    if not start_date:
        start_date = trans['date'].min()
    if not end_date:
        end_date = pd.Timestamp.now()

    duration = (end_date - start_date) / np.timedelta64(1, 'M')
    sel_trans = trans[(trans['date'] >= start_date) & (trans['date'] <= end_date)]

    def make_subtotal_tree(trans):
        """
        Calculate the subtotal for each node (direct subtotal only, no children) in
        the provided transaction tree and store it in the tree.
        """
        trans = trans.reset_index(drop=True).set_index('account')
        sel_tree = make_account_tree_from_trans(trans)
        subtotals = trans.groupby('account').sum()['amount']
        for node in sel_tree.all_nodes():
            try:
                subtotal = subtotals.loc[node.tag]
            except KeyError:
                # These should be nodes without leaf_totals, and therefore
                # not present in the subtotals DataFrame
                continue

            norm_subtotal = round(subtotal / duration)
            if norm_subtotal < 0:
                norm_subtotal = 0
            node.data = {'leaf_total': norm_subtotal}

        return sel_tree

    _sun_tree = make_subtotal_tree(sel_trans)

    #######################################################################
    # Total up all the nodes.
    #######################################################################
    # sunburst is very very finicky and wants the subtotals to be
    # exactly correct and never missing, so build them directly from
    # the leaf totals to avoid floats, rounding, and other fatal problems.
    #
    # If a leaf_total is moved out of a subtotal, there
    # has to be a way to differentiate between clicking
    # on the sub-total and clicking on the leaf.  Do this by
    # appending a magic string to the id of the leaf.
    # Then, use the tag as the key to transaction.account.
    # This will cause the parent tag, 'XX Subtotal', to fail matches, and
    # the child, which is labeled 'XX Leaf' but tagged 'XX' to match.

    # BEFORE                          | AFTER
    # id   parent   tag  leaf_total   | id       parent   tag          leaf_total    total
    # A             A            50   | A                 A Subtotal                    72
    # B    A        B            22   | A Leaf   A        A                    50       50
    #                                 | B        A        B                    22       22

    def set_node_total(node):
        """
        Set the total value of the node as a property of the node.  Assumes
        a _sun_tree treelib.Tree in surrounding scope, and modifies that
        treelib as a side effect.

        Assumption: No negative leaf values

        Uses 'leaf_total' for all transactions that belong to this node's account,
        and 'total' for the final value for the node, including descendants.
        """
        nonlocal _sun_tree
        node_id = node.identifier
        tag = node.tag
        try:
            leaf_total = node.data.get('leaf_total', 0)
        except AttributeError:
            # in case it doesn't even have a data node
            leaf_total = 0
        running_subtotal = leaf_total

        children = _sun_tree.children(node_id)

        if children:
            # if it has children, rename it to subtotal, but
            # don't change the identity.
            subtotal_tag = tag + SUBTOTAL_SUFFIX
            _sun_tree.update_node(node_id, tag=subtotal_tag)

            # If it has its own leaf_total, move that amount
            # to a new leaf node
            if leaf_total > 0:

                new_leaf_id = node_id + LEAF_SUFFIX
                node.data['leaf_total'] = 0
                _sun_tree.create_node(identifier=new_leaf_id,
                                      tag=tag,
                                      parent=node_id,
                                      data=dict(leaf_total=leaf_total,
                                                total=leaf_total))

            for child in children:
                # recurse to get subtotals.  This won't double-count
                # the leaf_total from the node because children
                # was set before the new synthetic node
                child_total = set_node_total(child)
                running_subtotal += child_total

        # Remove zeros, because they look terrible in sunburst.
        if running_subtotal == 0:
            _sun_tree.remove_node(node_id)
        else:
            if node.data:
                node.data['total'] = running_subtotal
            else:
                node.data = {'total': running_subtotal}

        return running_subtotal

    root = _sun_tree.get_node(_sun_tree.root)

    set_node_total(root)

    def summarize_to_other(node):
        """
        If there are more than (MAX_SLICES - 2) children in this node,
        group the excess children into a new 'other' node.
        Recurse to do this for all children, including any 'other' nodes
        that get created.

        The "-2" accounts for the Other node to be created, and for
        one-based vs zero-based counting.
        """
        nonlocal _sun_tree
        node_id = node.identifier
        children = _sun_tree.children(node_id)
        if len(children) > (MAX_SLICES - 2):
            other_id = OTHER_PREFIX + node_id
            other_subtotal = 0
            _sun_tree.create_node(identifier=other_id,
                                  tag=other_id,
                                  parent=node_id,
                                  data=dict(total=other_subtotal))
            total_list = [(dict(identifier=x.identifier,
                                total=x.data['total']))
                          for x in children]
            sorted_list = sorted(total_list, key=lambda k: k['total'], reverse=True)
            for i, child in enumerate(sorted_list):
                if i > (MAX_SLICES - 2):
                    other_subtotal += child['total']
                    _sun_tree.move_node(child['identifier'], other_id)
            _sun_tree.update_node(other_id, data=dict(total=other_subtotal))

        children = _sun_tree.children(node_id)

        for child in children:
            summarize_to_other(child)

    # summarize_to_other(root)

    #######################################################################
    # Make the figure
    #######################################################################

    sun_frame = pd.DataFrame([(x.identifier,
                               x.tag,
                               x.bpointer,
                               x.data['total']) for x in _sun_tree.all_nodes()],
                             columns=['id', 'name', 'parent', 'value'])

    figure = px.sunburst(sun_frame,
                         ids='id',
                         names='name',
                         parents='parent',
                         values='value',
                         color='id',
                         color_discrete_sequence=['lightskyblue', 'lightskyblue'],
                         height=600,
                         branchvalues='total')

    figure.update_traces(
        go.Sunburst(),
        insidetextorientation='horizontal',
        maxdepth=3,
        hovertemplate='%{label}<br>%{value}',
        texttemplate='%{label}<br>%{value}',
    )

    figure.update_layout(
        font=big_font,
        margin=dict(
            t=10,
            l=5,  # NOQA
            r=5,
            b=5)
    )
    return figure


def positize(trans):
    """Negative values can't be plotted in sunbursts.  This can't be fixed with absolute value
    because that would erase the distinction between debits and credits within an account.
    This function always returns a net-positive-value DataFrame of transactions suitable for
    a sunburst."""

    if trans.sum(numeric_only=True)['amount'] < 0:
        trans['amount'] = trans['amount'] * -1

    return trans


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


#######################################################################
# Initialize and set up formatting
#######################################################################

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)


app = dash.Dash(__name__)

# this eliminates an error about 'A local version of http://localhost/dash_layout.css'
app.css.config.serve_locally = False

app.css.append_css(dict(external_url='http://localhost/dash_layout.css'))

pd.set_option('display.max_rows', None)  # useful for DEBUGging, put back to 10?

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

#######################################################################
# Load Data
#######################################################################

# this could come from a URL; simpler now to get from a local file
# crash if the load fails, as nothing is going to work

trans, account_tree = load_transactions('http://localhost/transactions.csv')
trans = trans.sort_values(['date', 'account'])
earliest_trans = trans['date'].min()
latest_trans = trans['date'].max()

# Load a custom eras file if present.
#
eras = load_eras('http://localhost/eras.csv', earliest_trans, latest_trans)
SUBTOTAL_SUFFIX = ' Subtotal'
LEAF_SUFFIX = ' Leaf'
OTHER_PREFIX = 'Other '
MAX_SLICES = 7  # TODO: expose this in a control


#######################################################################
# Declare the content of the page
#######################################################################
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
app.layout = html.Div(
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
                    id='account_burst',
                    figure=make_sunburst(trans, SUBTOTAL_SUFFIX=SUBTOTAL_SUFFIX))
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
#######################################################################
# Callback functions
#######################################################################


@app.callback(
    [Output('master_time_series', 'figure')],
    [Input('time_series_resolution', 'value'),
     Input('time_series_span', 'value')])
def apply_time_series_resolution(time_resolution, time_span):
    try:
        tr = TIME_RES_LOOKUP[time_resolution]
        ts = TIME_SPAN_LOOKUP[time_span]
        ts_label = ts.get('label')      # e.g., 'Annual' or 'Monthly'
        tr_label = tr.get('label')          # e.g., 'by Era'
    except IndexError:
        logging.critical(f'Bad data from period selectors: time_resolution {time_resolution}, time_span {time_span}')
        return

    chart_fig = go.Figure(layout=chart_fig_layout)
    root_account_id = account_tree.root  # TODO: Stub for controllable design
    selected_accounts = get_children(root_account_id, account_tree)

    for i, account in enumerate(selected_accounts):
        chart_fig.add_trace(make_bar(account, i, time_resolution, time_span, deep=True))

    chart_fig.update_layout(
        title={'text': f'Average {ts_label} $, by {tr_label} '},
        xaxis={'showgrid': True, 'dtick': 'M3'},
        barmode='relative')

    return [chart_fig]


@app.callback(
    [Output('selected_account_display', 'children'),
     Output('selected_date_range_display', 'children'),
     Output('detail_store', 'data'),
     Output('account_burst', 'figure')],
    [Input('master_time_series', 'figure'),
     Input('master_time_series', 'selectedData')])
def apply_selection_from_time_series(figure, selectedData):
    """
    Selecting specific points from the time series chart updates the
    account burst and the detail labels.

    Reminder to self: When you think selectedData input is broken, remember
    that unaltered default action in the graph is to zoom, not to select.

    Note: all of the necessary information is in figure but that doesn't seem
    to trigger reliably.  Adding selectedData as a second Input causes reliable
    triggering.

    TODO: maybe check for input safety?

    """
    selection_start_date = None
    selection_end_date = None
    date_range_content = None
    filtered_trans = None
    selected_accounts = []
    detail_store = None

    for trace in figure.get('data'):
        account = trace.get('name')
        points = trace.get('selectedpoints')
        if not points:
            continue
        selected_accounts.append(account)
        for point in points:
            # back out the selection parameters (account and start/end dates)
            # from the trace
            # TODO: for All, x is end date
            #       for By Era, x is start date
            #       for A/Q/M, x is end date
            # so fix that.
            selection_start_date = pd.to_datetime(trace['x'][point])
            # the last point in the time-series won't have a following point
            try:
                selection_end_date = pd.to_datetime(trace['x'][point + 1])
            except IndexError:
                selection_end_date = latest_trans

            logging.debug(f'point: start {selection_start_date}, end {selection_end_date}')
            point_accounts = get_descendents(account, account_tree)

            new_trans = trans.loc[trans['account'].isin(point_accounts)].\
                loc[trans['date'] >= selection_start_date].\
                loc[trans['date'] <= selection_end_date]

            try:
                filtered_trans.append(new_trans)
            except AttributeError:
                filtered_trans = new_trans

    # If no transactions are ultimately selected, show all transactions
    try:
        data_count = len(filtered_trans)
    except TypeError:
        data_count = 0
    if data_count == 0:
        filtered_trans = trans
        selected_accounts = ['All']

    pos_trans = positize(filtered_trans)
    sun_fig = make_sunburst(pos_trans, selection_start_date, selection_end_date, SUBTOTAL_SUFFIX=SUBTOTAL_SUFFIX)
    account_children = ', '.join(selected_accounts)
    if selection_start_date and selection_end_date:
        date_range_content = ['Between ',
                              selection_start_date.strftime("%Y-%m-%d"),
                              ' and ',
                              selection_end_date.strftime("%Y-%m-%d")]
        detail_store = {'start': selection_start_date, 'end': selection_end_date}
    return [account_children, date_range_content, detail_store, sun_fig]


@app.callback(
    [Output('trans_table', 'data'),
     Output('transaction_time_series', 'figure'),
     Output('burst_selected_account_display', 'children')],
    [Input('account_burst', 'clickData'),
     Input('detail_store', 'data')])
def apply_burst_click(burst_clickData, detail_data):
    """
    Clicking on a slice in the Sunburst updates the transaction list with matching transactions

    TODO: maybe check for input safety?
    """
    selected_accounts = []
    tts_fig = go.Figure(layout=chart_fig_layout)

    if burst_clickData:
        click_account = burst_clickData['points'][0]['id']
    else:
        click_account = []

    if click_account:
        try:
            selected_accounts = [click_account] + get_children(click_account, account_tree)
        except treelib.exceptions.NodeIDAbsentError:
            # This is a hack.  If the account isn't there, assume that the reason
            # is that it was reidentified to 'X Leaf', and back that out.
            try:
                if LEAF_SUFFIX in click_account:
                    revised_id = click_account.replace(LEAF_SUFFIX, '')
                    selected_accounts = [revised_id]
            except treelib.exceptions.NodeIDAbsentError:
                pass
    else:
        title = 'All'
        pass

    if selected_accounts:
        title = click_account
        sel_trans = trans[trans['account'].isin(selected_accounts)]
    else:
        sel_trans = trans

    try:
        start_date = detail_data['start']
        end_date = detail_data['end']
        sel_trans = sel_trans[(sel_trans['date'] >= start_date) & (sel_trans['date'] <= end_date)]
        tts_fig.add_shape(
            type="rect",
            x0=earliest_trans,
            x1=start_date,
            yref='paper',
            ysizemode='scaled',
            y0=0,
            y1=1,
            line=dict(width=0),
            fillcolor='#e1e1e1',
            opacity=0.6
        )
        tts_fig.add_shape(
            type="rect",
            x0=end_date,
            x1=latest_trans,
            yref='paper',
            ysizemode='scaled',
            y0=0,
            y1=1,
            line=dict(width=0),
            fillcolor='#e1e1e1',
            opacity=0.6
        )

    except (KeyError, TypeError):
        pass

    if len(selected_accounts) == 1:
        try:
            account = selected_accounts[0]
            tts_fig.add_trace(make_scatter(account, sel_trans))
        except TypeError:
            pass
    elif len(selected_accounts) > 1:
        # TODO: design bug: certain leaves (maybe with ¿hidden children?)
        # appear as leaves in the sunburst and show only one
        # account in the trans table, but have multiple selected_accounts
        # and so render as bars when they should be scatter
        for i, account in enumerate(selected_accounts):
            tts_fig.add_trace(make_bar(account, i, 4, 1, deep=True))
            tts_fig.update_layout(
                barmode='stack',
                showlegend=True)
    return [sel_trans.to_dict('records'), tts_fig, title]


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
