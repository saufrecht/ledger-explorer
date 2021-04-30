import pandas as pd

from errors import LError
from params import CONST


class Ledger(pd.DataFrame):
    """
    TODO: Move this into Datastore?  Or have Ledger be a subclass of DataFrame?
    """

    @staticmethod
    def positize(trans):
        """Negative values can't be plotted in sunbursts.  This can't be fixed
        with absolute value because that would erase the distinction
        between debits and credits within an account.  Simply
        reversing sign could result in a net-negative sum, which also
        breaks sunbursts.  This function always returns a DataFrame of
        transactions which sums to a positive number, thus suitable
        for a sunburst.
        """
        if trans.sum(numeric_only=True)["amount"] < 0:
            trans["amount"] = trans["amount"] * -1
        return trans

    @staticmethod
    def prorate_factor(time_span: str, ts_resolution: str = None, duration: float = 0):
        """
        Given a time_span keyword and either resolution keyword or duration number,
        return the factor by which to multiple amounts to produce appropriately prorated
        values.
        """
        if time_span == 'total' or (ts_resolution == 'era' and duration == 0):
            return 1
        else:
            try:
                factor_num: float = CONST["time_span_lookup"][time_span]['months']
            except KeyError as E:
                raise LError(f'Invalid keyword for time series: {E}')
        factor_denom: float = None
        if ts_resolution and len(ts_resolution) > 0:
            try:
                factor_denom: float = CONST["time_res_lookup"][ts_resolution]['months']
            except KeyError as E:
                raise LError(f'Invalid keyword for time resolution: {E}')
        else:
            factor_denom = duration
        return factor_num / factor_denom
