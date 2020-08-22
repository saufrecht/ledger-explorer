import json
import numpy as np
import pandas as pd
import treelib
import urllib


import dash_table
import plotly.express as px
import plotly.graph_objects as go


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

TIME_RES_LOOKUP: dict = {
    0: {'label': 'Total', 'abbrev': 'Total'},
    1: {'label': 'Era', 'abbrev': 'era'},
    2: {'label': 'Year', 'abbrev': 'Y', 'resample_keyword': 'A', 'months': 12},
    3: {'label': 'Quarter', 'abbrev': 'Q', 'resample_keyword': 'Q', 'months': 3},
    4: {'label': 'Month', 'abbrev': 'Mo', 'resample_keyword': 'M', 'months': 1}}

TIME_RES_OPTIONS: dict = {key: value['label'] for key, value in TIME_RES_LOOKUP.items()}

TIME_SPAN_LOOKUP: dict = {
    0: {'label': 'Annual', 'abbrev': ' ⁄y', 'months': 12},
    1: {'label': 'Monthly', 'abbrev': ' ⁄mo', 'months': 1}}

TIME_SPAN_OPTIONS: dict = {key: value['label'] for key, value in TIME_SPAN_LOOKUP.items()}


SUBTOTAL_SUFFIX: str = ' Subtotal'
LEAF_SUFFIX: str = ' Leaf'
OTHER_PREFIX: str = 'Other '
MAX_SLICES: int = 7  # TODO: expose this in a control


def data_from_json_store(data_store: str, filter: list) -> tuple:
    """ Parse data stored in Dash JSON component.  Used to move data between different
    callbacks in Dash """

    data = json.loads(data_store)
    trans = pd.read_json(data['trans'], orient='split')
    account_tree = make_account_tree_from_trans(trans)
    filter_accounts: list = []

    for account in filter:
        filter_accounts = filter_accounts + get_descendents(account, account_tree)

    if filter_accounts:
        trans = trans[trans['account'].isin(filter_accounts)]

    # rebuild account tree from filtered trans
    account_tree = make_account_tree_from_trans(trans)

    eras = pd.read_json(data['eras'],
                        orient='split',
                        dtype={'index': 'str', 'start_date': 'datetime64', 'end_date': 'datetime64'})
    earliest_trans = trans['date'].min()
    latest_trans = trans['date'].max()

    return trans, eras, account_tree, earliest_trans, latest_trans


def get_descendents(account_id: str, account_tree: treelib) -> list:
    """
    Return a list of tags of all descendent accounts of the input account.
    """

    try:
        descendent_nodes = account_tree.subtree(account_id).all_nodes()
    except treelib.exceptions.NodeIDAbsentError:
        descendent_nodes = []

    return [x.tag for x in descendent_nodes]


def make_bar(trans: pd.DataFrame,
             account_tree: treelib,
             eras: pd.DataFrame,
             account_id: str,
             color_num: int = 0,
             time_resolution: int = 0,
             time_span: int = 1,
             deep: bool = False):
    """ returns a go.Bar object with total by time_resolution period for
    the selected account.  If deep, include total for all descendent accounts. """
    if deep:
        tba = trans[trans['account'].isin(get_descendents(account_id, account_tree))]
    else:
        tba = trans[trans['account'] == account_id]

    tba = tba.set_index('date')
    tr: dict = TIME_RES_LOOKUP[time_resolution]
    tr_hover: str = tr.get('abbrev', None)      # e.g., "Q"
    tr_label: str = tr.get('label', None)       # e.g., "Quarter"
    tr_months: int = tr.get('months', None)     # e.g., 3

    ts = TIME_SPAN_LOOKUP[time_span]
    ts_hover = ts.get('abbrev')      # NOQA  e.g., "y"
    ts_months = ts.get('months')     # e.g., 12

    earliest_trans = tba.index.min()
    latest_trans = tba.index.max()

    if tr_label == 'Total':
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

    bin_amounts['customdata'] = account_id
    bin_amounts['texttemplate'] = '%{customdata}'  # workaround for passing variables through layers of plotly

    if tr_label == 'Era':
        bar = go.Bar(
            name=account_id,
            x=bin_amounts.midpoint,
            width=bin_amounts.width,
            y=bin_amounts.value,
            customdata=bin_amounts.customdata,
            text=bin_amounts.text,
            texttemplate=bin_amounts.texttemplate,
            textposition='auto',
            opacity=0.9,
            hovertemplate='%{customdata}: %{y:$,.0f}<br>%{text}<extra></extra>',
            marker_color=marker_color)
    else:
        bar = go.Bar(
            name=account_id,
            x=bin_amounts.date,
            y=bin_amounts.value,
            customdata=bin_amounts.customdata,
            text=bin_amounts.text,
            texttemplate=bin_amounts.texttemplate,
            textposition='auto',
            opacity=0.9,
            hovertemplate='%{customdata}: %{y:$,.0f}<br>%{text}<br>starting %{x}<extra></extra>',
            marker_color=marker_color)

    return bar


