#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import shutil

from framework.build.make import Make
from framework.build.configure import Configure
from framework.berkeleydb.download import BerkeleyDbDownload

SRC_SUBDIR = "db-4.8.30.NC"
BUILD_TARGET_SUBDIR = "berkeleydb-install"
BUILD_FROM_SUBDIR = "build_unix"
CONFIGURE_SCRIPT = "../dist/configure"
CONFIGURE_OUTFILE = "bdb-configure.log"
CONFIGURE_OPTIONS = "--enable-cxx --disable-shared --with-pic --prefix=%s"
MAKE_OUTFILE = "bdb-make-install.log"


class BerkeleyDbBuild(object):
    """
    Produces a build and installed subdirectory for Bitoin's build process to
    use. The instructions from build-unix.md are automated and the prefix to
    use for Bitcoin's ./configure step is made available.
    """
    def __init__(self, directory, silent=False):
        self.directory = directory
        self.silent = silent
        self.build_target_dir = os.path.join(self.directory,
                                             BUILD_TARGET_SUBDIR)
        self.src_dir = os.path.join(self.directory, SRC_SUBDIR)
        self.build_from_dir = os.path.join(self.src_dir, BUILD_FROM_SUBDIR)
        self.configure_outfile = os.path.join(self.directory,
                                              CONFIGURE_OUTFILE)
        self.make_outfile = os.path.join(self.directory, MAKE_OUTFILE)
        self.downloader = BerkeleyDbDownload(self.directory,
                                             silent=self.silent)
        self._prep_directory()

    def _prep_directory(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)
        if os.path.exists(self.build_target_dir):
            shutil.rmtree(self.build_target_dir)
        os.makedirs(self.build_target_dir)
        if os.path.exists(self.src_dir):
            shutil.rmtree(self.src_dir)

    def prefix(self):
        return self.build_target_dir

    def build(self):
        self.downloader.download()
        self.downloader.verify()
        self.downloader.unpack()
        options = CONFIGURE_OPTIONS % self.prefix()
        self.configurator = Configure(self.build_from_dir,
                                      self.configure_outfile,
                                      script=CONFIGURE_SCRIPT, options=options)
        self.configurator.run(silent=self.silent)
        self.maker = Make(self.build_from_dir, self.make_outfile,
                          target="install")
        self.maker.run(silent=self.silent)
