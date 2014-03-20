__author__ = 'Mattia'


class _HttpException(Exception):
    def __init__(self, stream):
        Exception.__init__(self)
        self.stream = stream
        self.data = self.stream.read()

    def __str__(self):
        return self.data


class LoginException(_HttpException):
    pass


class DownloadException(_HttpException):
    pass