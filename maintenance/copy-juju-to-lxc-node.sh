#!/bin/bash

set -ex
source ./maintenance/helpers-lxc-node.sh

container=${NODE_NAME:-"juju-client-box"}
container_exists $container

RUN rm -rf /home/ubuntu/.local/share/juju/*
RUN rm -rf /var/lib/jenkins/.local/share/juju/*
PUSH ~/.local/share/juju/accounts.yaml /home/ubuntu/.local/share/juju/
PUSH ~/.local/share/juju/models.yaml /home/ubuntu/.local/share/juju/
PUSH ~/.local/share/juju/controllers.yaml /home/ubuntu/.local/share/juju/
PUSH ~/.local/share/juju/credentials.yaml /home/ubuntu/.local/share/juju/
RUN mkdir -p /var/lib/jenkins/.local/share/juju
PUSH ~/.local/share/juju/foo.json /var/lib/jenkins/.local/share/juju/
RUN chown ubuntu:ubuntu -R /home/ubuntu/.local

