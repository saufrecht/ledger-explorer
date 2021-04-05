import pandas as pd
import pytest

from ledgex.atree import ATree, tle
from ledgex.params import CONST

skinny_tree: ATree = ATree()
skinny_tree.create_node("Lower Trunk", "lt")
skinny_tree.create_node("Middle Trunk", "mt", parent="lt")
skinny_tree.create_node("Top Trunk", "tt", parent="mt")
skinny_tree.create_node("Branch Alpha", "ba", parent="tt")
skinny_tree.create_node("Branch Beta", "bb", parent="tt")
skinny_tree.create_node("Branch Gamma", "bg", parent="tt")

skinny_tree_j = '{"Lower Trunk": {"children": [{"Middle Trunk": {"children": [{"Top Trunk": {"children": ["Branch Alpha", "Branch Beta", "Branch Gamma"]}}]}}]}}'  # NOQA

fan = pd.Series(
    [
        "Continents:All Africa:Senegal",
        "Continents:All Africa:Seychelles",
        "Continents:All Africa:Sierra Leone",
        "Continents:All South America:Colombia",
        "Continents:All South America:Argentina",
        "Entities:MERCOSUR",
        "Entities:EU",
    ]
)  # NOQA

parents = pd.DataFrame(
    {
        CONST["account_col"]: [
            "Continents",
            "All Africa",
            "Senegal",
            "Seychelles",
            "Sierra Leone",
            "All South America",
            "Colombia",
            "Argentina",
            "Entities",
            "MERCOSUR",
            "EU",
        ],
        CONST["parent_col"]: [
            "root",
            "Continents",
            "All Africa",
            "All Africa",
            "All Africa",
            "Continents",
            "All South America",
            "All South America",
            "root",
            "Entities",
            "Entities",
        ],
    }
)  # NOQA

delim_pipe = pd.Series(
    [
        "Continents|All Africa|Senegal",
        "Continents|All Africa|Seychelles",
        "Continents|All Africa|Sierra Leone",
        "Continents|All South America|Colombia",
        "Continents|All South America|Argentina",
        "Entities|MERCOSUR",
        "Entities|EU",
    ]
)  # NOQA

fan_tree = ATree()
fan_tree.create_node(tag=ATree.ROOT_TAG, identifier=ATree.ROOT_ID)
fan_tree.create_node("Continents", "Continents", parent=ATree.ROOT_ID)
fan_tree.create_node("Entities", "Entities", parent=ATree.ROOT_ID)
fan_tree.create_node("All Africa", "All Africa", parent="Continents")
fan_tree.create_node("All South America", "All South America", parent="Continents")
fan_tree.create_node("MERCOSUR", "MERCOSUR", parent="Entities")
fan_tree.create_node("EU", "EU", parent="Entities")
fan_tree.create_node("Senegal", "Senegal", parent="All Africa")
fan_tree.create_node("Seychelles", "Seychelles", parent="All Africa")
fan_tree.create_node("Sierra Leone", "Sierra Leone", parent="All Africa")
fan_tree.create_node("Argentina", "Argentina", parent="All South America")
fan_tree.create_node("Colombia", "Colombia", parent="All South America")


@pytest.fixture
def naughty_tree():
    import treelib

    tree = ATree()
    blns_list = []
    tree.create_node(tag=ATree.ROOT_TAG, identifier=ATree.ROOT_ID)
    with open("tests/blns.txt") as f:
        parent = ATree.ROOT_ID
        for line in f:
            if len(line) > 0 and line != "":
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
        assert skinny_tree.get_node("lt").tag == "Lower Trunk"

    def test_mt(self):
        assert skinny_tree.get_node("mt").tag == "Middle Trunk"

    short_tree: ATree = skinny_tree.trim_excess_root()

    def test_lt_gone(self):
        assert self.short_tree.get_node("lt") is None

    def test_mt_gone(self):
        assert self.short_tree.get_node("mt") is None

    def test_tt(self):
        title = self.short_tree.get_node("tt").tag
        assert title == "Top Trunk"

    def test_root(self):
        id = self.short_tree.root
        assert id == "tt"


class TestSkinnyString:
    """ render a string """

    def test_show(self):
        assert (
            skinny_tree.show_to_string()
            == "Lower Trunk\n└── Middle Trunk\n    └── Top Trunk\n        ├── Branch Alpha\n        ├── Branch Beta\n        └── Branch Gamma\n"
        )  # NOQA


class TestJson:
    """ Test converting the skinny string to and from JSON """

    def test_skinny_to_json(self):
        assert skinny_tree.to_json() == skinny_tree_j

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

    @pytest.mark.xfail(
        reason="Haven't decided yet how to handle adding the [Total] root, so this comparison fails"
    )
    def test_tree_to_json_to_tree(self):
        test_j = skinny_tree.to_json()
        new_tree = ATree.from_json(test_j)
        # only tests that tags and relationships are identical
        assert skinny_tree.to_dict() == new_tree.to_dict()


