"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Manager sitting between workers and the communication medium
"""

import threading
import queue
import time

# local imports
from cploy.log import Log
from cploy.task import Task
from cploy.sftp import Sftp
from cploy.worker import Worker
from cploy.com import Com
from cploy.message import Message as Msg


class Manager:

    def __init__(self, args, socketpath,
                 front=False, debug=False):
        self.args = args
        self.socketpath = socketpath
        self.front = front
        self.debug = debug
        self.threadid = 1

        self.stopreq = threading.Event()
        self.sockthread = None
        self.lthreads = []
        self.rqueue = queue.Queue()

    def start(self, actions=[]):
        ''' start the manager '''
        if actions:
            try:
                self._process_actions(actions)
            except Exception as e:
                Log.err('error starting task: {}'.format(e))
                return False
        if self.debug:
            Log.debug('starting communication ...')
        self._start_com()
        return True

    def _process_actions(self, actions):
        ''' process all actions in list '''
        for action in actions:
            if not action:
                continue
            if self.debug:
                Log.debug('executing action: {}'.format(action))
            self._work(action)
            if self.debug:
                Log.debug('task successfully started: {}'.format(action))

    def callback(self, action):
        ''' process command received through the communication thread '''
        msg = Msg.ack
        if self.debug:
            Log.debug('received message: \"{}\"'.format(action))

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
        elif action.startswith(Msg.resync):
            id = int(action.split()[1])
            if id < self.threadid:
                t = next((x for x in self.lthreads if x.id == id), None)
                t.queue.put(Msg.resync)
        else:
            try:
                self._process_actions([action])
            except Exception as e:
                Log.err('error starting task: {}'.format(e))
                msg = e.msg
        return msg

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
            msg += '\n{}'.format(self.rqueue.get())
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

    def _start_com(self):
        ''' start the communication '''
        self.sock = Com(self.socketpath, debug=self.debug)
        try:
            self.sock.listen(self.callback)
        except Exception as e:
            Log.err(e)
        # blackhole
        self.sock.stop()
        for t in self.lthreads:
            self._stop_thread(t)
        if self.debug:
            Log.debug('all threads have stopped, stopping')

    def _work(self, args):
        ''' launch the syncing '''
        task = Task(args)

        if self.debug:
            Log.debug('connecting with sftp')
        sftp = Sftp(task, self.threadid, debug=self.debug)
        sftp.connect()

        # try to do first sync
        if self.debug:
            Log.debug('init sync initiated')
        if not sftp.initsync(task.local, task.remote):
            sftp.close()
            err = 'unable to sync dir'
            raise SyncException(err)

        # work args
        inq = queue.Queue()

        # create the thread worker
        worker = Worker(task, sftp, inq,
                        self.rqueue, debug=self.debug,
                        force=task.force)
        args = (self.stopreq, )
        t = threading.Thread(target=worker.start, args=args)

        # record this thread
        self.lthreads.append(Lthread(t, self.threadid, inq))
        self.threadid += 1

        # start the thread
        t.start()


class Lthread:

    def __init__(self, thread, id, queue):
        self.thread = thread
        self.id = id
        self.queue = queue
