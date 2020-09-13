from treelib import Tree

from ledger_explorer import utils


skinny_tree: Tree = Tree()
skinny_tree.create_node('Lower Trunk', 'lt')
skinny_tree.create_node('Middle Trunk', 'mt', parent='lt')
skinny_tree.create_node('Top Trunk', 'tt', parent='mt')
skinny_tree.create_node('Branch Alpha', 'ba', parent='tt')
skinny_tree.create_node('Branch Beta', 'bb', parent='tt')
skinny_tree.create_node('Branch Gamma', 'bg', parent='tt')


# class TestTrim:
#     # Should remove lower and middle trunk

#     def test_lt(self):
#         assert (skinny_tree.get_node('lt').tag == 'Lower Trunk')

#     def test_mt(self):
#         assert (skinny_tree.get_node('mt').tag == 'Middle Trunk')

#     short_tree: Tree = utils.trim_excess_root(skinny_tree)

#     def test_lt_gone(self):
#         assert (self.short_tree.get_node('lt') is None)

#     def test_mt_gone(self):
#         assert (self.short_tree.get_node('mt') is None)

#     def test_tt(self):
#         title = self.short_tree.get_node('tt').tag
#         assert (title == 'Top Trunk')

#     def test_root(self):
#         id = self.short_tree.root
#         assert (id == 'tt')
