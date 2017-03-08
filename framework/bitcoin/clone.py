#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os

from framework.git.clone import GitClone

DEFAULT_UPSTREAM_URL = "https://github.com/bitcoin/bitcoin/"


class BitcoinClone(object):
    """
    Clones a bitcoin repository to a directory. If the directory already
    exists, just fetch changes from upstream to avoid re-downloading.
    """
    def __init__(self, directory, upstream_url=DEFAULT_UPSTREAM_URL,
                 silent=False):
        self.directory = directory
        self.upstream_url = upstream_url
        self.cloner = GitClone(self.upstream_url, silent=silent)

    def clone(self):
        self.cloner.clone_or_fetch(self.directory)
