class LError(Exception):
    """ Base class for package errors"""


class LoadError(LError):
    """ Errors during transaction, Account Tree, and Eras data load """

    def __init__(self, message):
        self.message = message
