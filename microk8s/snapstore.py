import os
from dateutil import parser
from subprocess import check_output, check_call


class Microk8sSnap:

    def __init__(self, track, channel):
        cmd = "snapcraft list-revisions microk8s --arch amd64".split()
        revisions_list = check_output(cmd).decode("utf-8").split("\n")
        if track == "latest":
            channel_patern = " {}*".format(channel)
        else:
            channel_patern = " {}/{}*".format(track, channel)

        revision_info_str = None
        for revision in revisions_list:
            if channel_patern in revision:
                revision_info_str = revision
        if revision_info_str:
            # revision_info_str looks like this:
            # "180     2018-09-12T15:51:33Z  amd64   v1.11.3    1.11/edge*"
            revision_info = revision_info_str.split()

            self.track = track
            self.channel = channel
            self.under_testing_channel = channel
            if "edge" in self.under_testing_channel:
                self.under_testing_channel = "{}/under-testing".format(self.under_testing_channel)
            self.revision = revision_info[0]
            self.version = revision_info[3]
            self.release_date = parser.parse(revision_info[1])
            self.released = True
        else:
            self.released = False

    def release_to(self, channel, dry_run="no"):
        '''
        Release the Snap to the input channel
        Args:
            channel: The channel to release to

        '''
        target = channel if self.target == "latest" else "{}/{}".format(self.track, channel)
        cmd = "snapcraft release microk8s {} {}".format(self.revision, target)
        if dry_run == "no":
            check_call(cmd.split())
        else:
            print("DRY RUN - calling: {}".format(cmd))

    def test_cross_distro(self,  channel_to_upgrade='stable',
                          distributions = ["ubuntu:16.04", "ubuntu:18.04"]):
        '''
        Test the channel this snap came from and make sure we can upgrade the
        channel_to_upgrade. Tests are run on the distributions distros.

        Args:
            channel_to_upgrade: whta channel to try to upgrade
            distributions: where to run tests on

        '''
        cmd = "rm -rf microk8s".split()
        check_call(cmd)
        cmd = "git clone http://www.github.com/ubuntu/microk8s".split()
        check_call(cmd)
        os.chdir("microk8s")
        if "under-testing" in self.under_testing_channel:
            self.release_to(self.under_testing_channel)
        for distro in distributions:
            cmd = "tests/test-distro.sh {} {} {}".format(distro, channel_to_upgrade, self.under_testing_channel).split()
            check_call(cmd)
