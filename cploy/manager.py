"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Manager sitting between workers and the communication medium
"""

import os
import threading
import queue
import time
import json
import shlex
import string
from docopt import docopt, DocoptExit

# local imports
from cploy.log import Log
from cploy.task import Task
from cploy.sftp import Sftp
from cploy.worker import Worker
from cploy.com import Com
from cploy.message import Message as Msg
from cploy.exceptions import *
from . import __usage__ as USAGE


class Manager:

    def __init__(self, args, socketpath, front=False,
                 savefile=None, debug=False):
        self.args = args
        self.socketpath = socketpath
        self.front = front
        self.savefile = savefile
        self.debug = debug
        self.threadid = 1

        self.stopreq = threading.Event()
        self.sockthread = None
        self.lthreads = []
        self.hashes = []
        self.rqueue = queue.Queue()

    def start(self, actions=[]):
        ''' start the manager '''
        if actions:
            msg = self._process_actions(actions)
            if not msg == Msg.ack:
                return False
        if self.debug:
            Log.debug('starting communication ...')
        self._start_com()
        return True

    def _process_actions(self, actions):
        ''' process all actions in list '''
        self._check_hashes()
        msg = []
        for action in actions:
            try:
                action = json.loads(action)
                if not action:
                    continue
                if self.debug:
                    Log.debug('executing task: \"{}\"'.format(action['cli']))
                self._work(action)
                if self.debug:
                    Log.debug('task started: \"{}\"'.format(action['cli']))
            except Exception as e:
                Log.err('task \"{}\" failed: {}'.format(action, e))
                msg.append(str(e))
        if not msg:
            msg = [Msg.ack]
        return ', '.join(msg)

    def callback(self, action):
        ''' process command received through the communication thread '''
        msg = Msg.ack
        if self.debug:
            Log.debug('callback received message: \"{}\"'.format(action))

        self._check_hashes()
        if action == Msg.stop:
            self.stopreq.set()
        elif action == Msg.info:
            msg = self.get_info()
        elif action == Msg.debug:
            self._toggle_debug(not self.debug)
            msg = 'daemon debug is now {}'.format(self.debug)
        elif action.startswith(Msg.unsync):
            id = int(action.split()[1])
            if id < self.threadid:
                t = next((x for x in self.lthreads if x.id == id), None)
                self._stop_thread(t)
                msg = self.get_info()
                self.hashes.remove(t.task.hash())
            else:
                msg = 'no such task'
        elif action.startswith(Msg.resync):
            id = int(action.split()[1])
            if id < self.threadid:
                t = next((x for x in self.lthreads if x.id == id), None)
                t.queue.put(Msg.resync)
            else:
                msg = 'no such task'
        elif action.startswith(Msg.resume):
            path = action.split()[1]
            msg = self._resume(path)
        else:
            msg = self._process_actions([action])
        return msg

    def _check_hashes(self):
        ''' go through task and remove dead ones '''
        new = []
        for t in self.lthreads:
            if not t.thread.is_alive():
                continue
            check = t.task.hash()
            new.append(check)
        self.hashes = new

    def get_info(self):
        ''' return info from all threads '''
        cnt = 0
        for t in self.lthreads:
            if t.thread.is_alive():
                cnt += 1
                t.queue.put(Msg.info)

        msg = '{} thread(s) running'.format(cnt)
        # give some time to threads to answer
        time.sleep(1)
        while not self.rqueue.empty():
            msg += '\n\t{}'.format(self.rqueue.get())
        if self.debug:
            Log.debug('info: {}'.format(msg))
        return msg

    def _stop_thread(self, lthread):
        ''' stop all threads '''
        if not lthread:
            return
        lthread.queue.put(Msg.stop)
        if self.debug:
            Log.debug('waiting for thread {} to stop'.format(lthread.id))
        lthread.thread.join()
        if self.debug:
            Log.debug('thread {} stopped'.format(lthread.id))

    def _toggle_debug(self, debug):
        ''' toggle debug in all threads '''
        self.debug = debug
        self.sock.debug = debug
        for t in self.lthreads:
            t.queue.put(Msg.debug)

    def _edit_resumes(self, argv, path):
        '''edit the command live'''
        if argv[0] == 'sync':
            if argv[1] == '.':
                argv[1] = os.path.dirname(path)
            else:
                argv[1] = string.Template(argv[1]).substitute(os.environ)
            argv[1] = os.path.abspath(argv[1])
        return argv

    def _resume(self, path):
        ''' resume tasks from file '''
        clis = []
        if not path or not os.path.exists(path):
            err = 'resume path does not exist: \"{}\"'.format(path)
            Log.err(err)
            return clis
        Log.log('loading sync from file: \"{}\"'.format(path))
        with open(path, 'r') as fd:
            clis = fd.readlines()
        clis = [l.strip() for l in clis]
        jsons = []
        for cli in clis:
            Log.log('parsing resuming task: \"{}\"'.format(cli))
            argv = shlex.split(cli)
            Log.log('argv: \"{}\"'.format(argv))
            argv = self._edit_resumes(argv, path)
            Log.log('argv after edit: \"{}\"'.format(argv))
            try:
                args = docopt(USAGE, help=False, argv=argv)
            except DocoptExit as e:
                Log.err('docopt error: {}'.format(e))
                continue
            args['cli'] = cli
            jsons.append(json.dumps(args))
        if not jsons:
            err = 'no task to resume'
            Log.err(err)
            return err
        Log.log('resuming {} task(s)'.format(len(jsons)))
        return self._process_actions(jsons)

    def _save(self, clis):
        ''' save tasks to file '''
        if not self.savefile:
            return
        if not clis:
            return
        # start by reading the saves
        saves = []
        if os.path.exists(self.savefile):
            with open(self.savefile, 'r') as fd:
                saves = fd.readlines()
        # remove empty lines and clean
        saves = [x.rstrip() for x in saves if x != '\n']
        # deduplicates saves
        saves.extend(clis)
        saves = list(set(saves))
        # save to file
        with open(self.savefile, 'w') as fd:
            for save in saves:
                fd.write('{}\n'.format(save))
        if clis:
            Log.log('tasks saved to {}'.format(self.savefile))

    def _start_com(self):
        ''' start the communication '''
        self.sock = Com(self.socketpath, debug=self.debug)
        try:
            self.sock.listen(self.callback)
        except Exception as e:
            Log.err(e)
        # blackhole
        self.sock.stop()

        clis = []
        for t in self.lthreads:
            self._stop_thread(t)
            clis.append(t.task.get_cli())
        self._save(clis)

        if self.debug:
            Log.debug('all threads have stopped, stopping')

    def _work(self, args):
        ''' launch the syncing '''
        if self.debug:
            Log.debug('creating task: \"{}\"'.format(args['cli']))
        try:
            task = Task(args)
        except SyncException as e:
            Log.err('error creating task: {}'.format(e.msg))
            raise e
        check = task.hash()
        if check in self.hashes:
            Log.err('sync already being done')
            raise SyncException('duplicate of existing sync')

        Log.log('connecting with sftp')
        sftp = Sftp(task, self.threadid, debug=self.debug)
        try:
            sftp.connect()
        except ConnectionException as e:
            Log.err('error connecting: {}'.format(e.msg))
            raise e
        except SyncException as e:
            Log.err('error connecting: {}'.format(e.msg))
            raise e

        # try to do first sync
        Log.log('first sync initiated')
        if not sftp.initsync(task.local, task.remote):
            sftp.close()
            err = 'unable to sync dir'
            Log.err(err)
            raise SyncException(err)

        self.hashes.append(check)

        # work args
        inq = queue.Queue()

        # create the thread worker
        if self.debug:
            Log.debug('create worker')
        worker = Worker(task, sftp, inq,
                        self.rqueue, debug=self.debug,
                        force=task.force)
        args = (self.stopreq, )
        t = threading.Thread(target=worker.start, args=args)

        # record this thread
        lt = Lthread(t, self.threadid, inq, task)
        self.lthreads.append(lt)
        self.threadid += 1

        # start the thread
        if self.debug:
            Log.debug('start thread {}'.format(lt.id))
        t.start()


class Lthread:

    def __init__(self, thread, id, queue, task):
        self.thread = thread
        self.id = id
        self.queue = queue
        self.task = task
