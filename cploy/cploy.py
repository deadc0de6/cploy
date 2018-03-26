"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
The ad hoc continuous deployment tool
"""

import sys
import os
from docopt import docopt
import daemon
import signal
try:
    import daemon.pidlockfile as pidlockfile
except ImportError:
    import daemon.pidfile as pidlockfile
import time
import datetime

# local imports
from . import __version__ as VERSION
from . import __banner__ as BANNER
from . import __usage__ as USAGE
from .log import Log
from .manager import Manager
from .com import Com
from .message import Message as Msg

DIRPATH = '/tmp/{}'.format(BANNER)
PIDPATH = '{}/{}.pid'.format(DIRPATH, BANNER)
LOGPATH = '{}/{}.log'.format(DIRPATH, BANNER)
SPATH = '{}/{}.socket'.format(DIRPATH, BANNER)
MAXWAIT = 5  # seconds
STIMEOUT = 15  # seconds


def daemon_send(data, debug, quiet=False):
    ''' communicate with daemon '''
    if not os.path.exists(SPATH):
        if debug:
            Log.debug('daemon not running')
        return False
    s = Com(SPATH, debug=debug)
    try:
        msg = s.send(data, timeout=STIMEOUT)
    except Exception as e:
        if not quiet:
            Log.err(e)
        return False
    if not msg:
        if not quiet:
            err = 'error communicating with daemon'
            Log.err(err)
        return False
    if debug:
        Log.debug('received back: \"{}\"'.format(msg))
    if not quiet:
        Log.log(msg)
    return True


def daemon_cmd(args, debug):
    ''' run command related to the daemon '''
    ret = True
    if args['start']:
        Log.log('starting daemon ...')
        daemonize(args, debug)
    elif args['restart']:
        Log.log('re-starting daemon ...')
        if daemon_send(Msg.stop, debug, quiet=True):
            wait_for_stop(debug)
        pid = get_pid(PIDPATH)
        if pid:
            Log.err('daemon still runing: pid {}'.format(pid))
            return False
        daemonize(args, debug)
    elif args['stop']:
        Log.log('stopping daemon ...')
        if daemon_send(Msg.stop, debug):
            wait_for_stop(debug)
    elif args['info']:
        Log.log('getting info from daemon ...')
        ret = daemon_send(Msg.info, debug)
    elif args['debug']:
        Log.log('toggle debug on daemon ...')
        ret = daemon_send(Msg.debug, debug)
    elif args['ping']:
        ret = daemon_send(Msg.ping, debug, quiet=True)
    elif args['unsync']:
        id = args['<id>']
        Log.log('unsync task {} ...'.format(id))
        msg = '{} {}'.format(Msg.unsync, id)
        ret = daemon_send(msg, debug)
    elif args['resync']:
        id = args['<id>']
        Log.log('resync task {} ...'.format(id))
        msg = '{} {}'.format(Msg.resync, id)
        ret = daemon_send(msg, debug)
    if not ret:
        Log.err('error communicating with daemon, is it running?')
    return ret


def sig_stop(signum, frame):
    ''' signal handlers '''
    daemon_send(Msg.stop, False, quiet=True)


def start_manager(args, debug, actions=[]):
    ''' start the manager '''
    Log.log('daemon pid: {}'.format(os.getpid()))
    manager = Manager(args, SPATH, front=args['--front'], debug=debug)
    if not manager.start(actions=actions):
        Log.err('manager failed to start')
        return False
    return True


def daemonize(args, debug, actions=[]):
    ''' start the daemon for the manager '''
    pid = get_pid(PIDPATH)
    if pid:
        Log.log('daemon already running (pid: {})'.format(pid))
        return
    Log.log('daemon started, logging to {}'.format(LOGPATH))
    context = get_context(debug)
    context.open()
    with context:
        start_manager(args, debug, actions=actions)


def wait_for_stop(debug):
    ''' wait for daemon to stop '''
    start = datetime.datetime.now()
    if debug:
        Log.debug('waiting for pidfile to disappear ...')
    while get_pid(PIDPATH):
        time.sleep(1)
        end = datetime.datetime.now()
        sec = (end-start).seconds
        if sec > MAXWAIT:
            Log.err('daemon has not stopped correctly')
            break
    if not get_pid(PIDPATH):
        Log.log('daemon has stopped')


def get_pid(path):
    ''' get daemon pid from file '''
    if not os.path.exists(path):
        return None
    lock = pidlockfile.PIDLockFile(path, threaded=False)
    if lock.is_locked():
        return open(path, 'r').read()
    return None


def get_context(debug):
    ''' return daemon context '''
    sysout = open(LOGPATH, 'a')
    syserr = open(LOGPATH, 'a')
    pf = pidlockfile.PIDLockFile(PIDPATH, threaded=False)
    context = daemon.DaemonContext(
            signal_map={
                signal.SIGTERM: sig_stop,
                signal.SIGTSTP: sig_stop,
            },
            stdout=sysout,
            stderr=syserr,
            pidfile=pf,
        )
    return context


def argv_to_str(argv):
    ''' join args and respect quotes '''
    return ' '.join(["'"+a+"'" if ' ' in a else a for a in argv])


def main():
    ''' entry point '''
    ret = True
    args = docopt(USAGE, version=VERSION)
    front = args['--front']
    debug = args['--debug']
    action = argv_to_str(sys.argv[1:])
    pid = get_pid(PIDPATH)

    if not os.path.exists(DIRPATH):
        os.mkdir(DIRPATH)

    if args['sync']:
        if front:
            if pid:
                Log.err('manager already running: pid {}'.format(pid))
                return False
            if debug:
                Log.debug('starting manager in foreground ...')
            ret = start_manager(args, debug, actions=[action])
        else:
            if not pid:
                Log.log('starting manager in background ...')
                daemonize(args, debug, actions=[action])
            else:
                Log.log('manager already running ... sending new task')
                daemon_send(action, debug)
    elif args['daemon']:
        ret = daemon_cmd(args, debug)
    return ret


if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)
