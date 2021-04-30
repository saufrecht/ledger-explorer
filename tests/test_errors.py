import pytest

from ledgex import errors


class TestLoadError:
    """ should be a normal Exception, subclassed to differentiate from other Exceptions. """

    def test_load_error(self):
        with pytest.raises(errors.LoadError):
            raise errors.LoadError('foobar')

    def test_load_error_message(self):
        try:
            raise errors.LoadError('foobar')
        except errors.LoadError as E:
            assert E.message == 'foobar'
