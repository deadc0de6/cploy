"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Represent a task to sync
"""

import os

# local import
from cploy.exceptions import *


class Task:

    USER_SEP = '@'
    PORT_SEP = ':'

    def __init__(self, args):
        self.args = args
        self._parse()

    def _parse(self):
        ''' parse arguments to construct task '''
        self.force = self.args['--force']
        self.local = self.args['<local_path>']
        self.remote = self.args['<remote_path>']
        if not os.path.exists(self.local):
            err = 'local path \"{}\" does not exist'.format(self.local)
            raise SyncException(err)
        self.username = self.args['--user']
        self.hostname = self.args['<hostname>']
        self.port = int(self.args['--port'])
        if self.USER_SEP in self.hostname:
            self.username = self.hostname.split(self.USER_SEP)[0]
            self.hostname = self.hostname.split(self.USER_SEP)[1]
            if self.PORT_SEP in self.hostname:
                self.port = int(self.hostname.split(self.PORT_SEP)[1])
                self.hostname = self.hostname.split(self.PORT_SEP)[0]
        self.key = self.args['--key']
        if self.key:
            self.key = self.args['--key']
        self.keypass = self.args['--keypass']
        self.password = self.args['--pass']
        self.exclude = self.args['--exclude']
        self.command = self.args['--command']

    def get_cli(self):
        ''' returns the command used to create the task '''
        return self.args['cli']

    def hash(self):
        ''' create hash of this sync '''
        check = hash(self.local)
        check ^= hash(self.remote)
        check ^= hash(self.username)
        check ^= hash(self.hostname)
        return check
