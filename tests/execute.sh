#!/usr/bin/env bash
# author: deadc0de6 (https://github.com/deadc0de6)
# Copyright (c) 2018, deadc0de6

set -ev

opt="--debug"
l=`mktemp -d --suffix=.cploy`
r=`mktemp -d --suffix=.cploy`
dst="${r}/cploy.canary"

echo "[===] TEST command execution"
python3 -m cploy.cploy daemon ${opt} start
[ "$?" != "0" ] && echo "ERROR daemon start" && exit 1

python3 -m cploy.cploy sync ${opt} --force ${l} localhost ${r} --command="echo -n test >> ${dst}"
[ "$?" != "0" ] && echo "ERROR sync" && exit 1

python3 -m cploy.cploy daemon info
[ "$?" != "0" ] && echo "ERROR daemon info" && exit 1

# change some file to trigger command execution
touch ${l}/test
sleep 1

# test remote file is sync'ed
[ ! -e "${r}/test" ] && echo "ERROR file sync" && exit 1

python3 -m cploy.cploy daemon info
[ "$?" != "0" ] && echo "ERROR daemon info 2" && exit 1

python3 -m cploy.cploy daemon stop
[ "$?" != "0" ] && echo "ERROR daemon stop" && exit 1

[ ! -e ${dst} ] && echo "ERROR file not synced" && exit 1
# expect two changes for a file creation thus test+test
[ "`cat ${dst}`" != "testtest" ] && echo "ERROR command not executed" && exit 1

echo "[===] ok"
exit 0