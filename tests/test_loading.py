import pandas as pd
import pytest

import ledgex.loading as loading
import ledgex.params as params

def_params = params.Params()
def_params.fill_defaults()
min_trans_url = 'https://ledge.uprightconsulting.com/s/minimal_transaction_data.csv'
min_trans_filename = 'minimal_transaction_data.csv'
min_trans_input_file = 'data:text/csv;base64,RGF0ZSxUcmFuc2FjdGlvbiBJRCxOdW1iZXIsRGVzY3JpcHRpb24sTm90ZXMsQ29tbW9kaXR5L0N1cnJlbmN5LFZvaWQgUmVhc29uLEFjdGlvbixNZW1vLEZ1bGwgQWNjb3VudCBOYW1lLEFjY291bnQgTmFtZSxBbW91bnQgV2l0aCBTeW0sQW1vdW50IE51bS4sUmVjb25jaWxlLFJlY29uY2lsZSBEYXRlLFJhdGUvUHJpY2UNCjAxLzAxLzIwMTcsMDFmYWNhNWE3NWVkNGZlZDlmMzZmNmRlYTA0YjlmOWMsLEZvdW5kIG1vbmV5IG9uIHRoZSBzdHJlZXQsLENVUlJFTkNZOjpVU0QsLCwsQXNzZXRzOkN1cnJlbnQgQXNzZXRzOkNhc2ggaW4gV2FsbGV0LENhc2ggaW4gV2FsbGV0LCIkMSwwMDAuMDAiLCIxLDAwMC4wMCIsbiwsMS4wMA0KLCwsLCwsLCwsSW5jb21lOk90aGVyIEluY29tZSxPdGhlciBJbmNvbWUsIi0kMSwwMDAuMDAiLCItMSwwMDAuMDAiLG4sLDEuMDANCjA5LzI5LzIwMTgsZGJiYmQ3Njc3MjdjNGJiNWFhOTdmNzMxYzVjODkwMWMsLFNlY3VyaXR5IEd1YXJkIEpvYiwsQ1VSUkVOQ1k6OlVTRCwsLCxBc3NldHM6Q3VycmVudCBBc3NldHM6Q2hlY2tpbmcgQWNjb3VudCxDaGVja2luZyBBY2NvdW50LCIkMSw4NzUuMDAiLCIxLDg3NS4wMCIsbiwsMS4wMA0KLCwsLCwsLDEvMS8xOSxEaXJlY3QgZGVwb3NpdCBmcm9tIHNlY3VyaXR5IGd1YXJkIGpvYixJbmNvbWU6U2FsYXJ5LFNhbGFyeSwiLSQxLDg3NS4wMCIsIi0xLDg3NS4wMCIsbiwsMS4wMA0KMDEvMDMvMjAxOSw5OGM4MWYyYjNkMjE0NTE0Yjg3MTdlYTE5ZmZjNzJjZSwsY29jYWluZSBoYWJpdCwsQ1VSUkVOQ1k6OlVTRCwsLCxBc3NldHM6Q3VycmVudCBBc3NldHM6Q2hlY2tpbmcgQWNjb3VudCxDaGVja2luZyBBY2NvdW50LC0kMTAwLjAwLC0xMDAuMDAsbiwsMS4wMA0KLCwsLCwsLCwsRXhwZW5zZXM6SG9iYmllcyxIb2JiaWVzLCQxMDAuMDAsMTAwLjAwLG4sLDEuMDANCjA0LzE1LzIwMjAsZjQzNWNlNzM3ODg5NGQyMGJkZjBjZGY1ZTNlMTRlNDMsLG5vdGhpbmcgc3VzcGljaW91cyBhYm91dCB0aGlzIHRheCBwYXltZW50LCxDVVJSRU5DWTo6VVNELCwsLEV4cGVuc2VzOlRheGVzOkZlZGVyYWwsRmVkZXJhbCwiJDIsMDAwLjAwIiwiMiwwMDAuMDAiLG4sLDEuMDANCiwsLCwsLCwsLEluY29tZTpTYWxhcnksU2FsYXJ5LCItJDIsMDAwLjAwIiwiLTIsMDAwLjAwIixuLCwxLjAwDQo='  # NOQA
min_eras_input_file = 'data:text/csv;base64,bmFtZSxkYXRlX3N0YXJ0LGRhdGVfZW5kCiJmaXJzdCBqb2IiLCwyMDE3LTEyLTMxCiJOaW5lLW1vbnRoIFN0aXBlbmQiLDIwMTgtMDEtMDEsMjAxOC0wOC0zMQoic2VjdXJpdHkgZ3VhcmQiLDIwMTgtMDktMDEgCg=='  # NOQA
min_eras_frame = pd.DataFrame({'name': ['first job', 'Nine-month Stipend', 'security guard'], 'date_start': ['', '2018-01-01', '2018-09-01'], 'date_end': ['2017-12-31', '2018-08-31', '']})  # NOQA


