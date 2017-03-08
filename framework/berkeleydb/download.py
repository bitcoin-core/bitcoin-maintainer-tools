#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import subprocess
import urllib.request as Download

from framework.file.hash import FileHash

TARBALL = "db-4.8.30.NC.tar.gz"
DOWNLOAD_URL = "http://download.oracle.com/berkeley-db/" + TARBALL
CHECKSUM = "12edc0df75bf9abd7f82f821795bcee50f42cb2e5f76a6a281b85732798364ef"
UNTAR = "tar -xzf " + TARBALL


class BerkeleyDbDownload(object):
    """
    Downloads, verifies and unpacks the BerkeleyDB tarball from Oracle.
    """
    def __init__(self, directory, silent=False):
        self.directory = directory
        self.silent = silent
        self.tarball = os.path.join(self.directory, TARBALL)

    def download(self):
        if os.path.exists(self.tarball):
            # To avoid abusing Oracle's server, don't re-download if we
            # already have the tarball.
            if not self.silent:
                print("Found %s" % (self.tarball))
            return
        if not self.silent:
            print("Downloading %s..." % DOWNLOAD_URL)
        Download.urlretrieve(DOWNLOAD_URL, self.tarball)
        if not self.silent:
            print("Done.")

    def verify(self):
        if not str(FileHash(self.tarball)) == CHECKSUM:
            sys.exit("*** %s does not have expected hash %s" % (self.tarball,
                                                                CHECKSUM))

    def unpack(self):
        original_dir = os.getcwd()
        os.chdir(self.directory)
        rc = subprocess.call(UNTAR.split(" "))
        os.chdir(original_dir)
        if rc != 0:
            sys.exit("*** could not unpack %s" % self.tarball)
