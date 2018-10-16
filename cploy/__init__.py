"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
"""

import sys
import os

__banner__ = 'cploy'
__version__ = '0.6.4'

__usage__ = '''
CPLOY

Usage:
    {0} sync [-dfF] <local_path> <hostname> <remote_path>
             [-p <port>] [-u <user>] [-P <pass>] [-k <key>]
             [-K <pass>] [-c <cmd>] [-e <pattern>...] [-E <path]
    {0} (start | stop | restart) [-d]
    {0} (info | ping | debug) [-d]
    {0} unsync <id> [-d]
    {0} resync <id> [-d]
    {0} resume <path> [-d]
    {0} --help
    {0} --version

Options:
    -p --port=<port>          SSH port to use [default: 22].
    -u --user=<user>          username for SSH [default: {1}].
    -k --key=<key>            Path of SSH private key to use.
    -P --pass=<pass>          SSH password to use.
    -K --keypass=<pass>       SSH private key passphrase.
    -e --exclude=<pattern>    Pattern to exclude using fnmatch.
    -E --expath=<path>        Load exclude pattern(s) from file.
    -c --command=<cmd>        Command to execute on changes.
    -F --front                Do not daemonize.
    -f --force                Force overwrite on remote [default: False].
    -d --debug                Enable debug [default: False].
    -v --version              Show version.
    -h --help                 Show this screen.
'''.format(__banner__, os.environ['USER'])


def main():
    import cploy.cploy
    if cploy.cploy.main():
        sys.exit(0)
    sys.exit(1)
