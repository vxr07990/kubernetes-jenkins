#!/usr/bin/python3

import os
from snapstore import Microk8sSnap
from configbag import tracks


dry_run = os.environ.get('DRY_RUN', 'yes')


if __name__ == '__main__':
    print("Check edge for a new release cross-distro test and release to bet and candidate")
    for track in tracks:
        print("Looking at track {}".format(track))
        edge_snap = Microk8sSnap(track, 'edge')
        if not edge_snap.released:
            print("Nothing released on {} edge.".format(track))
            break

        beta_snap = Microk8sSnap(track, 'beta')
        if beta_snap.released:
            # We already have a snap on beta. Let's see if we have to push a new release.
            if beta_snap.version == edge_snap.version:
                # Beta and edge are the same version. Nothing to release on this track.
                continue

            edge_snap.test_cross_distro(channel_to_upgrade='beta')

        # The following will raise exceptions in case of a failure
        edge_snap.release_to('beta', dry_run=dry_run)
        edge_snap.release_to('candidate', dry_run=dry_run)
