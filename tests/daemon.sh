#!/usr/bin/env bash
# author: deadc0de6 (https://github.com/deadc0de6)
# Copyright (c) 2018, deadc0de6

set -v

opt="--debug"

echo "[===] TEST start"
python3 -m cploy.cploy daemon ${opt} start
[ "$?" != "0" ] && echo "ERROR daemon start" && exit 1

sleep 1

echo "[===] TEST info"
python3 -m cploy.cploy daemon ${opt} info
[ "$?" != "0" ] && echo "ERROR daemon info" && exit 1

echo "[===] TEST debug"
python3 -m cploy.cploy daemon ${opt} debug
[ "$?" != "0" ] && echo "ERROR daemon debug" && exit 1

echo "[===] TEST debug"
python3 -m cploy.cploy daemon ${opt} debug
[ "$?" != "0" ] && echo "ERROR daemon debug 2" && exit 1

echo "[===] TEST ping"
python3 -m cploy.cploy daemon ${opt} ping
[ "$?" != "0" ] && echo "ERROR daemon ping" && exit 1

echo "[===] TEST restart"
python3 -m cploy.cploy daemon ${opt} restart
[ "$?" != "0" ] && echo "ERROR daemon restart" && exit 1

echo "[===] TEST stop"
python3 -m cploy.cploy daemon ${opt} stop
[ "$?" != "0" ] && echo "ERROR daemon stop" && exit 1

echo "[===] ok"
exit 0
