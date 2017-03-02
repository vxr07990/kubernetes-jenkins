#!/usr/bin/env bash
# Push the kubernetes charm code, release the charms and grant everyone access.

set -o errexit  # Exit when an individual command fails.
set -o pipefail  # The exit status of the last command is returned.
set -o xtrace  # Print the commands that are executed.

SCRIPT_DIR="$( cd "$( dirname "${0}" )" && pwd )"
if [[ -z "${WORKSPACE}" ]]; then
  export WORKSPACE=${PWD}
fi
ID=${1}
CHANNEL=${2}

# The cloud is an option for this script, default to gce.
CLOUD=${CLOUD:-"gce"}
# The path to the archive of the JUJU_DATA directory for the specific cloud.
JUJU_DATA_TAR="/var/lib/jenkins/juju/juju_${CLOUD}.tar.gz"
# Uncompress the file that contains the Juju data to the workspace directory.
tar -xvzf ${JUJU_DATA_TAR} -C ${WORKSPACE}

# Set the JUJU_DATA directory for this jenkins workspace.
export JUJU_DATA=${SCRIPT_DIR}/juju
export JUJU_REPOSITORY=${SCRIPT_DIR}/charms

# Define the juju functions.
source ${SCRIPT_DIR}/define-juju.sh

# Expand all the charm archives to the charms/builds directory.
CHARMS_BUILDS=${JUJU_REPOSITORY}/builds
tar -xzf ${CHARMS_BUILDS}/easyrsa.tar.gz -C ${CHARMS_BUILDS}
tar -xzf ${CHARMS_BUILDS}/etcd.tar.gz -C ${CHARMS_BUILDS}
tar -xzf ${CHARMS_BUILDS}/flannel.tar.gz -C ${CHARMS_BUILDS}
tar -xzf ${CHARMS_BUILDS}/kubeapi-load-balancer.tar.gz -C ${CHARMS_BUILDS}
tar -xzf ${CHARMS_BUILDS}/kubernetes-e2e.tar.gz -C ${CHARMS_BUILDS}
tar -xzf ${CHARMS_BUILDS}/kubernetes-master.tar.gz -C ${CHARMS_BUILDS}
tar -xzf ${CHARMS_BUILDS}/kubernetes-worker.tar.gz -C ${CHARMS_BUILDS}
ls -al ${CHARMS_BUILDS}/*

ARCH=${ARCH:-"amd64"}
# The resources must be in the current directory.
E2E_RESOURCE=$(ls -1 e2e-*-${ARCH}.tar.gz)
EASYRSA_RESOURCE=$(ls -1 easyrsa-resource-*.tgz)
FLANNEL_RESOURCE=$(ls -1 flannel-resource-*-${ARCH}.tar.gz)
MASTER_RESOURCE=$(ls -1 kubernetes-master-*-${ARCH}.tar.gz)
WORKER_RESOURCE=$(ls -1 kubernetes-worker-*-${ARCH}.tar.gz)

# Get the charm identifiers for each charm, none of them have a series.
E2E=$(charm_id ${ID} "" kubernetes-e2e)
EASYRSA=$(charm_id ${ID} "" easyrsa)
ETCD=$(charm_id ${ID} "" etcd)
FLANNEL=$(charm_id ${ID} "" flannel)
MASTER=$(charm_id ${ID} "" kubernetes-master)
WORKER=$(charm_id ${ID} "" kubernetes-worker)

# Some of the files in JUJU_DATA my not be owned by the ubuntu user, fix that.
CHOWN_CMD="sudo chown -R ubuntu:ubuntu /home/ubuntu/.local/share/juju"
# Create a model just for this run of the tests.
in-charmbox "${CHOWN_CMD} && charm login"

# The resources are in /home/ubuntu/workspace inside the container.
CONTAINER_PATH=/home/ubuntu/workspace

E2E_RESOURCES=e2e_${ARCH}=${CONTAINER_PATH}/${E2E_RESOURCE}
charm_push_release ${CHARMS_BUILDS}/kubernetes-e2e ${E2E} ${CHANNEL} "${E2E_RESOURCES}"
EASYRSA_RESOURCES=easyrsa=${CONTAINER_PATH}/${EASYRSA_RESOURCE}
charm_push_release ${CHARMS_BUILDS}/easyrsa ${EASYRSA} ${CHANNEL} "${EASYRSA_RESOURCES}"
# The etcd charm does not have a built resource at this time.
charm_push_release ${CHARMS_BUILDS}/etcd ${ETCD} ${CHANNEL}
FLANNEL_RESOURCES=flannel=${CONTAINER_PATH}/${FLANNEL_RESOURCE}
charm_push_release ${CHARMS_BUILDS}/flannel ${FLANNEL} ${CHANNEL} "${FLANNEL_RESOURCES}"
MASTER_RESOURCES=kubernetes=${CONTAINER_PATH}/${MASTER_RESOURCE}
charm_push_release ${CHARMS_BUILDS}/kubernetes-master ${MASTER} ${CHANNEL} "${MASTER_RESOURCES}"
WORKER_RESOURCES=kubernetes=${CONTAINER_PATH}/${WORKER_RESOURCE}
charm_push_release ${CHARMS_BUILDS}/kubernetes-worker ${WORKER} ${CHANNEL} "${WORKER_RESOURCES}"