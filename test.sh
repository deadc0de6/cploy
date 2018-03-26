#!/usr/bin/env bash
# author: deadc0de6 (https://github.com/deadc0de6)
# Copyright (c) 2018, deadc0de6

# make sure to be able to log in through ssh
# on localhost with the current user
# to run those tests

# stop on first error
set -ev

pycodestyle cploy/
pycodestyle tests/

echo "=========================================================="
tests/daemon.sh

echo "=========================================================="
tests/connection.sh

echo "=========================================================="
tests/execute.sh
