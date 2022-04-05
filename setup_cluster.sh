#!/bin/bash

# set -x;

cp config ~/.ssh

# config key
if [ ! -f "`echo ~`/.ssh/id_rsa" ]; then
    ssh-keygen -f ~/.ssh/id_rsa -t rsa -N ''
fi

echo "What is your username?"
read SSH_USER
export SSH_USER
echo "What is your password?"
read -s PASSWORD 
export PASSWORD
HOSTBASE="10.0.0."
START=11
END=33

for i in $(seq -f "$HOSTBASE%g" $START $END); do
    export HOST=$i
    expect -c '
    set SSH_USER $env(SSH_USER)
    set HOST $env(HOST)
    set PASSWORD $env(PASSWORD)
    spawn ssh-copy-id $SSH_USER@$HOST
    expect {
        "continue" {
            send "yes\n";
            exp_continue
        }
        "password:" {
            send "$PASSWORD\n";
        }
    }
    expect eof'

    echo "Done $HOST"
done;
