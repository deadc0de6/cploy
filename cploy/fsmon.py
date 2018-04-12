"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
Filesystem monitoring class using pyinotify
"""

import pyinotify
import fnmatch
import os

# local imports
from cploy.log import Log


class Fsmon:

    mask = pyinotify.IN_DELETE | \
           pyinotify.IN_CREATE | \
           pyinotify.IN_ATTRIB | \
           pyinotify.IN_CLOSE_WRITE | \
           pyinotify.IN_MOVED_FROM | \
           pyinotify.IN_MOVED_TO

    def __init__(self, worker, exclude=None, debug=False):
        self.worker = worker
        self.id = self.worker.id
        self.excl = exclude
        self.debug = debug
        self.wm = pyinotify.WatchManager()
        self.handler = EventHandler(self.worker, exclude=self.excl,
                                    debug=self.debug)
        self.notifier = pyinotify.ThreadedNotifier(self.wm, self.handler)
        self.started = False

    def start(self):
        ''' start monitoring for changes '''
        if self.started:
            return False
        local = self.worker.get_local()
        self.notifier.start()
        self.wdd = self.wm.add_watch(local, self.mask,
                                     rec=True, auto_add=True)
        if self.debug:
            Log.debug('th{} adding watch on {}'.format(self.id, local))
        Log.log('th{} filesystem monitoring started'.format(self.id))
        self.started = True
        return self.started

    def stop(self):
        ''' stop monitoring for changes '''
        if not self.started:
            return True
        # remove watches
        self.wm.rm_watch(self.wdd.values(), rec=True)
        # stop the notifier
        self.notifier.stop()
        self.started = False
        Log.log('th{} filesystem monitoring stopped'.format(self.id))
        return True


class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, worker, exclude=None, debug=False):
        self.worker = worker
        self.id = self.worker.id
        self.exclude = exclude
        self.debug = debug

    def _ignore(self, path):
        ''' check if this path needs to be ignored '''
        if not self.exclude:
            return False
        if any([fnmatch.fnmatch(path, p) for p in self.exclude]):
            if self.debug:
                Log.debug('th{} {} ignored'.format(self.id, path))
            return True
        return False

    def process_IN_CREATE(self, event):
        ''' something was created '''
        if not event.dir:
            # only process directory creation
            return
        if self.debug:
            Log.debug('th{} creating: {}'.format(self.id, event.pathname))
        if self._ignore(event.pathname):
            return
        if os.path.exists(event.pathname):
            self.worker.create(event.pathname)

    def process_IN_DELETE(self, event):
        ''' something was deleted '''
        if self.debug:
            Log.debug('th{} removing: {}'.format(self.id, event.pathname))
        if self._ignore(event.pathname):
            return
        self.worker.delete(event.pathname)

    def process_IN_ATTRIB(self, event):
        ''' some attribute changed '''
        if self.debug:
            Log.debug('th{} attrib: {}'.format(self.id, event.pathname))
        if self._ignore(event.pathname):
            return
        if os.path.exists(event.pathname):
            self.worker.attrib(event.pathname)

    def process_IN_CLOSE_WRITE(self, event):
        ''' was written to '''
        if self.debug:
            Log.debug('th{} close-write: {}'.format(self.id, event.pathname))
        if self._ignore(event.pathname):
            return
        if os.path.exists(event.pathname):
            self.worker.mirror(event.pathname)

    def process_IN_MOVED_FROM(self, event):
        ''' first call for moves '''
        if self.debug:
            Log.debug('th{} move from: {}'.format(self.id, event.pathname))
        if not os.path.exists(event.pathname):
            self.worker.delete(event.pathname)

    def process_IN_MOVED_TO(self, event):
        ''' second call for moves '''
        if self.debug:
            Log.debug('th{} move to: {}'.format(self.id, event.pathname))
        if self._ignore(event.pathname):
            return
        if os.path.exists(event.pathname):
            self.worker.mirror(event.pathname)
