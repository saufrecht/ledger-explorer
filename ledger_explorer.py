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



#######################################################################
# Declare the content of the page
#######################################################################
#######################################################################
# Callback functions
#######################################################################




if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0')
