#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import subprocess
import urllib.request as Download

from framework.file.hash import FileHash
from framework.clang.tarball import ClangTarball

UNTAR = "tar -xJf %s"


class ClangDownload(object):
    """
    Downloads, verifies and unpacks a clang 3.9.0 release tarball that
    matches the current platform from the LLVM project's servers.
    """
    def __init__(self, directory, silent=False):
        self.directory = directory
        self.silent = silent
        self.tarball = ClangTarball()
        if not self.tarball.supported:
            sys.exit("*** couldn't find a clang tarball for this platform.")
        self.download_path = os.path.join(self.directory,
                                          self.tarball.filename())

    def download(self):
        if os.path.exists(self.download_path):
            # To avoid abusing LLVM's server, don't re-download if we
            # already have the tarball in the right place.
            if not self.silent:
                print("Found %s" % (self.download_path))
            return
        if not self.silent:
            print("Downloading %s..." % self.tarball.url())
        Download.urlretrieve(self.tarball.url(), self.download_path)
        if not self.silent:
            print("Done.")

    def verify(self):
        if not str(FileHash(self.download_path)) == self.tarball.sha256():
            sys.exit("*** %s does not have expected hash %s" %
                     (self.download_path, self.tarball.sha256()))

    def unpack(self):
        original_dir = os.getcwd()
        os.chdir(self.directory)
        cmd = UNTAR % self.tarball.filename()
        rc = subprocess.call(cmd.split(" "))
        os.chdir(original_dir)
        if rc != 0:
            sys.exit("*** could not unpack %s" % self.download_path)
        return os.path.join(self.directory,
                            self.tarball.unpacked_directory())
