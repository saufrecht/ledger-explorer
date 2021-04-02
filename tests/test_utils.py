from numpy import datetime64
from ledgex.utils import to_decade, period_to_date_range, pretty_date


class TestToDecade:
    """ Convert MCDY to "an int representing the first year of the containing decade" """

    def test_happy1(self):
        assert to_decade("2001") == 2000

    def test_happy0(self):
        assert to_decade("2000") == 2000

    def test_happy9(self):
        assert to_decade("2009") == 2000

    def test_2010(self):
        assert to_decade("2010") == 2010


class TestPeriodToDateRange:
    """ changes various complex inputs into dateranges (tuple of start and end datetimes) """

    def test_decade_happy(self):
        assert period_to_date_range("decade", "2001") == (
            datetime64("2000-01-01T00:00:00.000000"),
            datetime64("2009-12-31T00:00:00.000000"),
        )
