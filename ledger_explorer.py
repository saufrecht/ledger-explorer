# -*- coding: utf-8 -*-
import dash
import dash_table
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import treelib
import urllib


#######################################################################
# All function definitions here, except for the callbacks at the end
#######################################################################


def color_variant(hex_color, brightness_offset=1):
    """ takes a color like #87c95f and produces a lighter or darker variant
    from https://chase-seibert.github.io/blog/2011/07/29/python-calculate-lighterdarker-rgb-colors.html """

    if len(hex_color) != 7:
        app.logger.debug(f'Passed {hex_color} into color_variant(), but it needs to be in #xxxxxx format.')
    rgb_hex = [hex_color[x:x+2] for x in [1, 3, 5]]
    new_rgb_int = [int(hex_value, 16) + brightness_offset for hex_value in rgb_hex]
    new_rgb_int = [min([255, max([0, i])]) for i in new_rgb_int]  # make sure new values are between 0 and 255
    return '#' + ''.join([hex(i)[2:] for i in new_rgb_int])


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


def get_account_tree_from_transaction_data(trans):
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


def get_era_bar(account, eras, color_num=0):
    """
    returns a line trace and two scatter traces, with era-grouped
    monthly averages for the selected account.
    """

    # filter to get transaction by account (tba)
    tba = trans[trans['account'] == account]
    if len(tba) == 0:
        return

    # convert the era dates to a series that can be used for grouping
    bins = eras.start_date.sort_values()

    # group the data and build the traces
    tba['bins'] = pd.cut(x=tba.date, bins=bins, duplicates='drop')
    sums = tba.groupby('bins').sum()
    bar_x = []
    bar_y = []
    label_x = []
    label_y = []

    # convert the sums array into a plotable line trace, by using
    # start and stop of each bin as x values, and using the y value
    # twice for each bin.  probably this is the most hacky way to do
    # it.  This hack messes up lebeling, so make a separate annotation
    # trace.
    for i in range(len(sums)):
        value = int(sums['amount'][i] / (sums.axes[0][i].length / np.timedelta64(1, 'M')))
        bar_x.append(sums.index[i].left)
        bar_x.append(sums.index[i].right)
        bar_y.append(value)
        bar_y.append(value)
        label_x.append(sums.index[i].mid)
        label_y.append(value)
    bar = go.Scatter(
        name='average monthly spending',
        x=bar_x,
        y=bar_y,
        mode='lines+text',
        line_shape='hvh',
        text=None,
        hovertemplate="<extra></extra>",
        line=dict(
            color=color_variant(disc_colors[color_num], 30),
            width=2))

    era_value = go.Scatter(
        name='era values',
        x=label_x,
        y=label_y,
        mode='text',
        text=label_y,
        textposition='top center',
        textfont=medium_font,
        hovertemplate="<extra></extra>")

    era_name = go.Scatter(
        name='era labels',
        x=label_x,
        y=label_y,
        mode='text',
        text=eras.index,
        textposition='bottom center',
        textfont=dict(
            size=12),
        line=dict(
            color=color_variant(disc_colors[color_num], 30),
            width=2),
        hovertemplate="<extra></extra>")

    return bar, era_value, era_name


