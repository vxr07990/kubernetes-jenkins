#!/bin/bash

set -ex
source ./maintenance/helpers-lxc-node.sh

container=${NODE_NAME:-"juju-client-box"}

lxc launch ubuntu:16.04 $container

while ! lxc info $container | grep -qE 'eth0:\sinet\s'; do
    sleep 3
done

RUN sed -i "$ a export PATH=\$PATH:/snaps/bin/" /home/ubuntu/.bashrc
PUSH integration-tests/install-deps.sh /home/ubuntu/
RUN /home/ubuntu/install-deps.sh

RUN mkdir -p /home/ubuntu/.local/share/juju

PUSH ~/.local/share/juju/accounts.yaml /home/ubuntu/.local/share/juju/
PUSH ~/.local/share/juju/models.yaml /home/ubuntu/.local/share/juju/
PUSH ~/.local/share/juju/controllers.yaml /home/ubuntu/.local/share/juju/
PUSH ~/.local/share/juju/credentials.yaml /home/ubuntu/.local/share/juju/
RUN mkdir -p /var/lib/jenkins/.local/share/juju
PUSH ~/.local/share/juju/foo.json /var/lib/jenkins/.local/share/juju/
RUN chown ubuntu:ubuntu -R /home/ubuntu/.local

# Allow ssh access
RUN mkdir -p /home/ubuntu/.ssh
PUSH ~/.ssh/id_rsa.pub /home/ubuntu/.ssh/authorized_keys
RUN chmod 600 /home/ubuntu/.ssh/authorized_keys
RUN chown ubuntu:ubuntu /home/ubuntu/.ssh/authorized_keys

# Jenkins agent needs java
RUN apt-get install -y default-jre

RUN mkdir -p /home/ubuntu/bin
RUN wget https://ci.kubernetes.juju.solutions/jnlpJars/slave.jar
RUN mv slave.jar /home/ubuntu/bin

echo "Your lxc container is ready to be added as jenkins node."
echo "Go to Manage Jenkins -> Manage Nodes -> New Node and select"
echo "Launch agent via execution of command on the master and enter the following:"
echo "ssh -o StrictHostKeyChecking=no -v ubuntu@<container_ip> java -jar ~/bin/slave.jar"
lxc list
