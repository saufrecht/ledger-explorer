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
# All function definitions here, except for callbacks at the end
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


def purge_root(tree):
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

    tree = purge_root(tree)
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
    tba['bins'] = pd.cut(x=tba.date, bins=bins)
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
        text=eras['name'],
        textposition='bottom center',
        textfont=dict(
            size=12),
        line=dict(
            color=color_variant(disc_colors[color_num], 30),
            width=2),
        hovertemplate="<extra></extra>")

    return bar, era_value, era_name


def get_quarterly_bar(account, color_num=0):
    """ returns a go.Bar object with monthly summaries for the selected account """

    tba = trans[trans['account'] == account]
    m_amounts = tba.set_index('date').resample('Q').sum()['amount'] / 3
    try:
        marker_color = disc_colors[color_num]
    except IndexError:
        # don't ever run out of colors
        marker_color = 'var(--Cyan)'
    bar = go.Bar(
        name=account,
        x=m_amounts.index,
        y=m_amounts,
        customdata=[dict(account=account)],
        marker_color=marker_color,
        hovertemplate='%{y:$,.0f}/mo, Q ending %{x}')

    return bar


def get_children(account_id, account_tree):
    """
    Return a list of tags of all direct child accounts of the input account.
    """
    return [x.tag for x in account_tree.children(account_id)]


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
    Create bins for selecting periods of data.  If custom bins are
    not provided, make year-based bins.
    """

    all_data = pd.DataFrame({'start_date': [earliest_date], 'end_date': [latest_date], 'name': 'All'})
    all_data = all_data.reset_index(drop=True).set_index('name')
    try:
        data = pd.read_csv(source)
        data = data.astype({'start_date': 'datetime64'})
        data = data.astype({'end_date': 'datetime64'})
    except urllib.error.HTTPError:
        data = pd.DataFrame({'end_date': pd.date_range(start=earliest_date, end=latest_date, freq='Y')})
        data['start_date'] = data['end_date'].shift(1)
        data['name'] = data['end_date'].dt.year

    data = data.sort_values(by=['start_date'], ascending=False)
    data = data.reset_index(drop=True).set_index('name')

    if pd.isnull(data.iloc[0].end_date):
        data.iloc[0].end_date = latest_date
    if pd.isnull(data.iloc[-1].start_date):
        data.iloc[-1].start_date = earliest_date
    combined_data = pd.concat([all_data, data])

    print(combined_data)
    return combined_data


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
            y=0.9))

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

eras_dropdown_data = [dict(label=name, value=name) for name in eras.index]
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
    style_cell={'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'maxWidth': 0},
    page_size=30)


app.layout = html.Div(
    className="layout_box",
    children=[
        html.Div(
            className='account_burst dashbox',
            children=[
                html.Div(
                    className="control_bar",
                    children=[
                        html.H1(
                            id='titlebar',
                            children=['Ledger']),
                        html.Div(
                            style=dict(textAlign='right', padding='0 10px 0 0'),
                            children=['Era']),
                        dcc.Dropdown(
                            id='era_dropdown',
                            options=eras_dropdown_data,
                            clearable=True,
                            value=eras.index[0],
                            placeholder='Select Time Period')
                    ]),
                dcc.Graph(
                    id='account_burst',
                    figure=make_sunburst(account_tree, trans))
            ]),
        html.Div(
            className='time_series dashbox',
            children=[
                dcc.Graph(
                    id='transaction_time_series')
            ]),
        html.Div(
            className="trans_table dashbox",
            children=[
                trans_table
            ])
    ])

#######################################################################
# Callback functions
#######################################################################


@app.callback(
    Output('account_burst', 'figure'),
    [Input('era_dropdown', 'value')])
def apply_era_selector(selection):
    try:
        start_date = eras.loc[selection].start_date
        end_date = eras.loc[selection].end_date
    except IndexError:
        start_date = None
        end_date = None
    sun_fig = make_sunburst(account_tree, trans, start_date, end_date)
    return sun_fig


@app.callback(
    [Output('titlebar', 'children'),
     Output('transaction_time_series', 'figure')],
    [Input('account_burst', 'clickData')])
def apply_burst_click(clickData):
    """
    Clicking on a slice in the Sunburst updates the titlebar with the name of the
    now-active account and updates the transaction_time_series with the transactions:
    For a leaf account, chart transactions, and monthly averages by year or era.
    For a node account, chart monthly summaries of all subtree accounts.

    Changing transaction_time_series will trigger the next callback, which will
    update the transaction table
    transactions for that account
    """
    chart_fig = go.Figure(layout=chart_fig_layout)
    if clickData:
        click_account = clickData['points'][0]['id']
    else:
        click_account = []

    selected_accounts = []
    if click_account:
        title = f'{click_account}'
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
        pass

    if not selected_accounts:
        title = 'All'

    chart_fig.update_layout(dict(
        title={'text': title}))

    if len(selected_accounts) == 1:
        account = selected_accounts[0]
        chart_fig.add_trace(get_trace(account))
        try:
            era_bar, era_value, era_name = get_era_bar(account, eras=eras)
            chart_fig.add_trace(era_bar)
            chart_fig.add_trace(era_value)
            chart_fig.add_trace(era_name)
        except TypeError:
            pass
    elif len(selected_accounts) > 1:
        for i, account in enumerate(selected_accounts):
            chart_fig.add_trace(get_quarterly_bar(account, i))
        chart_fig.update_layout(
            barmode='stack',
            showlegend=True)
    else:
        pass

    return title, chart_fig


@app.callback(
    Output('trans_table', 'data'),
    [Input('transaction_time_series', 'selectedData'),
     Input('transaction_time_series', 'figure')])
def apply_selection_from_time_series(selectedData, figure):
    """
    Selecting specific points from the time series chart updates the
    transaction table.

    Reminder to self: When you think selectedData input is broken, remember
    that unaltered default action in the graph is to zoom, not to select.

    A Dash object can only be an Input to one callback, and an Output
    to one callback.  But we want to update the trans_table in two
    different ways: either by selecting an account in the sunburst, in
    which case the trans_table is all transactions in that account, or
    by selecting some specific dots in the transaction_time_series, in
    which case only those specific transactions should show up in the
    trans_table.  To make this possible, the sunburst updates the
    transaction_time_series, which then updates the trans_table in
    either of two ways:

    If the whole transaction_time_series figure is changed, then that
    triggers this callback, and the ids of all the transactions on the
    chart, inside figure['data'], comprise the transactions to include.

    Or, if selectedData is set by selecting some markers, that
    triggers this callback and updates the table with only those
    transactions.

    Or, if a bar in a barchart is clicked, that will also trigger selectedData,
    and the transactions comprising that bar marker will go to the table.

    Selecting a point on a scatter plot:

    Selected: {'points': [{'curveNumber': 0, 'pointNumber': 53, 'pointIndex': 53, 'x': '2017-11-08', 'y': 861, 'id': 3997, 'text': 'Teresa'}]}  # NOQA

    Selecting a bar:

    Selected: {'points': [{'curveNumber': 3, 'pointNumber': 1, 'pointIndex': 1, 'x': '2015-12-31', 'y': 1543.6666666666667, 'label': '2015-12-31', 'value': 1543.6666666666667}]},  # NOQA

    Scatter plot has an ID, bar doesn't.

    """
    selected_ids = []
    selected_accounts = []
    filtered_trans = []
    # catch clicks
    if selectedData:
        # figure out if the selection is a quarterly bar, or a point or group of transactions
        # if it has ids in the first curve, it's a set of transactions.  Otherwise, it's a bar.
        points = selectedData['points']
        try:
            selected_ids = [i['id'] for i in list(filter(lambda x: x['curveNumber'] == 0, points))]
        except KeyError:
            # debugging selecting multiple bar segments
            # DEBUG
            pass
        if len(selected_ids) > 0:
            # If IDs are present, assume it's a selection of one or multiple individual points or bars.
            filtered_trans = trans[trans.index.isin(selected_ids)]
        else:
            # assume this is a click on a single bar in barchart.  Reverse-engineer the bar
            # parameters
            curve = points[0]
            curve_num = curve['curveNumber']
            end_date = pd.to_datetime(curve['x'])
            start_date = end_date - pd.tseries.offsets.QuarterBegin(n=1, startingMonth=1)
            # get the account from the full figure
            traces = locals()['figure']['data']
            try:
                account = traces[curve_num]['customdata'][0]['account']
            except IndexError:
                # debugging
                pass
            filtered_trans = trans[
                (trans['account'] == account) &
                (trans['date'] >= start_date) &
                (trans['date'] <= end_date)]
    elif figure:
        for trace in figure['data']:
            ttype = trace.get('type', None)
            # should only be bars or scatter (plus summary & labels)
            if ttype == 'bar':
                try:
                    trace_account = trace['customdata'][0]['account']
                    selected_accounts.append(trace_account)
                except KeyError:
                    print(f'DEBUG: Bad Assumption Warning: unable to get account from trace {trace}.')
            elif ttype == 'scatter':
                # hack: rather than try to pass along account name reliable, just grab all of the transactions
                # in the scatter plot
                trace_ids = trace.get('ids', [])
                selected_ids += trace_ids
        if selected_ids:
            filtered_trans = trans[trans.index.isin(selected_ids)]
        elif selected_accounts:
            filtered_trans = trans[trans['account'].isin(selected_accounts)]

    if len(filtered_trans) > 0:
        pass
    else:
        # if no transactions are selected, show all of them.
        filtered_trans = trans.copy()

    # format date so minutes don't show in trans_table
    filtered_trans['date'] = filtered_trans['date'].dt.strftime('%Y-%m-%d')

    return filtered_trans.to_dict('records')


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
