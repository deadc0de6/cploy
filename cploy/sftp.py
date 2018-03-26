"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Represents an sftp connection
"""

import os
import paramiko
import binascii
import stat

# local imports
from cploy.log import Log
from cploy.task import Task
from cploy.exceptions import *


class Sftp:

    KNOWNHOSTS = '~/.ssh/known_hosts'

    def __init__(self, task, id, debug=False):
        self.task = task
        self.id = id
        self.debug = debug
        self.trans = None
        self.sftp = None
        self.initerr = ''

    def close(self):
        ''' close sftp connection '''
        if self.trans:
            self.trans.close()

    def connect(self):
        ''' connect on remote through sftp '''
        if self.trans and trans.is_authenticated():
            return
        if not self._verif_hostkey(self.task.hostname):
            err = 'hostkey verification failed'
            self._err(err)
            raise ConnectionException(err)
        trans = self._connect()
        if not trans.is_authenticated():
            err = 'cannot authenticate'
            self._err(err)
            raise ConnectionException(err)
        self._debug('is authenticated')
        self.trans = trans
        self.sftp = paramiko.SFTPClient.from_transport(self.trans)
        if not os.path.exists(self.task.local):
            self.close()
            err = 'local path does not exist'
            self._err(err)
            raise SyncException(err)
        if self.exists(self.task.remote) and not self.task.force:
            self.close()
            err = 'remote path exists (use --force)'
            self._err(err)
            raise SyncException(err)
        if not self.exists(self.task.remote):
            self.mkdirp(self.task.remote)

    def _con_key(self):
        ''' connect using provided key '''
        t = paramiko.Transport((self.task.hostname, self.task.port))
        self._debug('connecting using provided key for sftp ...')
        k = paramiko.RSAKey.from_private_key_file(self.task.key,
                                                  password=self.task.keypass)
        t.connect(username=self.task.username, pkey=k)
        return t

    def _con_pass(self):
        ''' connect using provided password '''
        t = paramiko.Transport((self.task.hostname, self.task.port))
        self._debug('connecting using provided password ...')
        t.connect(username=self.task.username, password=self.task.password)
        return t

    def _con_agent(self):
        ''' connect using agent '''
        t = paramiko.Transport((self.task.hostname, self.task.port))
        err = 'ok'
        self._debug('connecting using agent ...')
        agent = paramiko.agent.Agent()
        keys = agent.get_keys()
        # try all keys
        for key in keys:
            t = paramiko.Transport((self.task.hostname, self.task.port))
            fp = binascii.hexlify(key.get_fingerprint()).decode("utf-8")
            self._debug('trying to connect with key {}'.format(fp))
            try:
                t.connect(username=self.task.username, pkey=key)
            except paramiko.ssh_exception.SSHException as e:
                continue
            if t.is_authenticated():
                self._debug('connection successful with key {}'.format(fp))
                break
            t.close()
        return t

    def _knownhosts(self):
        ''' load known host from file '''
        p = os.path.expanduser(self.KNOWNHOSTS)
        if not os.path.exists(p):
            return None
        return paramiko.hostkeys.HostKeys(p)

    def _verif_hostkey(self, host):
        ''' verify host against hostkey file '''
        kh = self._knownhosts()
        if not kh:
            return False
        return kh.lookup(host) is not None

    def _connect(self):
        ''' connect to remote through sftp '''
        if self.task.key:
            t = self._con_key()
        elif self.task.password:
            t = self._con_pass()
        else:
            t = self._con_agent()
        return t

    ###########################################################
    # file operations
    ###########################################################
    def _init_files(self, files, ldir, rdir):
        ''' copy multiple files to remote '''
        for f in files:
            lpath = os.path.join(ldir, f)
            rpath = os.path.join(rdir, f)
            self._debug('[sync] init file: {}'.format(rpath))
            if not self.copy(lpath, rpath):
                return False
        return True

    def _init_dirs(self, dirs, ldir, rdir):
        ''' create multiple directories to remote '''
        for d in dirs:
            lpath = os.path.join(ldir, d)
            rpath = os.path.join(rdir, d)
            self._debug('[sync] init dir: {}'.format(rpath))
            if self.exists(rpath):
                continue
            if not self.mkdir(rpath):
                return False
        return True

    def initsync(self, ldir, rdir):
        ''' sync local directory on remote '''
        self._debug('[sync] sync dir {} with {}'.format(ldir, rdir))
        for cur, subd, files in os.walk(ldir):
            com = os.path.commonpath([ldir, cur])
            rcur = os.path.join(rdir, cur[len(com)+1:])
            if not self._init_files(files, cur, rcur):
                return False
            if not self._init_dirs(subd, cur, rcur):
                return False
            for sub in subd:
                rpath = os.path.join(rcur, sub)
                self._debug('[sync] init sub: {}'.format(rpath))
                if not self.mkdir(rpath):
                    return False
        return True

    def copy(self, lpath, rpath):
        ''' copy file to the remote '''
        if not os.path.exists(lpath):
            self._debug('[sync] copy - lfile disappeared: {}'.format(lpath))
            return False
        d = os.path.dirname(rpath)
        if not self.exists(d):
            self._debug('[sync] create remote dir: {}'.format(d))
            if not self.mkdir(d):
                return False
        self._debug('[sync] copy {} to {}'.format(lpath, rpath))
        try:
            self.sftp.put(lpath, rpath)
            self.chattr(lpath, rpath)
        except FileNotFoundError:
            Log.err('cannot create file {}'.format(rpath))
            return False
        except PermissionError as e:
            Log.err('cannot create file {}: {}'.format(rpath, e))
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def mkdirp(self, path):
        ''' mkdir -p recursive equivalent '''
        (head, tail) = os.path.split(path)
        if head and not self.exists(head):
            self.mkdirp(head)
        if tail:
            self.mkdir(tail)

    def mkdir(self, path):
        ''' mkdir on remote '''
        if self.exists(path):
            return True
        self._debug('[sync] mkdir {}'.format(path))
        try:
            self.sftp.mkdir(path)
        except FileNotFoundError:
            Log.err('cannot create dir \"{}\"'.format(path))
            return False
        except PermissionError as e:
            Log.err('cannot create file {}: {}'.format(rpath, e))
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def rm(self, path):
        ''' remote file on remote '''
        if not self.exists(path):
            return True
        try:
            if self.is_dir(path):
                self._debug('[sync] rm -r {}'.format(path))
                self.sftp.rmdir(path)
            elif self.is_file(path):
                self._debug('[sync] rm {}'.format(path))
                self.sftp.remove(path)
        except PermissionError as e:
            Log.err('cannot remove file {}: {}'.format(rpath, e))
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def chattr(self, lpath, rpath):
        ''' change file attribute '''
        if not os.path.exists(lpath):
            self._debug('[sync] chattr - {} does not exist'.format(lpath))
            return False
        if not self.exists(rpath):
            self._debug('[sync] chattr - {} does not exist'.format(rpath))
            return False
        self._debug('[sync] chattr {}'.format(rpath))
        try:
            self.sftp.chmod(rpath, self._get_mode(lpath))
        except PermissionError as e:
            Log.err('cannot create file {}: {}'.format(rpath, e))
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def mv(self, rsrc, rdst):
        if not self.exists(rsrc):
            self._debug('[sync] mv - src file disappeared: {}'.format(rsrc))
            return True
        self._debug('[sync] mv {} {}'.format(rsrc, rdst))
        try:
            self.sftp.rename(rsrc, rdst)
        except PermissionError as e:
            Log.err('cannot create file {}: {}'.format(rpath, e))
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def is_dir(self, path):
        ''' test if remote path is a directory '''
        if not self.exists(path):
            return False
        mode = self.sftp.stat(path).st_mode
        return stat.S_ISDIR(mode)

    def is_file(self, path):
        ''' test if remote path is a regular file '''
        if not self.exists(path):
            return False
        mode = self.sftp.stat(path).st_mode
        return stat.S_ISREG(mode)

    def exists(self, path):
        ''' test if path exists on remote '''
        try:
            self.sftp.stat(path)
        except IOError:
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def execute(self, cmd):
        ''' execute command on remote through sftp '''
        self._debug('[sync] run on remote: \"{}\"'.format(cmd))
        channel = self.trans.open_session()
        channel.exec_command(cmd)
        return True

    ###########################################################
    # file operations helpers
    ###########################################################
    def _get_mode(self, lpath):
        '''' return attrib of local file '''
        return os.stat(lpath).st_mode

    ###########################################################
    # utils
    ###########################################################
    def _log(self, msg):
        msg = '[{}] {}'.format(self.id, msg)
        Log.log(msg)

    def _err(self, msg):
        msg = '[{}] {}'.format(self.id, msg)
        Log.err(msg)

    def _debug(self, msg):
        if not self.debug:
            return
        msg = '[{}] {}'.format(self.id, msg)
        Log.debug(msg)
