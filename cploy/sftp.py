"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Represents an sftp connection
"""

import os
import paramiko
import binascii
import stat
import fnmatch

# local imports
from cploy.log import Log
from cploy.task import Task
from cploy.exceptions import *


class Sftp:

    KNOWNHOSTS = '~/.ssh/known_hosts'
    BUFSZ = 1024

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
        if self.debug:
            Log.debug('th{} initiate connection'.format(self.id))
        if self.trans and self.trans.is_authenticated():
            return
        if not self._verif_hostkey(self.task.hostname):
            err = 'hostkey verification failed'
            Log.err('{} {}'.format(self.id, err))
            raise ConnectionException(err)
        trans = self._connect()
        if not trans.is_authenticated():
            self.close()
            err = 'cannot authenticate'
            Log.err('{} {}'.format(self.id, err))
            raise ConnectionException(err)
        if self.debug:
            Log.debug('th{} is authenticated'.format(self.id))
        self.trans = trans
        self.sftp = paramiko.SFTPClient.from_transport(self.trans)
        if not os.path.exists(self.task.local):
            self.close()
            err = 'local path does not exist'
            Log.err('{} {}'.format(self.id, err))
            raise SyncException(err)

        if self.exists(self.task.remote) and not self.task.force:
            self.close()
            err = 'remote path exists (use --force)'
            Log.err('{} {}'.format(self.id, err))
            raise SyncException(err)

        if not self.exists(self.task.remote):
            if self.debug:
                Log.debug('th{} create remote directory'.format(self.id))
            self.mkdirp(self.task.remote)

        # adapt remote path with sftp
        self.task.remote = self.sftp.normalize(self.task.remote)
        if self.debug:
            Log.debug('th{} rpath adapted to {}'.format(self.id,
                                                        self.task.remote))

        # change to monitored directory
        if self.debug:
            Log.debug('th{} chdir to \"{}\"'.format(self.id, self.task.remote))
        self.sftp.chdir(self.task.remote)
        if self.debug:
            Log.debug('th{} cwd: {}'.format(self.id, self.sftp.normalize('.')))

    def _con_key(self):
        ''' connect using provided key '''
        t = paramiko.Transport((self.task.hostname, self.task.port))
        if self.debug:
            Log.log('th{} connecting using key'.format(self.id))
        k = paramiko.RSAKey.from_private_key_file(self.task.key,
                                                  password=self.task.keypass)
        t.connect(username=self.task.username, pkey=k)
        return t

    def _con_pass(self):
        ''' connect using provided password '''
        t = paramiko.Transport((self.task.hostname, self.task.port))
        if self.debug:
            Log.debug('th{} connecting using password'.format(self.id))
        t.connect(username=self.task.username, password=self.task.password)
        return t

    def _con_agent(self):
        ''' connect using agent '''
        t = paramiko.Transport((self.task.hostname, self.task.port))
        err = 'ok'
        if self.debug:
            Log.debug('th{} connecting using agent'.format(self.id))
        agent = paramiko.agent.Agent()
        keys = agent.get_keys()
        # try all keys
        for key in keys:
            t = paramiko.Transport((self.task.hostname, self.task.port))
            fp = binascii.hexlify(key.get_fingerprint()).decode("utf-8")
            if self.debug:
                Log.debug('th{} trying with key {}'.format(self.id, fp))
            try:
                t.connect(username=self.task.username, pkey=key)
            except paramiko.ssh_exception.SSHException as e:
                if self.debug:
                    Log.debug('th{} key {} failed'.format(self.id, fp))
                continue
            if t.is_authenticated():
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
        if self.debug:
            Log.debug('th{} initfiles'.format(self.id))
        for f in files:
            lpath = os.path.join(ldir, f)
            if self._is_excluded(lpath):
                continue
            rpath = os.path.join(rdir, f)
            if self.debug:
                Log.log('th{} init file: {}'.format(self.id, rpath))
            if not self.copy(lpath, rpath):
                return False
        return True

    def _init_dirs(self, dirs, ldir, rdir):
        ''' create multiple directories to remote '''
        if self.debug:
            Log.debug('th{} initdirs'.format(self.id))
        for d in dirs:
            lpath = os.path.join(ldir, d)
            if self._is_excluded(lpath):
                continue
            rpath = os.path.join(rdir, d)
            if self.debug:
                Log.debug('th{} init dir: {}'.format(self.id, rpath))
            if self.exists(rpath):
                continue
            if not self.mkdir(rpath):
                return False
        return True

    def initsync(self, ldir, rdir):
        ''' sync local directory on remote '''
        if self.debug:
            Log.debug('th{} initsync dir {} with {}'.format(self.id,
                                                            ldir,
                                                            rdir))
        try:
            for cur, subd, files in os.walk(ldir):
                com = os.path.commonpath([ldir, cur])
                rcur = os.path.join(rdir, cur[len(com)+1:])
                if not self._init_files(files, cur, rcur):
                    return False
                if not self._init_dirs(subd, cur, rcur):
                    return False
                for sub in subd:
                    lsub = os.path.join(cur, sub)
                    if self._is_excluded(lsub):
                        continue
                    rpath = os.path.join(rcur, sub)
                    if self.debug:
                        Log.debug('th{} init sub: {}'.format(self.id, rpath))
                    if not self.mkdir(rpath):
                        return False
        except Exception as e:
            raise SyncException('initsync: {}'.format(e))
        return True

    def _is_excluded(self, path):
        if not self.task.exclude:
            # ignore if no exclude pattern
            return False
        exc = any([fnmatch.fnmatch(path, p) for p in self.task.exclude])
        if exc and self.debug:
            Log.debug('th{} \"{}\" excluded from sync'.format(self.id, path))
        return exc

    def copy(self, lpath, rpath):
        ''' copy file to the remote '''
        if not os.path.exists(lpath):
            return False
        d = os.path.dirname(rpath)
        if not self.exists(d):
            if self.debug:
                Log.debug('th{} create remote dir: {}'.format(self.id, d))
            if not self.mkdir(d):
                return False
        if self.debug:
            Log.debug('th{} copy {} to {}'.format(self.id, lpath, rpath))
        try:
            self.sftp.put(lpath, rpath)
            self.chattr(lpath, rpath)
        except FileNotFoundError as e:
            Log.err('copy cannot create file {}: {}'.format(rpath, e))
            return False
        except PermissionError as e:
            Log.err('copy cannot create file {}: {}'.format(rpath, e))
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def mkdirp(self, path):
        ''' mkdir -p recursive equivalent '''
        if self.debug:
            Log.debug('th{} mkdir -p {}'.format(self.id, path))
        (head, tail) = os.path.split(path)
        if head and not self.exists(head):
            self.mkdirp(head)
        if tail:
            self.mkdir(path)

    def mkdir(self, path):
        ''' mkdir on remote '''
        if self.exists(path):
            return True
        if self.debug:
            Log.debug('th{} mkdir {}'.format(self.id, path))
        try:
            self.sftp.mkdir(path)
        except FileNotFoundError as e:
            Log.err('cannot create dir \"{}\": {}'.format(path, e))
            return False
        except PermissionError as e:
            Log.err('cannot create dir \"{}\": {}'.format(rpath, e))
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
                if self.debug:
                    Log.debug('th{} rm -r {}'.format(self.id, path))
                self.sftp.rmdir(path)
            elif self.is_file(path):
                if self.debug:
                    Log.debug('th{} rm {}'.format(self.id, path))
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
            return False
        if not self.exists(rpath):
            return False
        if self.debug:
            Log.debug('th{} chattr {}'.format(self.id, rpath))
        try:
            self.sftp.chmod(rpath, self._get_mode(lpath))
        except PermissionError as e:
            Log.err('chattr cannot create file {}: {}'.format(rpath, e))
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def mv(self, rsrc, rdst):
        if not self.exists(rsrc):
            return True
        if self.debug:
            Log.debug('th{} mv {} {}'.format(self.id, rsrc, rdst))
        try:
            self.sftp.rename(rsrc, rdst)
        except PermissionError as e:
            Log.err('mv cannot create file {}: {}'.format(rpath, e))
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
            # ok that proves it doesn't exist
            return False
        except OSError as e:
            Log.err('socket error: {}'.format(e))
            return False
        return True

    def execute(self, cmd):
        ''' execute command on remote through sftp '''
        if self.debug:
            Log.debug('th{} run on remote: \"{}\"'.format(self.id, cmd))
        channel = self.trans.open_session()
        # this will execute in default dir (usually $HOME)
        # unless forced using below lines
        # chd = 'cd {}'.format(self.task.remote)
        # channel.exec_command(chd)
        channel.exec_command(cmd)
        ret = channel.recv_exit_status()
        if self.debug:
            Log.debug('th{} command returned: {}'.format(self.id, ret))
        if ret == 0:
            try:
                data = channel.recv(self.BUFSZ).decode()
                Log.log('th{} command stdout: \n{}'.format(self.id, data))
            except socket.timeout as e:
                pass
        else:
            Log.log('th{} command returned error: {}'.format(self.id, ret))
        channel.close()
        return True

    ###########################################################
    # file operations helpers
    ###########################################################
    def _get_mode(self, lpath):
        '''' return attrib of local file '''
        return os.stat(lpath).st_mode