def make_bar(account, color_num=0, time_resolution=0, time_span=1, deep=False):
    """ returns a go.Bar object with total by time_resolution period for
    the selected account.  If deep, include total for all descendent accounts. """

    if deep:
        tba = trans[trans['account'].isin(get_descendents(account, account_tree))]
    else:
        tba = trans[trans['account'] == account]

    tba = tba.set_index('date')

    tr = TIME_RES_LOOKUP[time_resolution]
    tr_hover = tr['hovertext']  # e.g., "q."
    tr_label = tr['label']      # e.g., 'Quarterly'
    tr_months = tr['months']

    ts = TIME_SPAN_LOOKUP[time_span]
    ts_hover = ts['hovertext']      # e.g., 'per y'
    ts_months = ts['months']
    factor = ts_months / tr_months

    if tr_label == 'All':
        # TODO
        # this is the only way to get an entire tranche of data for all time into the sunburst
        # all_data = pd.DataFrame({'start_date': [earliest_date], 'end_date': [latest_date], 'name': 'All'})
        return None
    elif tr_label == 'By Era':
        # convert the era dates to a series that can be used for grouping
        bins = eras.start_date.sort_values()
        # group the data and build the traces
        tba['bin'] = pd.cut(x=tba.index, bins=bins, duplicates='drop')
        bin_amounts = tba.groupby('bin').sum()
    elif tr_label in ['Annual', 'Quarterly', 'Monthly']:
        resample_keyword = tr['resample_keyword']
        bin_amounts = tba.resample(resample_keyword).\
            sum()['amount'].\
            to_frame(name='value')
        bin_amounts['text'] = f'{ts_hover} <br>DEBUG ts_months: {ts_months}, tr_months: {tr_months}, factor {factor}<br>{tr_hover}'
        bin_amounts['value'] = bin_amounts['value'] * factor
        bin_amounts['account'] = account
    else:
        # bad input data
        return None

    try:
        marker_color = disc_colors[color_num]
    except IndexError:
        # don't ever run out of colors
        marker_color = 'var(--Cyan)'

    customdata = bin_amounts['account']
    bar = go.Bar(
        name=account,
        x=bin_amounts.index,
        y=bin_amounts.value,
        customdata=customdata,
        text=bin_amounts.text,
        hovertemplate='%{customdata} %{y:$,.0f} %{text} ending %{x}',
        marker_color=marker_color)

    return bar


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


def get_trace(account, color_num=0):
    """ returns """
    tba = trans[trans['account'] == account]
    trace = go.Scatter(
        name=account,
        x=tba['date'],
        y=tba['amount'],
        text=tba['account'],
        ids=tba.index,
        mode='markers',
        marker=dict(
            symbol='circle-open',
            opacity=0.5))
    return trace


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
    account_tree = get_account_tree_from_transaction_data(trans)
    return trans, account_tree


