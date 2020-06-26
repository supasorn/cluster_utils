#!/bin/bash

# set -x;

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
echo "What is your fist 9 digit of your ip? ex: 192.168.1."
read HOSTBASE
echo "What is the range of the host? ex: 10 111 = range from 192.168.1.10-192.168.1.111"
read START END

for i in $(seq -f "$HOSTBASE%03g" $START $END); do
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