def make_cum_bar(
        trans: pd.DataFrame,
        account_tree: treelib,
        eras: pd.DataFrame,
        account_id: str,
        color_num: int = 0,
        time_resolution: int = 0,
        time_span: int = 1,
        deep: bool = False) -> go.Bar:
    """ returns a go.Bar object with cumulative total by time_resolution period for
    the selected account.  If deep, include total for all descendent accounts. """

    if deep:
        tba = trans[trans['account'].isin(get_descendents(account_id, account_tree))]
    else:
        tba = trans[trans['account'] == account_id]

    latest_trans = tba['date'].max()

    tba = tba.set_index('date')
    tr = TIME_RES_LOOKUP[time_resolution]
    tr_label = tr['label']

    if tr_label == 'Total':
        value = tba['amount'].sum()
        data = {'value': value, 'date': latest_trans}
        bin_amounts = pd.DataFrame(data=data, index=[latest_trans])
        # TODO: should probably test for this in the callback and generate
        # a different figure, instead of hacking this into a barchart
    elif tr_label == 'Era':
        return None
    elif tr_label in ['Year', 'Quarter', 'Month']:
        resample_keyword = tr['resample_keyword']
        bin_amounts = tba.resample(resample_keyword).\
            sum()['amount'].\
            cumsum().\
            to_frame(name='value')
        bin_amounts['date'] = bin_amounts.index
        bin_amounts['value'] = bin_amounts['value']
    else:
        # bad input data
        return None

    try:
        marker_color = disc_colors[color_num]
    except IndexError:
        # don't ever run out of colors
        marker_color = 'var(--Cyan)'

    bin_amounts['customdata'] = account_id
    bin_amounts['texttemplate'] = '%{customdata}'  # workaround for passing variables through layers of plotly

    bar = go.Bar(
        name=account_id,
        x=bin_amounts.date,
        y=bin_amounts.value,
        customdata=bin_amounts.customdata,
        texttemplate=bin_amounts.texttemplate,
        textposition='auto',
        hovertemplate='%{customdata}: %{y:$,.0f}<br>as of %{x}<extra></extra>',
        marker_color=marker_color)

    return bar


def make_scatter(account_id: str, trans: pd.DataFrame, color_num: int = 0):
    """ returns scatter trace of input transactions
    """

    trace = go.Scatter(
        name=account_id,
        x=trans['date'],
        y=trans['amount'],
        text=trans['account'],
        ids=trans.index,
        mode='markers',
        marker=dict(
            symbol='circle'))
    return trace


def make_sunburst(
        trans: pd.DataFrame,
        start_date: np.datetime64 = None,
        end_date: np.datetime64 = None,
        SUBTOTAL_SUFFIX: str = None):
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
    sel_trans = positize(sel_trans)

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

            try:
                norm_subtotal = round(subtotal / duration)
            except OverflowError:
                norm_subtotal = 0
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
        marker={'line': {'color': 'white'}},
        maxdepth=3,
        hovertemplate='%{label}<br>%{value}',
        texttemplate='%{label}<br>%{value}',
    )

    figure.update_layout(
        font=big_font,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
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
    Simply reversing sign could result in a net-negative sum, which also breaks sunbursts.
    This function always returns a net-positive sum DataFrame of transactions, suitable for
    a sunburst."""

    if trans.sum(numeric_only=True)['amount'] < 0:
        trans['amount'] = trans['amount'] * -1

    return trans


def get_children(account_id, account_tree):
    """
    Return a list of tags of all direct child accounts of the input account.
    """
    return [x.tag for x in account_tree.children(account_id)]


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
    return trans


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
    # Remove any nodes from the root that have only 1 child.
    # I.e, replace A → B → (C, D) with B → (C, D)
    root_id = tree.root
    root_kids = tree.children(root_id)
    if len(root_kids) == 1:
        tree.update_node(root_kids[0].identifier, parent=None, bpointer=None)
        new_tree = tree.subtree(root_kids[0].identifier)
        return new_tree
    else:
        return tree


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
