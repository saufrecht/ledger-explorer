import json

import pandas as pd
from treelib import Tree
from treelib import exceptions as tle

from ledgex.app import app
from ledgex.params import CONST
from ledgex.ledger import Ledger


class ATree(Tree):
    """ Subclass of treelib Tree for holding extra functions """

    ROOT_TAG = "[Total]"
    ROOT_ID = "root"

    def pp(self, node="root"):  # DEBUG
        w_node = self[node]
        try:
            leaf_total = w_node.data.get("leaf_total")
        except AttributeError:
            leaf_total = 0
        print(
            f"{self.depth(w_node) * '   '} {w_node.identifier} ({w_node.tag}) {leaf_total}"
        )
        for child in self.children(node):
            self.pp(child.identifier)

    @classmethod
    def cast(cls, tree: Tree):
        """ Cast a Tree into an ATree """
        tree.__class__ = cls
        return tree

    def show_to_string(self) -> str:
        """ Alternative to the parent method show(), which outputs to stdout. """

        if len(self) == 0:
            return ""

        self._reader = ""

        def write(line):
            self._reader += line.decode("utf-8") + "\n"

        try:
            self._Tree__print_backend(func=write)
        except tle.NodeIDAbsentError:
            app.logger.info("Tree is empty")

        return self._reader

    def to_json(self, with_data=False, sort=True, reverse=False):
        """Override Tree.to_json with a version that doesn't error if tree is empty """
        if len(self) > 0:
            return json.dumps(
                self.to_dict(with_data=with_data, sort=sort, reverse=reverse)
            )
        else:
            return ""

    def dict_of_paths(self) -> dict:
        """Return full paths as primary internal representation of account
        tree. Note that ':' here is an internal detail, and so not
        affected by DELIM constant or user input

        """
        res = []
        for leaf in self.all_nodes():
            res.append([nid for nid in self.rsearch(leaf.identifier)][::-1])
        return {x[-1]: ":".join(x) for x in res}

    def trim_excess_root(self):
        """If root node has only one child, return a tree with that child as the new root."""
        root_id = self.root
        branches = self.children(root_id)
        if len(branches) == 1:
            self.update_node(branches[0].identifier, parent=None, bpointer=None)
            new_tree = self.subtree(branches[0].identifier)
            new_atree = ATree.cast(new_tree)
            return new_atree.trim_excess_root()
        else:
            return self

    @classmethod
    def from_names(cls, full_names: pd.Series, delim: str = CONST["delim"]) -> Tree:
        """extract all accounts from a list of Gnucash-like account paths

        Assumes each account name is a full path, delimiter is :.
        Creating each node the first time it's seen should handle these cases:
        - Parent accounts with no transactions and therefore no distinct rows
        - Nodes are presented out of order
        data, so reconstruct the complete tree implied by the
        transaction data.

        If there are multiple heads in the data, they will all belong
        to root, so the tree will still be a DAG

        """
        clean_list = full_names.unique()
        tree = ATree()
        tree.create_node(tag=tree.ROOT_TAG, identifier=tree.ROOT_ID)
        for account in clean_list:
            try:
                if account and len(account) > 0:
                    branches = account.split(delim)  # example: Foo:Bar:Baz
                    for i, branch in enumerate(branches):
                        name = branch
                        if i == 0:
                            parent = tree.ROOT_ID
                        else:
                            parent = branches[i - 1]
                        if not tree.get_node(name):
                            tree.create_node(tag=name, identifier=name, parent=parent)
            except tle.NodeIDAbsentError as E:
                app.logger.warning(f"Problem building account tree: {E}")
                # TODO: write some bad sample data to see what errors we should catch here.
                #  presumably: account not a list; branch in account not a string
                continue
        # tree = tree.trim_excess_root()  TODO waiting for trim_excess_root to get fixed
        return tree

    def get_children_tags(self, account_id: int):
        """
        Return a list of tags of all direct child accounts of the input account.
        """
        return [x.tag for x in self.children(account_id)]

    def get_children_ids(self, account_id: int):
        """
        Return a list of tags of all direct child accounts of the input account.
        """
        return [x.identifier for x in self.children(account_id)]

    def get_descendents(self, account_id: str) -> list:
        """
        Return a list of tags of all descendent accounts of the input account.
        """
        if (not account_id) or (len(account_id) == 0):
            return []
        try:
            # TODO: make this comparison case-insensitive
            subtree_nodes = self.subtree(account_id).all_nodes()
            descendent_list = [x.tag for x in subtree_nodes if x.tag != account_id]
        except tle.NodeIDAbsentError:
            descendent_list = []

        return descendent_list

    @classmethod
    def from_parents(cls, parent_list: pd.DataFrame) -> Tree:
        """Extract all accounts from dataframe of parent-child relationships.
        Similar assumptions as cls.from_names, except: parents may not
        exist when needed, and thus should be created directly under node
        when needed, and then moved to the right place in a second pass.

        """
        clean_list = parent_list[[CONST["account_col"], CONST["parent_col"]]]
        tree = cls()
        tree.create_node(tag=cls.ROOT_TAG, identifier=cls.ROOT_ID)
        for row in clean_list.itertuples(index=False):
            try:
                name = row[0]  # index assumes clean_list fixed column order
                parent = row[1]
                if not tree.get_node(parent):
                    tree.create_node(tag=parent, identifier=parent, parent=cls.ROOT_ID)
                if not tree.get_node(name):
                    tree.create_node(tag=name, identifier=name, parent=parent)
            except tle.NodeIDAbsentError as E:
                app.logger.warning(f"Error creating parent list: {E}")
                # TODO: write some bad sample data to see what errors we should catch here.
                #  presumably: account not a list; branch in account not a string
                continue
        # second pass, to get orphaned nodes in the right place
        for row in clean_list.itertuples(index=False):
            try:
                name = row[0]
                parent = row[1]
                if name == parent:
                    app.logger.info(
                        f"Cannot move {name} to be child of {parent}.  Skipping."
                    )
                else:
                    tree.move_node(name, parent)
            except tle.NodeIDAbsentError as E:
                app.logger.warning(f"Error moving node: {E}")
                # TODO: write some bad sample data to see what errors we should catch here.
                #  presumably: account not a list; branch in account not a string
                continue
        return tree

    @staticmethod
    def stuff_tree_into_trans(trans: Ledger, tree: Tree) -> pd.DataFrame:
        """Convert the tree into full account name format and add/update the
        full account field in trans accordingly.
        This should probably be a static method on TransFrame, once that Class exists."""
        paths = tree.dict_of_paths()
        trans[CONST["fan_col"]] = trans[CONST["account_col"]].map(paths)
        return trans

    def append_sums_from_trans(self, trans: Ledger, prorate_fraction: int = 1):
        """Calculate the subtotal for each node (direct subtotal only, no
        children) in the tree, based on exactly provided transaction
        frame, and return it within a new account tree
        """
        trans = trans.reset_index(drop=True).set_index(CONST["account_col"])
        subtotals = trans.groupby(CONST["account_col"]).sum()["amount"]
        for node in self.all_nodes():
            try:
                subtotal = subtotals.loc[node.tag]
            except KeyError:
                # These should be nodes without leaf_totals, and therefore
                # not present in the subtotals DataFrame
                continue
            try:
                prorated_subtotal = round(subtotal * prorate_fraction)
            except OverflowError:
                prorated_subtotal = 0
            node.data = {"leaf_total": prorated_subtotal}
        return self

    def summarize_to_other(self, node):
        """
        TODO: fix, and put back into use, with new UI to control it

        If there are more than (MAX_SLICES - 2) children in this node,
        group the excess children into a new 'other' node.
        Recurse to do this for all children, including any 'other' nodes
        that get created.

        The "-2" accounts for the Other node to be created, and for
        one-based vs zero-based counting.
        """
        node_id = node.identifier
        children = self.children(node_id)
        if len(children) > (CONST["max_slices"] - 2):
            other_id = CONST["other_prefix"] + node_id
            other_subtotal = 0
            self.create_node(
                identifier=other_id,
                tag=other_id,
                parent=node_id,
                data=dict(total=other_subtotal),
            )
            total_list = [
                (dict(identifier=x.identifier, total=x.data["total"])) for x in children
            ]
            sorted_list = sorted(total_list, key=lambda k: k["total"], reverse=True)
            for i, child in enumerate(sorted_list):
                if i > (CONST["max_slices"] - 2):
                    other_subtotal += child["total"]
                    self.move_node(child["identifier"], other_id)
            self.update_node(other_id, data=dict(total=other_subtotal))

        children = self.children(node_id)
        for child in children:
            self.summarize_to_other(child)

    def roll_up_subtotals(self, prevent_negatives: bool = False):
        """Modifies the tree in place, setting a subtotal for all branch
        nodes.

        TODO: If there are any negative children, pass back a flag to
        add warning text to the hovertext/ledgend.  e.g. "One or more
        nodes show contains a mix of negative and positive sub-nodes,
        which cannot be displayed in a sunburst.  Narrow your
        selection to get more depth."

        Sunburst is very very finicky and wants the subtotals to be
        exactly correct and never missing, so this builds them
        directly from the leaf totals, as opposed to generating
        subtotals from the original dataframe, in order to avoid
        rounding and other fatal problems.

        In order for the tree to be rendered as a hierarchical figure
        with area—like a sunburst or treemap—it may not contain any
        negative values, because that would require taking up a
        negative amount of area on in the figure, which is impossible.
        So, wehave the option to roll up any negative nodes until a
        positive parent node is achieved.  Example: A contains A¹=50
        and A²=−30.  This function will return A=20 with no children.

        If a node has a total, and has a child with a total, then there
        is no way to see what the node's total is in isolation.  So,
        any node that has value, and has children


        If a leaf_total is moved out of a subtotal, there has to be a
        way to differentiate between clicking on the sub-total and
        clicking on the leaf.  Do this by appending a magic string to
        the id of the leaf.  Then, use the tag as the key to
        transaction.account.  This will cause the parent tag, 'XX
        Subtotal', to fail matches, and the child, which is labeled
        'XX Leaf' but tagged 'XX' to match.
        BEFORE                          | AFTER
        id   parent   tag  leaf_total   | id       parent   tag          leaf_total    total
        A             A            50   | A                 A Subtotal                    72
        B    A        B            22   | A Leaf   A        A                    50       50
                                        | B        A        B                    22       22

        """

        def set_node_total(tree, node):
            """

            Recursively set the value of a node as the sum of its descendents' totals.
            Alters the tree as it goes, making subtotals and leafs where needed for clarity,
            and fixing unmappable nodes if so flagged.
            Uses 'leaf_total' for all transactions that belong to this node's account,
            and 'total' for the final value for the node, including descendents.
            """
            node_id: str = node.identifier
            tag: str = node.tag
            leaf_total: int = 0
            try:
                leaf_total = node.data.get("leaf_total", 0)
            except AttributeError:
                # in case it doesn't even have a data node
                pass
            running_subtotal: int = leaf_total
            children: ATree = tree.children(node_id)
            negative_child: bool = False
            if children:
                # make it a subtotal
                if node_id != tree.ROOT_ID:
                    subtotal_tag = tag + CONST["subtotal_suffix"]
                    tree.update_node(node_id, tag=subtotal_tag)
                for child in children:
                    # recurse to get subtotals.
                    child_total = set_node_total(tree, child)
                    running_subtotal += child_total
                    if child_total < 0:
                        negative_child = True
                node.data = {"total": running_subtotal}
                if prevent_negatives and negative_child:
                    # If any of the children are negative, the
                    # parent's subtotal won't match the sum of its
                    # children, so prune all the children
                    for child in children:
                        try:
                            tree.remove_node(child.identifier)
                        except tle.NodeIDAbsentError:
                            pass
                    # TODO: here's where to add a flag to get passed back
                    negative_child = False
                elif leaf_total > 0:
                    # if it's not childless, and has its own value,
                    # move that value to a leaf
                    new_leaf_id = node_id + CONST["leaf_suffix"]
                    node.data["leaf_total"] = 0
                    tree.create_node(
                        identifier=new_leaf_id,
                        tag=tag,
                        parent=node_id,
                        data=dict(total=leaf_total),
                    )
            if node.data:
                node.data["total"] = running_subtotal
            else:
                node.data = {"total": running_subtotal}
            # If this node and descendents total to zero or less, purge
            if running_subtotal == 0:
                try:
                    tree.remove_node(node_id)
                except tle.NodeIDAbsentError:
                    pass

            return running_subtotal

        root = self.get_node(self.root)
        set_node_total(self, root)
