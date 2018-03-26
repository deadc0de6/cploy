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
            Log.debug('[{}] adding watch on {}'.format(self.id, local))
        Log.log('[{}] filesystem monitoring started'.format(self.id))
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
        Log.log('[{}] filesystem monitoring stopped'.format(self.id))
        return True


class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, worker, exclude=None, debug=False):
        self.worker = worker
        self.id = self.worker.id
        self.exclude = exclude
        self.debug = debug
        self.move_from = None

    def _debug(self, msg):
        if not self.debug:
            return
        msg = '[event][{}] {}'.format(self.id, msg)
        Log.debug(msg)

    def _ignore(self, path):
        ''' check if this path needs to be ignored '''
        if not self.exclude:
            return False
        if any([fnmatch.fnmatch(event.pathname, p) for p in self.exclude]):
            self._debug('{} ignored'.format(event.pathname))
            return True
        return False

    def process_IN_CREATE(self, event):
        ''' something was created '''
        if not event.dir:
            # only process directory creation
            return
        self._debug('creating: {}'.format(self.id, event.pathname))
        if self._ignore(event.pathname):
            return
        if os.path.exists(event.pathname):
            self.worker.create(event.pathname)
        else:
            self._debug('file disappeared: {}'.format(event.pathname))

    def process_IN_DELETE(self, event):
        ''' something was deleted '''
        self._debug('removing: {}'.format(event.pathname))
        if self._ignore(event.pathname):
            return
        self.worker.delete(event.pathname)

    def process_IN_ATTRIB(self, event):
        ''' some attribute changed '''
        self._debug('attrib: {}'.format(event.pathname))
        if self._ignore(event.pathname):
            return
        if os.path.exists(event.pathname):
            self.worker.attrib(event.pathname)
        else:
            self._debug('file disappeared: {}'.format(event.pathname))

    def process_IN_CLOSE_WRITE(self, event):
        ''' was written to '''
        self._debug('close-write: {}'.format(event.pathname))
        if self._ignore(event.pathname):
            return
        if os.path.exists(event.pathname):
            self.worker.mirror(event.pathname)
        else:
            self._debug('file disappeared: {}'.format(event.pathname))

    def process_IN_MOVED_FROM(self, event):
        ''' first call for moves '''
        self._debug('move from: {}'.format(event.pathname))
        self.move_from = event.pathname

    def process_IN_MOVED_TO(self, event):
        ''' second call for moves '''
        self._debug('move to: {}'.format(event.pathname))
        if self._ignore(event.pathname):
            return
        if self.move_from:
            self.worker.move(self.move_from, event.pathname)
            self.move_from = None
