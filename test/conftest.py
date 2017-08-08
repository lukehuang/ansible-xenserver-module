""" Mock XenAPI for testing.

"""
import pytest


class _MockVM(object):
    """ Mock a XenAPI VM object.

    """
    @classmethod
    def get_all_records(cls):
        """ Return asset metadata.

        """
        return [
            {"uuid": "abc123"},
            {"uuid": "def456"},
        ]


class _MockApi(object):
    """ Mock a XenAPI API object.

    """
    VM = _MockVM()


class _MockSession(object):
    """ Mock a XenAPI Session object.

    """
    xenapi = _MockApi()

    def __init__(self, *args, **kwargs):
        """"""
        return

    def login_with_password(self, *args, **kwargs):
        return

@pytest.fixture
def session():
    return _MockSession
