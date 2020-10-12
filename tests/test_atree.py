import pandas as pd
import pytest

from ledgex.atree import ATree
from ledgex.params import CONST

skinny_tree: ATree = ATree()
skinny_tree.create_node('Lower Trunk', 'lt')
skinny_tree.create_node('Middle Trunk', 'mt', parent='lt')
skinny_tree.create_node('Top Trunk', 'tt', parent='mt')
skinny_tree.create_node('Branch Alpha', 'ba', parent='tt')
skinny_tree.create_node('Branch Beta', 'bb', parent='tt')
skinny_tree.create_node('Branch Gamma', 'bg', parent='tt')

fan = pd.Series(['Continents:All Africa:Senegal', 'Continents:All Africa:Seychelles', 'Continents:All Africa:Sierra Leone', 'Continents:All South America:Colombia', 'Continents:All South America:Argentina', 'Entities:MERCOSUR', 'Entities:EU'])  # NOQA

parents = pd.DataFrame({CONST['account_col']: ['Continents', 'All Africa', 'Senegal', 'Seychelles', 'Sierra Leone', 'All South America', 'Colombia', 'Argentina', 'Entities', 'MERCOSUR', 'EU'], CONST['parent_col']: ['root', 'Continents', 'All Africa', 'All Africa', 'All Africa', 'Continents', 'All South America',  'All South America', 'root', 'Entities', 'Entities']})  # NOQA

delim_pipe = pd.Series(['Continents|All Africa|Senegal', 'Continents|All Africa|Seychelles', 'Continents|All Africa|Sierra Leone', 'Continents|All South America|Colombia', 'Continents|All South America|Argentina', 'Entities|MERCOSUR', 'Entities|EU'])  # NOQA

fan_tree = ATree()
fan_tree.create_node(tag=ATree.ROOT_TAG, identifier=ATree.ROOT_ID)
fan_tree.create_node('Continents', 'Continents', parent=ATree.ROOT_ID)
fan_tree.create_node('Entities', 'Entities', parent=ATree.ROOT_ID)
fan_tree.create_node('All Africa', 'All Africa', parent='Continents')
fan_tree.create_node('All South America', 'All South America', parent='Continents')
fan_tree.create_node('MERCOSUR', 'MERCOSUR', parent='Entities')
fan_tree.create_node('EU', 'EU', parent='Entities')
fan_tree.create_node('Senegal', 'Senegal', parent='All Africa')
fan_tree.create_node('Seychelles', 'Seychelles', parent='All Africa')
fan_tree.create_node('Sierra Leone', 'Sierra Leone', parent='All Africa')
fan_tree.create_node('Argentina', 'Argentina', parent='All South America')
fan_tree.create_node('Colombia', 'Colombia', parent='All South America')


@pytest.fixture
def naughty_tree():
    import treelib
    tree = ATree()
    blns_list = []
    tree.create_node(tag=ATree.ROOT_TAG, identifier=ATree.ROOT_ID)
    with open('tests/blns.txt') as f:
        parent = ATree.ROOT_ID
        for line in f:
            if len(line) > 0 and line != '':
                try:
                    tree.create_node(tag=line, identifier=line, parent=parent)
                    parent = line
                    blns_list.append(line)
                except treelib.exceptions.DuplicatedNodeIdError:
                    pass
    return (tree, blns_list)


class TestSkinnyTrim:
    """ Should remove lower and middle trunk """

    def test_lt(self):
        assert (skinny_tree.get_node('lt').tag == 'Lower Trunk')

    def test_mt(self):
        assert (skinny_tree.get_node('mt').tag == 'Middle Trunk')

    short_tree: ATree = skinny_tree.trim_excess_root()

    def test_lt_gone(self):
        assert (self.short_tree.get_node('lt') is None)

    def test_mt_gone(self):
        assert (self.short_tree.get_node('mt') is None)

    def test_tt(self):
        title = self.short_tree.get_node('tt').tag
        assert (title == 'Top Trunk')

    def test_root(self):
        id = self.short_tree.root
        assert (id == 'tt')


class TestSkinnyString:
    """ render a string """

    def test_show(self):
        assert skinny_tree.show_to_string() == 'Lower Trunk\n└── Middle Trunk\n    └── Top Trunk\n        ├── Branch Alpha\n        ├── Branch Beta\n        └── Branch Gamma\n'  # NOQA


class TestJson:
    """ test render skinny_tree and check for correct output"""
    def test_skinny_to_json(self):
        assert skinny_tree.to_json() == '{"Lower Trunk": {"children": [{"Middle Trunk": {"children": [{"Top Trunk": {"children": ["Branch Alpha", "Branch Beta", "Branch Gamma"]}}]}}]}}'  # NOQA

    def test_naughty_to_json(self, naughty_tree):
        """The naughty strings file has 666 non-blank rows, but some rows are
        the same as '' from python's perspective, so there seem to be
        626 valid rows.  Kind of hard to test.
        """
        n_tree = naughty_tree[0]
        n_list = naughty_tree[1]
        assert n_tree.depth() == 626
        for item in n_list:
            assert n_tree[item].tag == item


class TestFroms:
    """ Test all of the from_ methods, which are the main ways to create ATree """
    def test_from_names(self):
        names_tree = ATree.from_names(fan)
        assert names_tree.show_to_string() == fan_tree.show_to_string()

    def test_from_parents(self):
        parents_tree = ATree.from_parents(parents)
        assert parents_tree.show_to_string() == fan_tree.show_to_string()

    def test_from_names_delim(self):
        delim_tree = ATree.from_names(delim_pipe, delim='|')
        assert delim_tree.show_to_string() == fan_tree.show_to_string()
