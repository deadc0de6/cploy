#!/usr/bin/env bash

passphrase=""
keydst="$HOME/.ssh/id_rsa"
auth="$HOME/.ssh/authorized_keys"
known="$HOME/.ssh/known_hosts"
conf="$HOME/.ssh/config"

[ "${TRAVIS}" != "true" ] && echo "not on travis" && exit 1

# start ssh
sudo start ssh
# create ssh key
ssh-keygen -q -t rsa -f "${keydst}" -N "${passphrase}"
# add key to authorized keys
cat "${keydst}" >> "${auth}"
# trust host
ssh-keyscan -t rsa localhost >> ${known}
# ensure key is used
cat << _EOF >> ${conf}
Host localhost
     IdentityFile ${keydst}
_EOF
