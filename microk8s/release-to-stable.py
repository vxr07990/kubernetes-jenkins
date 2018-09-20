#!/usr/bin/python3

import os
from datetime import datetime
from snapstore import Microk8sSnap
from configbag import tracks


dry_run = os.environ.get('DRY_RUN', 'yes')
always_release = os.environ.get('ALWAYS_RELEASE', 'no')


if __name__ == '__main__':
    print("Check candidate maturity and release microk8s to stable.")
    print("Dry run is set to '{}'.".format(dry_run))
    for track in tracks:
        print("Looking at track {}".format(track))
        candidate_snap = Microk8sSnap(track, 'candidate')
        if not candidate_snap.released:
            # Nothing to release
            print("Nothing on candidate. Nothing to release.")
            break

        if (datetime.now() - candidate_snap.date).days < 8 and always_release == 'no':
            # Candidate not mature enough
            print("Not releasing because candidate is {} days old and 'always_release' is {}".format(
                (datetime.now() - candidate_snap.date).days, always_release
            ))
            break

        stable_snap = Microk8sSnap(track, 'stable')
        if stable_snap.released:
            # We already have a snap released on stable. Lets run some tests.
            if candidate_snap.version == stable_snap.version and always_release == 'no':
                # Candidate and stable are the same version. Nothing to release.
                print("Beta and edge have the same version {}. We will not release.".format(stable_snap.version))
                break

            print("Candidate is at {}, stable at {}, and 'always_release' is {}.".format(
                candidate_snap.version, stable_snap.version, always_release
            ))
            candidate_snap.test_cross_distro(channel_to_upgrade='stable')
        else:
            print("Stable channel is empty. Releasing without any testing.")

        # The following will raise an exception if it fails
        candidate_snap.release_to('stable', dry_run=dry_run)
