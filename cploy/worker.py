"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Provides the operations from local to remote
"""

import os

# local imports
from cploy.log import Log
from cploy.sftp import Sftp
from cploy.fsmon import Fsmon
from cploy.message import Message as Msg


class Worker:

    def __init__(self, task, sftp,
                 inqueue, outqueue,
                 debug=False, force=False):
        self.task = task
        self.id = sftp.id
        self.sftp = sftp
        self.inqueue = inqueue
        self.outqueue = outqueue
        self.debug = debug
        self.force = force

    def _log(self, msg):
        ''' log with thread info '''
        Log.log('worker-th{} {}'.format(self.id, msg))

    def start(self, stopreq):
        ''' start syncing through filesystem monitoring '''
        self.mon = Fsmon(self, exclude=self.task.exclude, debug=self.debug)
        if not self.mon.start():
            err = 'th{} monitoring filesystem failed'.format(self.id)
            self.err(err)
            self.mon.stop()
            self.sftp.close()
            return False
        while not stopreq.is_set():
            # process anything in the inqueue
            cmd = self.inqueue.get()
            if not self._process_cmd(cmd):
                break
        self.mon.stop()
        self.sftp.close()
        return True

    def _process_cmd(self, cmd):
        ''' process command received '''
        if cmd == Msg.stop:
            if self.debug:
                Log.debug('th{} worker stopping'.format(self.id))
            return False
        if cmd == Msg.debug:
            if self.debug:
                Log.debug('th{} worker toggle debug'.format(self.id))
            self.debug = not self.debug
            return True
        if cmd == Msg.resync:
            if self.debug:
                Log.debug('th{} worker resync'.format(self.id))
            self.sftp.initsync(self.task.local, self.task.remote)
        elif cmd == Msg.info:
            if self.debug:
                Log.debug('th{} worker info'.format(self.id))
            msg = '{} sync \"{}\" to \"{}\" on {}'.format(self.id,
                                                          self.task.local,
                                                          self.task.remote,
                                                          self.task.hostname)
            self.outqueue.put(msg)
        return True

    def get_local(self):
        ''' return the local path '''
        return self.task.local

    def _norm(self, path):
        ''' normalize the path '''
        path = os.path.normpath(path)
        return os.path.expanduser(path)

    def _get_remotepath(self, abspath):
        ''' get final path on remote based on local path '''
        common = os.path.commonpath([self.task.local, abspath])
        remote = abspath[len(common):].lstrip(os.sep)
        remabs = os.path.join(self.task.remote, remote)
        return remabs

    def _on_change(self):
        ''' execute command on change if any '''
        if self.task.command:
            self.sftp.execute(self.task.command)

    ###########################################################
    # callbacks for changes
    ###########################################################
    def mirror(self, path):
        ''' copy a file to the remote '''
        local = self._norm(path)
        remote = self._get_remotepath(local)
        self._log('copy {} to {}'.format(local, remote))
        self.sftp.copy(local, remote)
        self._on_change()

    def create(self, path):
        ''' create a file on remote '''
        if not os.path.isdir(path):
            return
        remote = self._get_remotepath(path)
        self._log('create {}'.format(remote))
        self.sftp.mkdir(remote)
        self._on_change()

    def attrib(self, path):
        ''' copy rights on remote file '''
        remote = self._get_remotepath(path)
        self._log('change attr of {}'.format(remote))
        self.sftp.chattr(path, remote)
        self._on_change()

    def delete(self, path):
        ''' delete a file on the remote '''
        remote = self._get_remotepath(path)
        self._log('delete {}'.format(remote))
        self.sftp.rm(remote)
        self._on_change()

    def move(self, src, dst):
        ''' move a file from src to dst '''
        rsrc = self._get_remotepath(src)
        rdst = self._get_remotepath(dst)
        self._log('mv {} {}'.format(rsrc, rdst))
        self.sftp.mv(rsrc, rdst)
        self._on_change()
