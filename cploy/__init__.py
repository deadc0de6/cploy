"""
author: deadc0de6 (https://github.com/deadc0de6)
Copyright (c) 2018, deadc0de6
"""

import sys
import os

__banner__ = 'cploy'
__version__ = '0.1'

__usage__ = '''
{0}
Usage:
    {0} sync [-dfF] [-p <port>] [-u <user>] [-P <pass>]
        [-k <key>] [-K <pass>] [-c <cmd>] [-e <pattern>...]
        <local_path> <hostname> <remote_path>
    {0} daemon [-d] (start | stop | restart)
    {0} daemon [-d] (info | ping | debug)
    {0} daemon unsync <id>
    {0} daemon resync <id>
    {0} --help
    {0} --version

Options:
    -p --port=<port>          SSH port to use [default: 22].
    -u --user=<user>          username for SSH [default: {1}].
    -k --key=<key>            Path of SSH private key to use.
    -P --pass=<pass>          SSH password to use.
    -K --keypass=<pass>       SSH private key passphrase.
    -e --exclude=<pattern>    Pattern to exclude using fnmatch.
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
