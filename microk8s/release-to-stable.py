#!/usr/bin/python3

from datetime import datetime
from snapstore import Microk8sSnap
from configbag import tracks


if __name__ == '__main__':
    print("Check candidate maturity and release microk8s to stable")
    for track in tracks:
        print("Looking at track {}".format(track))
        candidate_snap = Microk8sSnap(track, 'candidate')
        if not candidate_snap.released:
            # Nothing to release
            break

        if (datetime.now() - candidate_snap.date).days < 8:
            # Candidate not mature enough
            break

        stable_snap = Microk8sSnap(track, 'stable')
        if stable_snap.released:
            # We already have a snap released on stable. Lets run some tests.
            if candidate_snap.version == stable_snap.version:
                # Candidate and stable are the same version. Nothing to release.
                break

            candidate_snap.test_cross_distro(channel_to_upgrade='stable')

        # The following will raise an exception if it fails
        candidate_snap.release_to('stable')
