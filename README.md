# CPLOY

[![Build Status](https://travis-ci.org/deadc0de6/cploy.svg?branch=master)](https://travis-ci.org/deadc0de6/cploy)
[![PyPI version](https://badge.fury.io/py/cploy.svg)](https://badge.fury.io/py/cploy)
[![Python](https://img.shields.io/pypi/pyversions/cploy.svg)](https://pypi.python.org/pypi/cploy)
[![License: GPL v3](https://img.shields.io/badge/License-GPL%20v3-blue.svg)](http://www.gnu.org/licenses/gpl-3.0)

*The ad hoc continuous deployment solution for developers*

I sometimes have to code stuff that needs to be deployed and run on remote hosts.
Since I don't have all my prefs/settings/dotfiles/etc on the remote, I usually code
on local and have a small one-liner lying around that allows me to quickly deploy
the code (with `scp` or similar) and run some command on the other side (with `ssh` for example).
This is not optimal and that's the reason I created *cploy*.

*Cploy* allows to mirror changes performed on a local directory to a remote
host through SSH. A specific command (bash one-liner for example) can be run
after any change, for example to trigger a build or execute a script.

Features:

  * handle multiple syncs in parallel
  * secure sync through SSH
  * can be daemonized
  * allows to provide a specific command to run on each local change
  * allows to exclude some files from sync

Quick start:
```bash
# install cploy
sudo pip3 install cploy
# start the daemon
cploy daemon start
# add a directory to sync
cploy sync /tmp/local someuser@somehost /tmp/remote
```

see [usage](#usage) for more info

---

**Table of Contents**

* [Installation](#installation)
* [Usage](#usage)

  * [Adding a task](#adding-a-task)
  * [Talking with the daemon](#talking-with-the-daemon)
  * [Exclusion](#exclusion)
  * [Sync events](#sync-events)
  * [Run a command on change](#run-a-command-on-change)

* [Contribution](#contribution)

# Installation

To install run:
```bash
$ sudo pip3 install cploy
```

Or from github directly
```bash
$ cd /tmp; git clone https://github.com/deadc0de6/cploy && cd cploy
$ sudo python3 setup.py install
$ cploy --help
```

To work with *cploy* without installing it, you can do the following
```bash
$ cd /tmp; git clone https://github.com/deadc0de6/cploy && cd cploy
$ sudo pip3 install -r requirements.txt
$ python3 -m cploy.cploy --help
```

or install it in a virtualenv
```bash
$ cd /tmp; git clone https://github.com/deadc0de6/cploy && cd cploy
$ virtualenv -p python3 env
$ source env/bin/activate
$ python setup.py install
$ cploy --help
```

# Usage

The usual way of using *cploy* is by starting the daemon and adding
tasks to it (directory to mirror on a remote host).

Once a new task is added, every changes in the monitored directory
is mirrored on the remote host through SSH.

Start the daemon
```bash
$ cploy daemon start --debug
```

and then add a task to it:
```bash
# sync dir /tmp/local on localhost to
# /tmp/remote on host "somehost"
$ cploy sync /tmp/local/ somehost /tmp/remote
```

Check the logs for any issue under `/tmp/cploy/cploy.log`.

Usage:
```
cploy

Usage:
    cploy sync [-dfF] [-p <port>] [-u <user>] [-P <pass>]
        [-k <key>] [-K <pass>] [-c <cmd>] [-e <pattern>...]
        <local_path> <hostname> <remote_path>
    cploy daemon [-d] (start | stop | restart)
    cploy daemon [-d] (info | ping | debug)
    cploy daemon unsync <id>
    cploy daemon resync <id>
    cploy --help
    cploy --version

Options:
    -p --port=<port>          SSH port to use [default: 22].
    -u --user=<user>          username for SSH [default: $USER].
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
```

## Adding a task

Connections to a remote hosts is done using SFTP (SSH). Multiple
options can be changed: connection with password, with SSH keys, using
the SSH agent, different port, different username, etc.

Besides using the above switches, The *<hostname>* argument can also be
provided using a compact format similar to what the SSH client provides:
```
<username>@<hostname>:<port>
```

After adding a task, make sure to check the daemon to see if the task has
been added successfully with `cploy daemon info`. In case it wasn't, checking
the logs in `/tmp/cploy/cploy.log` usually allows to identify the issue.

Once a new task is added, *cploy* will start by copying any local existing files to
the remote directory to initiate the mirror. Then, any change to the local directory
is applied on the remote.

Requirements:

* SSH access is working (obviously)
* remote host key is trusted
* local directory exists (`<local_path>`)
* remote directory does not exist (`<remote_path>`) unless `--force` is used

## Talking with the daemon

A few commands are available to talk to the daemon:

* **start**: start the daemon
* **stop**: stop the daemon
* **restart**: stop and then start the daemon
* **info**: get a list of current tasks
* **ping**: ping the daemon
* **debug**: toggle debug flag
* **unsync**: stop syncing a specific task
* **resync**: do a full sync starting from local of the sync'ed directory

If you prefer not to use the daemon, *cploy*'s daemon can also be run in the foreground
by using the `--front` switch. However only a single task can be added to it then.

Getting information from the daemon allows to see the different task
running and their id:

```bash
$ cploy daemon info
```

## Exclusion

Files can be excluded within the monitored directory by using `--exclude`.
Matching is done using [fnmatch](https://docs.python.org/3.4/library/fnmatch.html).

Example: exclude any hidden files:
```
--exclude '*/.*'
```

Example: exclude any files containing *test*
```
--exclude '*/test*'
```

## Sync events

Here is a list of changes that are sync'ed:

* File creation
* File deletion
* File attribute change
* File content modification
* File move

## Monitor the changes

If the daemon is running, logs are written in `/tmp/cploy/cploy.log`.

## Run a command on change

A command can be added to a task using the `--command` switch.
The provided command will be run on the remote anytime a change
is applied on the local monitored directory.

*Cploy* uses paramiko [exec\_command](http://docs.paramiko.org/en/2.4/api/client.html)
to execute the command which will be run from the default directory of the user
(usually $HOME).

Therefore if the remote directory is `/tmp/remote` and the script to
run remotely is located in `/tmp/remote/test.sh`, the command argument
will be `--command="/tmp/remote/test.sh"`.

Currently the specified command is run on any change with no control
over the granularity.

# Issues and bugs

This hasn't been extensively tested so please do report any bug you find.
Starting the daemon with `--debug` is always helpful to get more info
(or toggle it with the daemon command `debug`).

# Contribution

If you are having trouble installing or using *cploy*, open an issue.

If you want to contribute, feel free to do a PR (please follow PEP8).

Have a look at the *design* directory.

# License

This project is licensed under the terms of the GPLv3 license.
