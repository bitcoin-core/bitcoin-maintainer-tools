#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os

from framework.bitcoin.clone import DEFAULT_UPSTREAM_URL
from framework.bitcoin.repository import BitcoinRepository

DEFAULT_CLONE_DIR = "bitcoin"
BDB_DIR = "berkeley-db"
AUTOGEN_LOG = "autogen.log"
CONFIGURE_LOG = "configure.log"
TEST_BRANCH = "v0.14.0"


def bitcoin_setup_repo(tmp_directory, clone_directory=None,
                       upstream_url=DEFAULT_UPSTREAM_URL,
                       branch=TEST_BRANCH, silent=False):
    if not clone_directory:
        clone_directory = os.path.join(tmp_directory, DEFAULT_CLONE_DIR)
    repository = BitcoinRepository(clone_directory, clone=True,
                                   upstream_url=upstream_url, silent=silent)
    repository.reset_hard(branch)
    return repository


def bitcoin_setup_build_ready_repo(tmp_directory, clone_directory=None,
                                   upstream_url=DEFAULT_UPSTREAM_URL,
                                   branch=TEST_BRANCH, silent=False):
    repository = bitcoin_setup_repo(tmp_directory,
                                    clone_directory=clone_directory,
                                    upstream_url=upstream_url, branch=branch,
                                    silent=silent)
    bdb_dir = os.path.join(tmp_directory, BDB_DIR)
    autogen_log = os.path.join(tmp_directory, AUTOGEN_LOG)
    configure_log = os.path.join(tmp_directory, CONFIGURE_LOG)
    repository.build_prepare(bdb_dir, autogen_log, configure_log)
    return repository
