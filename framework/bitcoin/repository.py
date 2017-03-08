#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os

from framework.bitcoin.clone import BitcoinClone, DEFAULT_UPSTREAM_URL
from framework.git.repository import GitRepository
from framework.berkeleydb.build import BerkeleyDbBuild
from framework.build.autogen import Autogen
from framework.build.configure import Configure


class BitcoinRepository(GitRepository):
    """
    A git repository that is specifically a bitcoin repository.
    """
    def __init__(self, directory, clone=False,
                 upstream_url=DEFAULT_UPSTREAM_URL, silent=False):
        self.directory = directory
        self.silent = silent
        if clone:
            BitcoinClone(self.directory, upstream_url=upstream_url,
                         silent=self.silent).clone()
        super().__init__(self.directory)

    def build_prepare(self, bdb_directory, autogen_log, configure_log):
        """
        Downloads and builds BerkeleyDb, runs ./autogen.sh and ./configure
        with the prefix set to the built BerkeleyDb.
        """
        bdb = BerkeleyDbBuild(bdb_directory, silent=self.silent)
        bdb.build()
        prefix = bdb.prefix()
        Autogen(self.directory, autogen_log).run()
        options = "LDFLAGS=-L%s/lib/ CPPFLAGS=-I%s/include/" % (prefix, prefix)
        Configure(self.directory, configure_log, options=options).run()
