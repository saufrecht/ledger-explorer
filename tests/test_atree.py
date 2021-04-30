import pandas as pd
import pytest

from ledgex.atree import ATree, tle
from ledgex.params import CONST
from ledgex.ledger import Ledger


@pytest.fixture
def skinny_tree():
    skinny_tree: ATree = ATree()
    skinny_tree.create_node("Lower Trunk", "lt")
    skinny_tree.create_node("Middle Trunk", "mt", parent="lt")
    skinny_tree.create_node("Top Trunk", "tt", parent="mt")
    skinny_tree.create_node("Branch Alpha", "ba", parent="tt")
    skinny_tree.create_node("Branch Beta", "bb", parent="tt")
    skinny_tree.create_node("Branch Gamma", "bg", parent="tt")
    return skinny_tree


@pytest.fixture
def skinny_tree_j():
    return '{"Lower Trunk": {"children": [{"Middle Trunk": {"children": [{"Top Trunk": {"children": ["Branch Alpha", "Branch Beta", "Branch Gamma"]}}]}}]}}'  # NOQA


@pytest.fixture
def fan():
    return pd.Series(
        [
            "Continents:All Africa:Senegal",
            "Continents:All Africa:Seychelles",
            "Continents:All Africa:Sierra Leone",
            "Continents:All South America:Colombia",
            "Continents:All South America:Argentina",
            "Entities:MERCOSUR",
            "Entities:EU",
        ]
    )


@pytest.fixture
def parents():
    return pd.DataFrame(
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
    )


@pytest.fixture
def delim_pipe():
    return pd.Series(
        [
            "Continents|All Africa|Senegal",
            "Continents|All Africa|Seychelles",
            "Continents|All Africa|Sierra Leone",
            "Continents|All South America|Colombia",
            "Continents|All South America|Argentina",
            "Entities|MERCOSUR",
            "Entities|EU",
        ]
    )


@pytest.fixture
def fan_tree():
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
    return fan_tree


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


@pytest.fixture
def rollup_happy():
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
    return rollup_happy


@pytest.fixture
def rollup_empty():
    rollup_empty: ATree = ATree()
    rollup_empty.create_node("root", identifier="root")
    rollup_empty.root = "root"
    rollup_empty.create_node("Ten", identifier="Ten", parent="root")
    rollup_empty.create_node("Twenty", identifier="Twenty", parent="root")
    rollup_empty.create_node("Branch", identifier="Branch", parent="root")
    rollup_empty.create_node("Thirty", identifier="Thirty", parent="Branch")
    rollup_empty.create_node("Forty", identifier="Forty", parent="Branch")
    return rollup_empty


@pytest.fixture
def trans_happy():
    trans = Ledger(columns=[CONST["account_col"], CONST["amount_col"]])
    trans = trans.append({"account": "root", "amount": ""}, ignore_index=True)
    trans = trans.append({"account": "Ten", "amount": 5}, ignore_index=True)
    trans = trans.append({"account": "Ten", "amount": 5}, ignore_index=True)
    trans = trans.append({"account": "Twenty", "amount": 10}, ignore_index=True)
    trans = trans.append({"account": "Twenty", "amount": 5}, ignore_index=True)
    trans = trans.append({"account": "Twenty", "amount": 5}, ignore_index=True)
    trans = trans.append({"account": "Thirty", "amount": 15}, ignore_index=True)
    trans = trans.append({"account": "Thirty", "amount": 15}, ignore_index=True)
    trans = trans.append({"account": "Forty", "amount": 20}, ignore_index=True)
    trans = trans.append({"account": "Forty", "amount": 20}, ignore_index=True)
    return trans


@pytest.fixture
def trans_sad():
    trans = Ledger(columns=[CONST["account_col"], CONST["amount_col"]])
    trans = trans.append({"account": "root", "amount": None}, ignore_index=True)
    trans = trans.append({"account": "Ten", "amount": 1}, ignore_index=True)
    trans = trans.append({"account": "Ten", "amount": 5}, ignore_index=True)
    trans = trans.append({"account": "Twenty", "amount": 22}, ignore_index=True)
    trans = trans.append({"account": "Twenty", "amount": 3}, ignore_index=True)
    trans = trans.append({"account": "Twenty", "amount": 1}, ignore_index=True)
    trans = trans.append({"account": "Thirty", "amount": 11}, ignore_index=True)
    trans = trans.append({"account": "Thirty", "amount": 11}, ignore_index=True)
    trans = trans.append({"account": "Forty", "amount": 1}, ignore_index=True)
    trans = trans.append({"account": "Forty", "amount": 1}, ignore_index=True)
    return trans


@pytest.fixture
def rollup_leafy():
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
    return rollup_leafy


class TestSkinnyTrim:
    """ Should remove lower and middle trunk """

    def test_lt(self, skinny_tree):
        assert skinny_tree.get_node("lt").tag == "Lower Trunk"

    def test_mt(self, skinny_tree):
        assert skinny_tree.get_node("mt").tag == "Middle Trunk"

    def test_lt_gone(self, skinny_tree):
        assert skinny_tree.trim_excess_root().get_node("lt") is None

    def test_mt_gone(self, skinny_tree):
        assert skinny_tree.trim_excess_root().get_node("mt") is None

    def test_tt(self, skinny_tree):
        title = skinny_tree.trim_excess_root().get_node("tt").tag
        assert title == "Top Trunk"

    def test_root(self, skinny_tree):
        id = skinny_tree.trim_excess_root().root
        assert id == "tt"