class TestFroms:
    """ Test all of the from_ methods, which are the main ways to create ATree """

    def test_from_names(self):
        names_tree = ATree.from_names(fan)
        assert names_tree.to_dict() == fan_tree.to_dict()

    def test_from_parents(self):
        parents_tree = ATree.from_parents(parents)
        assert parents_tree.to_dict() == fan_tree.to_dict()

    def test_from_names_delim(self):
        delim_tree = ATree.from_names(delim_pipe, delim="|")
        assert delim_tree.to_dict() == fan_tree.to_dict()


class TestGets:
    """ Test the get_* functions which return lists of parents, children, lineage, etc """

    def test_get_ch_tags(self):
        assert skinny_tree.get_children_tags("lt") == ["Middle Trunk"]
        assert skinny_tree.get_children_tags("tt") == [
            "Branch Alpha",
            "Branch Beta",
            "Branch Gamma",
        ]
        assert skinny_tree.get_children_tags("bb") == []

    def test_get_ch_ids(self):
        assert skinny_tree.get_children_ids("lt") == ["mt"]
        assert skinny_tree.get_children_ids("tt") == ["ba", "bb", "bg"]
        assert skinny_tree.get_children_ids("bb") == []

    def test_get_desc_ids(self):
        assert skinny_tree.get_descendent_ids("lt") == ["mt", "tt", "ba", "bb", "bg"]
        assert skinny_tree.get_descendent_ids("tt") == ["ba", "bb", "bg"]
        assert skinny_tree.get_descendent_ids("bb") == []

    def test_get_lin_ids(self):
        assert skinny_tree.get_lineage_ids("lt") == []
        assert skinny_tree.get_lineage_ids("tt") == ["lt", "mt"]
        assert skinny_tree.get_lineage_ids("bb") == ["lt", "mt", "tt"]


class TestRollUpSubtotals:
    def test_happy(self):
        rollup_happy: ATree = ATree()
        rollup_happy.create_node("root", identifier="root", data={"leaf_total": 0})
        rollup_happy.root = "root"
        rollup_happy.create_node(
            "Ten", identifier="Ten", parent="root", data={"leaf_total": 10}
        )
        rollup_happy.create_node(
            "Twenty", identifier="Twenty", parent="root", data={"leaf_total": 20}
        )
        rollup_happy.create_node("Branch", identifier="Branch", parent="root")
        rollup_happy.create_node(
            "Thirty", identifier="Thirty", parent="Branch", data={"leaf_total": 30}
        )
        rollup_happy.create_node(
            "Forty", identifier="Forty", parent="Branch", data={"leaf_total": 40}
        )
        rollup_happy = rollup_happy.roll_up_subtotals()
        assert rollup_happy["Twenty"].data["total"] == 20
        assert rollup_happy["Branch"].data["total"] == 70
        assert rollup_happy["root"].data["total"] == 100

    def test_with_leafy(self):
        rollup_leafy: ATree = ATree()
        rollup_leafy.create_node("root", identifier="root", data={"leaf_total": 5})
        rollup_leafy.root = "root"
        rollup_leafy.create_node(
            "Ten", identifier="Ten", parent="root", data={"leaf_total": 10}
        )
        rollup_leafy.create_node(
            "Twenty", identifier="Twenty", parent="root", data={"leaf_total": 20}
        )
        rollup_leafy.create_node(
            "Branch", identifier="Branch", parent="root", data={"leaf_total": 15}
        )
        rollup_leafy.create_node(
            "Thirty", identifier="Thirty", parent="Branch", data={"leaf_total": 30}
        )
        rollup_leafy.create_node(
            "Forty", identifier="Forty", parent="Branch", data={"leaf_total": 40}
        )
        rollup_leafy = rollup_leafy.roll_up_subtotals()
        assert rollup_leafy["Twenty"].data["total"] == 20
        assert rollup_leafy["Branch"].data["total"] == 85
        assert rollup_leafy["root"].data["total"] == 120

    def test_with_negs(self):
        rollup_negs: ATree = ATree()
        rollup_negs.create_node("root", identifier="root", data={"leaf_total": 5})
        rollup_negs.root = "root"
        rollup_negs.create_node(
            "Ten", identifier="Ten", parent="root", data={"leaf_total": 10}
        )
        rollup_negs.create_node(
            "Twenty", identifier="Twenty", parent="root", data={"leaf_total": 20}
        )
        rollup_negs.create_node(
            "Branch", identifier="Branch", parent="root", data={"leaf_total": 15}
        )
        rollup_negs.create_node(
            "Thirty", identifier="Thirty", parent="Branch", data={"leaf_total": 30}
        )
        rollup_negs.create_node(
            "Forty", identifier="Forty", parent="Branch", data={"leaf_total": -40}
        )
        rollup_negs = rollup_negs.roll_up_subtotals()
        assert rollup_negs["Twenty"].data["total"] == 20
        assert rollup_negs["Branch"].data["total"] == 5
        with pytest.raises(tle.NodeIDAbsentError):
            assert rollup_negs["Thirty"]
        assert rollup_negs["root"].data["total"] == 40
