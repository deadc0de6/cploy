#!/usr/bin/env bash
# author: deadc0de6 (https://github.com/deadc0de6)
# Copyright (c) 2018, deadc0de6

set -v

opt=""
opt="--debug"
t=`mktemp -d --suffix=.cploy`
r=`mktemp -d --suffix=.cploy`

echo "[===] TEST non-existing source"
python3 -m cploy.cploy sync ${opt} --front /tmp/tmp/tmp/nonexisting localhost /tmp/remote
[ "$?" != "1" ] && echo "ERROR non-existing source" && exit 1

echo "[===] TEST bad key"
mkdir -p ${t}
python3 -m cploy.cploy sync ${opt} --front ${t} localhost ${r} -k /tmp/tmp/tmp/badkey
[ "$?" != "1" ] && echo "ERROR bad key" && exit 1

echo "[===] TEST bad password"
mkdir -p ${t}
python3 -m cploy.cploy sync ${opt} --front ${t} localhost ${r} -P "password"
[ "$?" != "1" ] && echo "ERROR bad password" && exit 1

echo "[===] TEST bad port"
mkdir -p ${t}
python3 -m cploy.cploy sync ${opt} --front ${t} localhost ${r} -p 0
[ "$?" != "1" ] && echo "ERROR bad port" && exit 1

rm -rf ${t} ${r}
echo "[===] ok"
exit 0