class TestSkinnyString:
    """ render a string """

    def test_show(self, skinny_tree):
        assert (
            skinny_tree.show_to_string()
            == "Lower Trunk\n└── Middle Trunk\n    └── Top Trunk\n        ├── Branch Alpha\n        ├── Branch Beta\n        └── Branch Gamma\n"  # NOQA
        )


class TestJson:
    """ Test converting the skinny string to and from JSON """

    def test_null_to_json(self):
        empty_tree = ATree()
        assert empty_tree.to_json() == ""

    def test_skinny_to_json(self, skinny_tree, skinny_tree_j):
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

    def test_tree_to_json_to_tree(self, skinny_tree):
        test_j = skinny_tree.to_json()
        new_tree = ATree.from_json(test_j)
        # ATree's implementation of to_json and from_json is not
        # a clean round trip, so don't test it with this:
        #
        #   assert skinny_tree.to_dict() == new_tree.to_dict()
        #
        # Instead, test the implementation as-is, which returns
        # trimmed treed.
        assert new_tree.to_dict() == skinny_tree.trim_excess_root().to_dict()


class TestFroms:
    """ Test all of the from_ methods, which are the main ways to create ATree """

    def test_from_names(self, fan, fan_tree):
        assert ATree.from_names(fan).to_dict() == fan_tree.to_dict()

    def test_from_parents(self, parents, fan_tree):
        assert ATree.from_parents(parents).to_dict() == fan_tree.to_dict()

    def test_from_names_delim(self, delim_pipe, fan_tree):
        delim_tree = ATree.from_names(delim_pipe, delim="|")
        assert delim_tree.to_dict() == fan_tree.to_dict()


class TestGets:
    """ Test the get_* functions which return lists of parents, children, lineage, etc """

    def test_get_ch_tags(self, skinny_tree):
        assert skinny_tree.get_children_tags("nonexistent root") == []
        assert skinny_tree.get_children_tags("lt") == ["Middle Trunk"]
        assert skinny_tree.get_children_tags("tt") == [
            "Branch Alpha",
            "Branch Beta",
            "Branch Gamma",
        ]
        assert skinny_tree.get_children_tags("bb") == []

    def test_get_ch_ids(self, skinny_tree):
        assert skinny_tree.get_children_ids("nonexistent root") == []
        assert skinny_tree.get_children_ids("lt") == ["mt"]
        assert skinny_tree.get_children_ids("tt") == ["ba", "bb", "bg"]
        assert skinny_tree.get_children_ids("bb") == []

    def test_get_desc_ids(self, skinny_tree):
        assert skinny_tree.get_descendent_ids("") == ["mt", "tt", "ba", "bb", "bg"]
        assert skinny_tree.get_descendent_ids("nonexistent root") == []
        assert skinny_tree.get_descendent_ids("lt") == ["mt", "tt", "ba", "bb", "bg"]
        assert skinny_tree.get_descendent_ids("tt") == ["ba", "bb", "bg"]
        assert skinny_tree.get_descendent_ids("bb") == []

    def test_get_lin_ids(self, skinny_tree):
        assert skinny_tree.get_lineage_ids("nonexistent root") == []
        assert skinny_tree.get_lineage_ids("lt") == []
        assert skinny_tree.get_lineage_ids("tt") == ["lt", "mt"]
        assert skinny_tree.get_lineage_ids("bb") == ["lt", "mt", "tt"]

    def test_get_dict_of_paths(self, skinny_tree):
        assert skinny_tree.get_dict_of_paths() == {
            "lt": "lt",
            "mt": "lt:mt",
            "tt": "lt:mt:tt",
            "ba": "lt:mt:tt:ba",
            "bb": "lt:mt:tt:bb",
            "bg": "lt:mt:tt:bg",
        }


class TestAppendSums:
    def test_happy(self, rollup_empty, trans_happy, rollup_happy):
        tree = rollup_empty.append_sums_from_trans(trans_happy)
        for test_point in ["Twenty", "Thirty", "Forty"]:
            assert (
                tree[test_point].data["leaf_total"] == rollup_happy[test_point].data["leaf_total"]
            )
        for test_point in ["root", "Branch"]:
            # TODO: this highlights how much better it would be to
            # move leaf_total and any other totals into ATree so there
            # wouldn't be hassle with getting variables out of a data
            # node that might or might not exist
            data = tree[test_point].data
            if data:
                assert data['leaf_total'] == 0
            else:
                pass

    def test_sad(self, rollup_empty, trans_sad, rollup_happy):
        tree = rollup_empty.append_sums_from_trans(trans_sad)
        for test_point in ["Twenty", "Thirty", "Forty"]:
            assert (
                tree[test_point].data["leaf_total"] != rollup_happy[test_point].data["leaf_total"]
            )


class TestRollUpSubtotals:
    def test_happy(self, rollup_happy):
        happy = rollup_happy.roll_up_subtotals()
        assert happy["Twenty"].data["total"] == 20
        assert happy["Branch"].data["total"] == 70
        assert happy["root"].data["total"] == 100

    def test_with_leafy(self, rollup_leafy):
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
