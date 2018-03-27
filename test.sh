#!/usr/bin/env bash
# author: deadc0de6 (https://github.com/deadc0de6)
# Copyright (c) 2018, deadc0de6

# make sure to be able to log in through ssh
# on localhost with the current user
# to run those tests

# stop on first error
set -ev

key="~/.ssh/id_rsa"
[ "$1" != "" ] && [ -e "$1" ] && key="$1"

pycodestyle cploy/
pycodestyle tests/

echo "=========================================================="
tests/daemon.sh

echo "=========================================================="
tests/connection.sh ${key}

echo "=========================================================="
tests/execute.sh ${key}