def make_sunburst(account_tree, trans, start_date=None, end_date=None):
    """
    Generate a figure for a sunburst, where each node is an account
    and the value of each node is the subtotal of all transactions for
    that node and any subtree, filtered by date.
    """

    #######################################################################
    # Set up a new tree with totals based on date-filtered transactions
    #######################################################################
    if not start_date:
        start_date = trans['date'].min()
    if not end_date:
        end_date = pd.Timestamp.now()
    duration = (end_date - start_date) / np.timedelta64(1, 'M')
    trans = trans[(trans['date'] >= start_date) & (trans['date'] <= end_date)]
    sun_tree = get_account_tree_from_transaction_data(trans)

    def leaf_total(account):
        """
        Generate the subtotal of all transactions for the account
        """
        subtotal = round((trans[trans['account'] == account].sum()['amount']) / duration)
        # this algorithm took 0.14 sec for Out.  Try something faster.
        if subtotal < 0:
            subtotal = 0
        return subtotal

    for node in sun_tree.all_nodes():
        node.data = {'leaf_total': leaf_total(node.identifier)}

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
        a sun_tree treelib.Tree in surrounding scope, and modifies that
        treelib as a side effect.

        Assumption: No negative leaf values

        Uses 'leaf_total' for all transactions that belong to this node's account,
        and 'total' for the final value for the node, including descendants.
        """
        nonlocal sun_tree
        node_id = node.identifier
        tag = node.tag
        leaf_total = node.data.get('leaf_total', 0)
        running_subtotal = leaf_total

        children = sun_tree.children(node_id)

        if children:
            # if it has children, rename it to subtotal, but
            # don't change the identity.
            subtotal_tag = tag + SUBTOTAL_SUFFIX
            sun_tree.update_node(node_id, tag=subtotal_tag)

            # If it has its own leaf_total, move that amount
            # to a new leaf node
            if leaf_total > 0:

                new_leaf_id = node_id + LEAF_SUFFIX
                node.data['leaf_total'] = 0
                sun_tree.create_node(identifier=new_leaf_id,
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
            sun_tree.remove_node(node_id)
        else:
            node.data['total'] = running_subtotal

        return running_subtotal

    root = sun_tree.get_node(sun_tree.root)

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
        nonlocal sun_tree
        node_id = node.identifier
        children = sun_tree.children(node_id)
        if len(children) > (MAX_SLICES - 2):
            other_id = OTHER_PREFIX + node_id
            other_subtotal = 0
            sun_tree.create_node(identifier=other_id,
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
                    sun_tree.move_node(child['identifier'], other_id)
            sun_tree.update_node(other_id, data=dict(total=other_subtotal))

        children = sun_tree.children(node_id)

        for child in children:
            summarize_to_other(child)

    # summarize_to_other(root)

    #######################################################################
    # Make the figure
    #######################################################################

    sun_frame = pd.DataFrame([(x.identifier,
                               x.tag,
                               x.bpointer,
                               x.data['total']) for x in sun_tree.all_nodes()],
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
        texttemplate='%{label}<br>%{value}',
        hovertemplate='%{label}<br>%{value}'
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


#######################################################################
# Initialize and set up formatting
#######################################################################
app = dash.Dash(__name__)

# this eliminates an error about 'A local version of http://localhost/dash_layout.css'
app.css.config.serve_locally = False

app.css.append_css(dict(external_url='http://localhost/dash_layout.css'))

# useful for DEBUGging
pd.set_option('display.max_rows', None)  # DEBUG: put back to 10?

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
    xaxis={'title': 'Date'},
    yaxis={'title': 'Dollars'},
    legend={'x': 0, 'y': 1},
    font=small_font,
    titlefont=medium_font)


chart_fig_layout = dict(
    clickmode='event+select',
    dragmode='select',
    margin=dict(
        l=10,  # NOQA
        r=10,
        t=10,
        b=10),
    showlegend=False,
    title=dict(
            font=big_font,
            x=0.5,
            y=0.9),
    hoverlabel=dict(
        bgcolor='var(--bg)',
        font_color='var(--fg)',
        font=small_font))

# TODO: move this to a class?
TIME_RES_LOOKUP = {
    0: {'label': 'All'},
    1: {'label': 'By Era'},
    2: {'label': 'Annual', 'hovertext': 'year', 'resample_keyword': 'A', 'months': 12},
    3: {'label': 'Quarterly', 'hovertext': 'q.', 'resample_keyword': 'Q', 'months': 3},
    4: {'label': 'Monthly', 'hovertext': 'mo.', 'resample_keyword': 'M', 'months': 1}}

TIME_RES_OPTIONS = {key: value['label'] for key, value in TIME_RES_LOOKUP.items()}

TIME_SPAN_LOOKUP = {
    0: {'label': 'per year', 'hovertext': 'per year', 'months': 12},
    1: {'label': 'per month', 'hovertext': 'per month', 'months': 1}}

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
MAX_SLICES = 7

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
            className="control_bar dashbox",
            children=[
                html.H1(
                    id='titlebar',
                    children=['Ledger']),
                dcc.Slider(
                    className='resolution-slider',
                    id='time_series_resolution',
                    min=0,
                    max=4,
                    step=1,
                    marks=TIME_RES_OPTIONS,
                    value=4
                ),
                dcc.Slider(
                    className='span-slider',
                    id='time_series_span',
                    min=0,
                    max=1,
                    step=1,
                    marks=TIME_SPAN_OPTIONS,
                    value=1
                ),
                dcc.RadioItems(
                    id='time_periods')
            ]),
        html.Div(
            className='account_burst dashbox',
            children=[
                dcc.Graph(
                    id='account_burst',
                    figure=make_sunburst(account_tree, trans))
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
    Output('master_time_series', 'figure'),
    [Input('time_series_resolution', 'value'),
     Input('time_series_span', 'value')])
def apply_time_series_resolution(time_resolution, time_span):
    chart_fig = go.Figure(layout=chart_fig_layout)

    root_account_id = account_tree.root  # TODO: Stub for controllable design

    title = account_tree[root_account_id].tag
    selected_accounts = get_children(root_account_id, account_tree)
    for i, account in enumerate(selected_accounts):
        chart_fig.add_trace(make_bar(account, i, time_resolution, time_span, deep=True))

    chart_fig.update_layout(dict(
        title={'text': title}))

    chart_fig.update_layout(
        barmode='stack',
        showlegend=True)

    return chart_fig


@app.callback(
    Output('trans_table', 'data'),
    [Input('master_time_series', 'figure'),
     Input('master_time_series', 'selectedData')])
def apply_selection_from_time_series(figure, selectedDat):
    """
    Selecting specific points from the time series chart updates the
    transaction table.

    Reminder to self: When you think selectedData input is broken, remember
    that unaltered default action in the graph is to zoom, not to select.

    """

    filtered_trans = None
    for trace in figure['data']:
        account = trace['name']
        points = trace.get('selectedpoints')
        if not points:
            continue
        for point in points:
            end_date = pd.to_datetime(trace['x'][point])
            #try:
            start_date = pd.to_datetime(trace['x'][point - 1])
            #except:  # TODO: get the error name when clicking the first entry
            #    start_date = earliest_trans

            new_trans = trans[
                (trans['account'].isin(get_descendents(account, account_tree))) &
                (trans['date'] >= start_date) &
                (trans['date'] <= end_date)]
            try:
                filtered_trans.append(new_trans)
            except AttributeError:
                filtered_trans = new_trans

    try:
        data_count = len(filtered_trans)
    except TypeError:
        data_count = 0

    if data_count == 0:
        filtered_trans = trans

    return filtered_trans.to_dict('records')


# #    Output('account_burst', 'figure'),
# def apply_era_selector(selection):
#     try:
#         start_date = eras.loc[selection].start_date
#         end_date = eras.loc[selection].end_date
#     except IndexError:
#         start_date = None
#         end_date = None
#     sun_fig = make_sunburst(account_tree, trans, start_date, end_date)
#     return sun_fig


# @app.callback(
#     [Output('titlebar', 'children'),
#      Output('transaction_time_series', 'figure')],
#     [Input('account_burst', 'clickData')])
# def apply_burst_click(clickData):
#     """
#     Clicking on a slice in the Sunburst updates the titlebar with the name of the
#     now-active account and updates the transaction_time_series with the transactions:
#     For a leaf account, chart transactions, and monthly averages by year or era.
#     For a node account, chart monthly summaries of all subtree accounts.

