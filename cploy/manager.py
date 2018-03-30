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
from docopt import docopt

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
                print(action)
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
        elif action.startswith(Msg.resync):
            id = int(action.split()[1])
            if id < self.threadid:
                t = next((x for x in self.lthreads if x.id == id), None)
                t.queue.put(Msg.resync)
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

    def _resume(self, path):
        ''' resume tasks from file '''
        clis = []
        if not path or not os.path.exists(path):
            return clis
        with open(path, 'r') as fd:
            clis = fd.readlines()
        clis = [l.strip() for l in clis]
        jsons = []
        for cli in clis:
            args = docopt(USAGE, help=False, argv=shlex.split(cli))
            args['cli'] = cli
            jsons.append(json.dumps(args))
        msg = self._process_actions(jsons)
        return msg

    def _save(self, clis):
        ''' save tasks to file '''
        if not self.savefile:
            return
        with open(self.savefile, 'a') as fd:
            for cli in clis:
                fd.write('{}\n'.format(cli))
        if clis:
            Log.log('syncs saved to {}'.format(self.savefile))

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
