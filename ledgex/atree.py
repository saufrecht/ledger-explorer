import json

import pandas as pd
from treelib import Tree
from treelib import exceptions as tle


from ledger import Ledger
from app import app
from params import CONST


class ATree(Tree):
    """Subclass of treelib Tree for holding ledger-related functions.

    ROOT_TAG and ROOT_ID are the preferred default tag and ID of root
    nodes, but current design doesn't guarantee they'll always be
    there.  If it were, then either stem pruning would not be
    possible, or other root nodes might have to be overwritten.  E.g.,
    should the tree "Root → B → C → branches…" be truncated to "Root →
    branches…", or to "c → branches…"?  The latter is currently implemented.

    """

    ROOT_TAG = "[Total]"
    ROOT_ID = "root"

    def pp(self, node: str = None):  # pragma: no cover      DEBUG helper function
        if not node:
            node = self.root
        w_node = self[node]
        try:
            leaf_total = w_node.data.get("leaf_total", 0)
            total = w_node.data.get("total", 0)
        except AttributeError:
            leaf_total = 0
            total = 0
        print(
            f"{self.depth(w_node) * '   '} {w_node.identifier} ({w_node.tag}) {leaf_total} {total}"
        )
        for child in self.children(node):
            self.pp(child.identifier)

    @classmethod
    def cast(cls, tree: Tree):
        """ Cast a Tree into an ATree """
        tree.__class__ = cls
        return tree

    def show_to_string(self) -> str:  # pragma: no cover
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

    def to_json(self, sort=True, reverse=False):
        """Override Tree.to_json with a version that doesn't error if tree is
        empty.  Due to to_dict implementation in parent class, this
        stores only tag and child relationships, not ids or data.
        """
        if len(self) > 0:
            return json.dumps(
                self.to_dict(with_data=False, sort=sort, reverse=reverse)
            )
        else:
            return ""

    @classmethod
    def from_json(cls, atree_j: str):
        """Parent class doesn't have this.  As with to_json, this stores only
        tags and child relationships, so it doesn't support id or
        data, so it's only useable for limited purposes.
        """
        def _dict_to_branch(atreedict, parent: str = None):
            if isinstance(atreedict, dict):
                tuple_list = []
                for node in atreedict.keys():
                    tuple_list = tuple_list + [(node, parent)]
                    try:
                        for child in atreedict[node]["children"]:
                            tuple_list = tuple_list + _dict_to_branch(child, parent=node)
                    except KeyError:
                        pass
            else:
                tuple_list = [(atreedict, parent)]
            return tuple_list
        tuple_list = _dict_to_branch(json.loads(atree_j))
        return cls.from_list_of_tuples(tuple_list)

    def get_dict_of_paths(self) -> dict:
        """Return full paths as primary internal representation of account
        tree. Note that ':' here is an internal detail, and so not
        affected by DELIM constant or user input

        """
        res = []
        for leaf in self.all_nodes():
            res.append([nid for nid in self.rsearch(leaf.identifier)][::-1])
        return {x[-1]: ":".join(x) for x in res}

    def get_children_tags(self, account_id: int):
        """
        Return a list of tags of all direct child accounts of the input account.
        """
        try:
            child_tags = [x.tag for x in self.children(account_id)]
            return child_tags
        except tle.NodeIDAbsentError as E:
            app.logger.warning(f"A specified node is missing from the account tree: {E}")
            return []

    def get_children_ids(self, account_id: int):
        """
        Return a list of tags of all direct child accounts of the input account.
        """
        try:
            child_ids = [x.identifier for x in self.children(account_id)]
            return child_ids
        except tle.NodeIDAbsentError as E:
            app.logger.warning(f"A specified node is missing from the account tree: {E}")
            return []

    def get_descendent_ids(self, account_id: str = None) -> list:
        """
        Return a list of ids of all descendent accounts of the input account.
        """
        if (not account_id) or (len(account_id) == 0):
            account_id = self.root
        try:
            # TODO: make this comparison case-insensitive
            subtree_nodes = self.subtree(account_id).all_nodes()
            descendent_list = [x.identifier for x in subtree_nodes if x.identifier != account_id]
        except tle.NodeIDAbsentError:
            descendent_list = []
        return descendent_list

    def get_lineage_ids(self, account_id: str) -> list:
        """
        Return a list of ids of all parent accounts of the input account up to root
        """
        if account_id == self.root:
            lineage = []
        else:
            try:
                parent = self.parent(account_id).identifier
                if parent == self.root:
                    lineage = [self.root]
                else:
                    lineage = self.get_lineage_ids(parent) + [parent]
            except tle.NodeIDAbsentError:
                lineage = []

        return lineage

    def trim_excess_root(self):
        """ Returns a version of the tree with no single-child root
        nodes (recursively). Does not modify the object."""
        root_id = self.root
        branches = self.children(root_id)
        if len(branches) == 1:
            new_tree = self.subtree(branches[0].identifier)
            new_atree = ATree.cast(new_tree)
            new_tree[new_tree.root].bpointer = None
            return new_atree.trim_excess_root()
        else:
            return self

    @classmethod
    def from_list_of_tuples(cls, node_list: list):
        """Convert a list of (node tag, node parent tag) tuples to an ATree
        with one root, trimmed of any long stem.  This function is the
        shared foundation of all other from_* ATree creation
        functions.  It creates a new root with default values, to
        guarantee a single-rooted tree. This would create an extra root
        node with each trip, but trimming prevents that.

        First pass creates all nodes.  Second pass builds all
        relationships.  This way, out-of-order data won't cause problems.
        """
        atree = cls()
        atree.create_node(tag=cls.ROOT_TAG, identifier=cls.ROOT_ID)
        atree.root = cls.ROOT_ID
        parent_list = [(cls.ROOT_ID, None)]
        for row in node_list:
            try:
                name = row[0]
                atree.create_node(tag=name, identifier=name, parent=atree.root)
                parent_list = parent_list + [row]
            except IndexError:
                app.logger.info(f"Bad data while creating account tree: {row}.  Skipping.")
                continue
            except tle.DuplicatedNodeIdError:
                pass
        for row in parent_list:
            name = row[0]
            try:
                parent = row[1]
                if parent is None:
                    parent = atree.root
            except IndexError:
                parent = atree.root
            if name != parent:
                try:
                    atree.move_node(name, parent)
                except tle.NodeIDAbsentError:
                    pass
            else:
                pass
        return atree.trim_excess_root()

    @classmethod
    def from_names(cls, full_names: pd.Series, delim: str = CONST["delim"]) -> Tree:
        """Extract all accounts from a list of Gnucash-like account paths.
        Assumes each account name is a full path, delimiter is :.
        """
        tuple_list = []
        for account in full_names.unique():
            try:
                if account and len(account) > 0:
                    nodes = account.split(delim)  # example: Foo:Bar:Baz
                    for i, node_tag in enumerate(nodes):
                        if i == 0:
                            parent = None
                        else:
                            parent = nodes[i - 1]
                        tuple_list = tuple_list + [(node_tag, parent)]
            except KeyError as E:
                app.logger.debug(f'Key error {E} converting account tree from names')
        return cls.from_list_of_tuples(tuple_list)

    @classmethod
    def from_parents(cls, parent_list: pd.DataFrame) -> Tree:
        """Extract all accounts from dataframe of parent-child relationships.
        Similar assumptions as cls.from_names, except: parents may not
        exist when needed, and thus should be created directly under node
        when needed, and then moved to the right place in a second pass.

        """
        clean_list = parent_list[[CONST["account_col"], CONST["parent_col"]]]
        tuple_list = []
        for row in clean_list.itertuples(index=False):
            tuple_list = tuple_list + [(row[0], row[1])]
        return cls.from_list_of_tuples(tuple_list)

    @staticmethod
    def stuff_tree_into_trans(trans: Ledger, tree: Tree) -> pd.DataFrame:
        """Convert the tree into full account name format and add/update the
        full account field in trans accordingly.
        This should probably be a static method on TransFrame, once that Class exists."""
        paths = tree.get_dict_of_paths()
        trans[CONST["fan_col"]] = trans[CONST["account_col"]].map(paths)
        return trans

    def append_sums_from_trans(self, trans: Ledger, prorate_fraction: int = 1):
        """Calculate the subtotal for each node (direct subtotal only, no
        children) in the tree, based on exactly provided transaction
        frame, and return it within a new account tree

        TODO: this modifies the tree in place, but for consistency and
        flexibility, it should return a new tree

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

    def summarize_to_other(self, node):  # pragma: no cover
        """
        TODO: fix, and put back into use, with new UI to control it
        TODO: this modifies the tree in place, but for consistency and
        flexibility, it should return a new tree

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

    def roll_up_subtotals(self, prevent_negatives: bool = True):
        """Return a version of the atree that has subtotals for each
        node.  To accommodate this, change the returned tree in several
        other ways:
          1. Append Subtotal to the name of any node with children
          2. For any node with children and its own value, move its value
             to a new child node (see below)
          3. Remove any negative children and their siblings, preserving
             their net value in the rollup.

        Sunburst is very very finicky and wants the subtotals to be
        exactly correct and never missing, so this builds them
        directly from the leaf totals, as opposed to generating
        subtotals from the original dataframe, in order to avoid
        rounding and other fatal problems.

        In order for the tree to be rendered as a hierarchical figure
        with area—like a sunburst or treemap—it may not contain any
        negative values, because that would require taking up a
        negative amount of area in 2D space, which is impossible.  By
        default, any negative-value node is pruned.  Sunburst also
        requires node totals to exactly match the value of
        descendents, so any children of a negative node must also be
        pruned.  Example: A contains A¹=50 and A²=−30.  This function
        will return A=20 with no children.

        If a node has a total, and has a child with a total, then
        there is no way to see what the node's total is in isolation.
        So, any node that has value, and has children, has to get
        split into an empty container node and a leaf node with the
        value.  Then, there has to be a way to differentiate between
        clicking on the sub-total and clicking on the leaf.  Do this
        by appending a magic string to the id of the leaf.  Then, use
        the tag as the key to transaction.account.  This will cause
        the parent tag, 'XX Subtotal', to fail matches, and the child,
        which is labeled 'XX Leaf' but tagged 'XX' to match.

                       BEFORE               ||                         AFTER
        -----------------------------------------------------------------------------------------
        id  | parent  | tag  | leaf_total   || id     | parent  | tag         | leaf_total | total
        A   |         | A    |         50   || A      |         | A Subtotal  |            |    72
        B   | A       | B    |         22   || A Leaf | A       | A           |         50 |    50
                                            || B      | A       | B           |         22 |    22

        """

        def set_node_total(atree, node):
            """Recursive function to operate on the atree.  Uses 'leaf_total' for
            all transactions that belong to this node's account, and
            'total' for the final value for the node, including
            descendents.
            """
            node_id: str = node.identifier
            tag: str = node.tag
            try:
                leaf_total: int = node.data.get("leaf_total", 0)
            except AttributeError:
                # in case it doesn't even have a data node
                leaf_total = 0
            if len(atree.children(node_id)) > 0 and leaf_total != 0:
                # if it's not childless, and has its own value, move
                # that value to a leaf.  do this
                new_leaf_id = node_id + CONST["leaf_suffix"]
                node.data["leaf_total"] = 0
                atree.create_node(
                    identifier=new_leaf_id,
                    tag=tag,
                    parent=node_id,
                    data=dict(total=leaf_total, leaf_total=leaf_total),
                )
                running_subtotal: int = 0
            else:
                running_subtotal: int = leaf_total
            children: ATree = atree.children(node_id)
            if children:
                negative_child: bool = False
                # re-label the node as subtotal
                if node_id != self.root:
                    subtotal_tag = tag + CONST["subtotal_suffix"]
                    atree.update_node(node_id, tag=subtotal_tag)
                for child in children:
                    # recurse to get subtotals.
                    child_total = set_node_total(atree, child)
                    if child_total < 0:
                        negative_child = True
                    running_subtotal += child_total
                if prevent_negatives and negative_child:
                    # prune all children
                    for child in children:
                        try:
                            atree.remove_node(child.identifier)
                        except tle.NodeIDAbsentError:
                            pass
            if running_subtotal != 0:
                if node.data:
                    node.data["total"] = running_subtotal
                else:
                    node.data = {"total": running_subtotal}
            else:
                try:
                    atree.remove_node(node_id)
                except tle.NodeIDAbsentError:
                    pass

            return running_subtotal

        root_id = self.root
        new_tree = Tree(self.subtree(root_id), deep=True)
        new_atree = ATree.cast(new_tree)
        set_node_total(new_atree, new_atree[root_id])
        return new_tree