#     Changing transaction_time_series will trigger the next callback, which will
#     update the transaction table with transactions for that selection
#     """
#     chart_fig = go.Figure(layout=chart_fig_layout)
#     if clickData:
#         click_account = clickData['points'][0]['id']
#     else:
#         click_account = []

#     selected_accounts = []
#     if click_account:
#         title = f'{click_account}'
#         try:
#             selected_accounts = [click_account] + get_children(click_account, account_tree)
#         except treelib.exceptions.NodeIDAbsentError:
#             # This is a hack.  If the account isn't there, assume that the reason
#             # is that it was reidentified to 'X Leaf', and back that out.
#             try:
#                 if LEAF_SUFFIX in click_account:
#                     revised_id = click_account.replace(LEAF_SUFFIX, '')
#                     selected_accounts = [revised_id]
#             except treelib.exceptions.NodeIDAbsentError:
#                 pass
#     else:
#         pass

#     if not selected_accounts:
#         title = 'All'

#     chart_fig.update_layout(dict(
#         title={'text': title}))

#     if len(selected_accounts) == 1:
#         account = selected_accounts[0]
#         chart_fig.add_trace(get_trace(account))
#         try:
#             era_bar, era_value, era_name = get_era_bar(account, eras=eras)
#             chart_fig.add_trace(era_bar)
#             chart_fig.add_trace(era_value)
#             chart_fig.add_trace(era_name)
#         except TypeError:
#             pass
#     elif len(selected_accounts) > 1:
#         for i, account in enumerate(selected_accounts):
#             chart_fig.add_trace(get_quarterly_bar(account, i))
#         chart_fig.update_layout(
#             barmode='stack',
#             showlegend=True)
#     else:
#         pass

#    return title, chart_fig


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
