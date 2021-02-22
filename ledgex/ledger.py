import pandas as pd


class Ledger(pd.DataFrame):
    """
    TODO: Work in progress to start using this instead of "trans" everywhere.
    """

    @staticmethod
    def positize(trans):
        """Negative values can't be plotted in sunbursts.  This can't be fixed
        with absolute value because that would erase the distinction
        between debits and credits within an account.  Simply
        reversing sign could result in a net-negative sum, which also
        breaks sunbursts.  This function always returns a net-positive
        sum DataFrame of transactions, suitable for a sunburst.
        """
        if trans.sum(numeric_only=True)["amount"] < 0:
            trans["amount"] = trans["amount"] * -1
        return trans
