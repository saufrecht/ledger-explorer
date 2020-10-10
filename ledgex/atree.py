import json
import pandas as pd
from treelib import Tree
from treelib import exceptions as tle


from ledgex.app import app
from ledgex.params import CONST


class ATree(Tree):
    """ Subclass of treelib Tree for holding extra functions """

    ROOT_TAG = '[Total]'
    ROOT_ID = 'root'

    def show_to_string(self) -> str:
        """ Alternative to the parent method show(), which outputs to stdout.
        Work in progress, still prints to stdout."""

        if len(self) == 0:
            return ''

        self._reader = ''

        def write(line):
            self._reader += line.decode('utf-8') + "\n"

        try:
            self._Tree__print_backend(func=write)
        except tle.NodeIDAbsentError:
            print('Tree is empty')

        return self._reader

    def to_json(self, with_data=False, sort=True, reverse=False):
        """Override Tree.to_json with a version that doesn't error if tree is empty """
        if len(self) > 0:
            return json.dumps(self.to_dict(with_data=with_data, sort=sort, reverse=reverse))
        else:
            return ''

    def dict_of_paths(self) -> dict:
        """Return full paths as primary internal representation of account
         tree. Note that ':' here is an internal detail, and so not
         affected by DELIM constant or user input

        """
        res = []
        for leaf in self.all_nodes():
            res.append([nid for nid in self.rsearch(leaf.identifier)][::-1])
        return {x[-1]: ':'.join(x) for x in res}

    @classmethod
    def cast(cls, tree: Tree):
        """ Cast a Tree into an ATree """
        tree.__class__ = cls
        return tree

    def trim_excess_root(self):
        """ Remove any nodes from the root that have only 1 child.
        I.e, replace A → B → (C, D) with B → (C, D)
        It feels like this should be an instance method, but when that was tried,
        ran into problems with subtleties of subclassing and scope:
          AttributeError: 'Tree' object has no attribute 'trim_excess_root'
        Method was in inspect and dir() but not __dir__.  :(
        """
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
    def from_names(cls, full_names: pd.Series, delim: str = CONST['delim']) -> Tree:
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
                            parent = branches[i-1]
                        if not tree.get_node(name):
                            tree.create_node(tag=name,
                                             identifier=name,
                                             parent=parent)
            except tle.NodeIDAbsentError as E:
                app.logger.warning(f'Problem building account tree: {E}')
                # TODO: write some bad sample data to see what errors we should catch here.
                #  presumably: account not a list; branch in account not a string
                continue
        # tree = tree.trim_excess_root()  TODO waiting for trim_excess_root to get fixed
        return tree

    def get_children(self, account_id: int):
        """
        Return a list of tags of all direct child accounts of the input account.
        """
        return [x.tag for x in self.children(account_id)]

    def get_descendents(self, account_id: str) -> list:
        """
        Return a list of tags of all descendent accounts of the input account.
        """
        if (not account_id) or (len(account_id) == 0):
            return []
        try:
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
        clean_list = parent_list[[CONST['account_col'], CONST['parent_col']]]
        tree = cls()
        tree.create_node(tag=cls.ROOT_TAG, identifier=cls.ROOT_ID)
        for row in clean_list.itertuples(index=False):
            try:
                name = row[0]  # index assumes clean_list fixed column order
                parent = row[1]
                if not tree.get_node(parent):
                    tree.create_node(tag=parent,
                                     identifier=parent,
                                     parent=cls.ROOT_ID)
                if not tree.get_node(name):
                    tree.create_node(tag=name,
                                     identifier=name,
                                     parent=parent)
            except tle.NodeIDAbsentError as E:
                app.logger.warning(f'Error creating parent list: {E}')
                # TODO: write some bad sample data to see what errors we should catch here.
                #  presumably: account not a list; branch in account not a string
                continue

        # second pass, to get orphaned nodes in the right place
        for row in clean_list.itertuples(index=False):
            try:
                name = row[0]
                parent = row[1]
                tree.move_node(name, parent)
            except tle.NodeIDAbsentError as E:
                app.logger.warning(f'Error moving node: {E}')
                # TODO: write some bad sample data to see what errors we should catch here.
                #  presumably: account not a list; branch in account not a string
                continue

        return tree

    @staticmethod
    def stuff_tree_into_trans(trans: pd.DataFrame, tree: Tree) -> pd.DataFrame:
        """ Convert the tree into full account name format and add/update the
        full account field in trans accordingly.
        This should probably be a static method on TransFrame, once that Class exists."""
        paths = tree.dict_of_paths()
        trans[CONST['fan_col']] = trans[CONST['account_col']].map(paths)
        return trans
