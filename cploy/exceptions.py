"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
"""


class ConnectionException(Exception):
    ''' Connection exception in SFTP '''
    def __init__(self, msg):
        super(ConnectionException, self).__init__(msg)
        self.msg = 'ConnectionException: {}'.format(msg)


class SyncException(Exception):
    ''' Sync exception in SFTP '''
    def __init__(self, msg):
        super(SyncException, self).__init__(msg)
        self.msg = 'SyncException: {}'.format(msg)


class ComException(Exception):
    ''' Socket communication exception '''
    def __init__(self, msg):
        super(ComException, self).__init__(msg)
        self.msg = 'ComException: {}'.format(msg)
