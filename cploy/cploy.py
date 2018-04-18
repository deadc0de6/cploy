"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
The ad hoc continuous deployment tool
"""

import sys
import os
import json
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
ERRPATH = '{}/{}.err'.format(DIRPATH, BANNER)
SAVPATH = '{}/{}.save'.format(DIRPATH, BANNER)
SPATH = '{}/{}.socket'.format(DIRPATH, BANNER)
MAXWAIT = 15  # seconds


def daemon_send(data, debug, quiet=False):
    ''' communicate with daemon '''
    if not os.path.exists(SPATH):
        if debug:
            Log.debug('daemon not running')
        return False
    s = Com(SPATH, debug=debug)
    try:
        msg = s.send(data)
    except Exception as e:
        if not quiet:
            Log.log('communication failed')
            Log.log('check daemon status')
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
        if msg == Msg.error:
            Log.log('check the daemon logs under \"{}\"'.format(LOGPATH))
            Log.log('check the daemon erro under \"{}\"'.format(ERRPATH))
    return True


def daemon_cmd(args, debug):
    ''' run command related to the daemon '''
    ret = True
    if args['start']:
        Log.log('starting daemon ...')
        ret = daemonize(args, debug)
    elif args['restart']:
        Log.log('re-starting daemon ...')
        if daemon_send(Msg.stop, debug, quiet=True):
            wait_for_stop(debug)
        pid = get_pid(PIDPATH)
        if pid:
            Log.err('daemon still runing: pid {}'.format(pid))
            return False
        ret = daemonize(args, debug)
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
    elif args['resume']:
        path = norm_path(args['<path>'])
        if not os.path.exists(path):
            Log.err('path \"{}\" does not exist'.format(path))
            return False
        Log.log('resume task from file {} ...'.format(path))
        msg = '{} {}'.format(Msg.resume, path)
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
    manager = Manager(args, SPATH, front=args['--front'],
                      savefile=SAVPATH, debug=debug)
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
    Log.log('daemon started, logging to {} and {}'.format(LOGPATH, ERRPATH))
    context = get_context(debug)
    try:
        context.open()
    except Exception as e:
        Log.err('cannot open context: {}'.format(e))
        return False
    with context:
        start_manager(args, debug, actions=actions)
    return True


def wait_for_stop(debug):
    ''' wait for daemon to stop '''
    start = datetime.datetime.now()
    if debug:
        Log.debug('waiting max {}s for manager to stop'.format(MAXWAIT))
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
        return open(path, 'r').read().rstrip()
    return None


def get_context(debug):
    ''' return daemon context '''
    sysout = open(LOGPATH, 'a')
    syserr = open(ERRPATH, 'a')
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


def norm_path(path):
    ''' normalize path '''
    if not path:
        return path
    path = os.path.expanduser(path)
    path = os.path.abspath(path)
    return path


def exclude_from_file(path):
    ''' read excludes from file '''
    ex = []
    with open(path, 'r') as fd:
        for line in fd:
            ex.append(line.rstrip())
    return ex


def enrich_args(args):
    ''' enrich and fix args '''
    # fix paths
    args['<local_path>'] = norm_path(args['<local_path>'])
    args['--key'] = norm_path(args['--key'])
    # add command-line arguments
    args['cli'] = argv_to_str(sys.argv[1:]).rstrip()
    # parse exclude pattern from file
    if args['--expath']:
        expath = norm_path(args['--expath'])
        if not os.path.exists(expath):
            Log.err('\"{}\" does not exist'.format(expath))
            return None
        ex = exclude_from_file(expath)
        args['--exclude'].extend(ex)
    del args['--expath']
    return args


def main():
    ''' entry point '''
    ret = True
    args = docopt(USAGE, version=VERSION)
    args = enrich_args(args)
    if not args:
        return False
    front = args['--front']
    debug = args['--debug']

    action = json.dumps(args)
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
                Log.log('starting manager in background and adding task')
                ret = daemonize(args, debug, actions=[action])
            else:
                Log.log('manager already running ... sending new task')
                ret = daemon_send(action, debug)
    else:
        ret = daemon_cmd(args, debug)
    return ret


if __name__ == '__main__':
    if main():
        sys.exit(0)
    sys.exit(1)