class TestParse64:
    """ n.b. also tested indirectly in TestLoadInput """

    def test_min(self):
        data = loading.parse_base64_file(min_trans_input_file, min_trans_filename)
        assert len(data) == 8
        assert data.iloc[4].Description == 'cocaine habit'
        assert data['Amount Num.'].sum() == 0


class TestLoadInput:
    """ test load_input_file """

    def test_input_file(self):
        new_filename, data, result_meta = loading.load_input_file(min_trans_input_file, None, min_trans_filename)
        assert len(data) == 8
        assert data.iloc[4].Description == 'cocaine habit'
        assert new_filename == min_trans_filename
        assert data['Amount Num.'].sum() == 0
        assert '8 records' in result_meta

    def test_url_file(self):
        new_filename, data, result_meta = loading.load_input_file(None, min_trans_url, None)
        assert len(data) == 8
        assert data.iloc[6].Description == 'nothing suspicious about this tax payment'
        assert data['Amount Num.'].sum() == 0
        assert '8 records' in result_meta


class TestRenameCol:
    """ test rename columns """

    def test_min(self):
        new_filename, data, result_meta = loading.load_input_file(min_trans_input_file, None, min_trans_filename)
        old_col = 'Amount Num.'
        new_col = params.CONST['amount_col']
        assert old_col in data.columns
        renamed = loading.rename_columns(data, def_params)
        assert new_col in renamed.columns
        assert old_col not in renamed.columns


class TestLoadTrans:
    """ test load trans """
    def test_min_trans(self):
        new_filename, data, result_meta = loading.load_input_file(min_trans_input_file, None, min_trans_filename)
        renamed = loading.rename_columns(data, def_params)
        trans = loading.load_transactions(renamed)
        assert len(trans) == 8
        assert trans['date'].min() == pd.Timestamp('2017-01-01 00:00:00')
        assert trans.iloc[0]['full account name'] == 'Assets:Current Assets:Cash in Wallet'


class TestLoadEras:
    """ test load_eras"""

    @pytest.mark.xfail(reason='bug in load_eras')
    def test_simple(self):
        early_date = pd.Timestamp('2010-01-01')
        late_date = pd.Timestamp('2020-12-31')
        eras = loading.load_eras(min_eras_frame, early_date, late_date)
        assert eras.loc['first job'].date_start == early_date
        assert eras.loc['Nine-month Stipend'].date_end == pd.Timestamp('2018-08-31 00:00:00')
        assert eras.loc['security guard'].date_start == pd.Timestamp('2018-09-01 00:00:00')
        assert eras.loc['security guard'].date_end == late_date


class TestConvertRaw:
    """ test convert_raw """

    def test_min(self):
        new_filename, raw_trans, result_meta = loading.load_input_file(min_trans_input_file, None, min_trans_filename)
        trans, atree, eras = loading.convert_raw_data(raw_trans, pd.DataFrame(), pd.DataFrame(), parameters=def_params)
        assert len(trans) == 8
        assert trans[trans['account'] == 'Salary'].amount.sum() == 3875
        assert trans['date'].min() == pd.Timestamp('2017-01-01 00:00:00')
