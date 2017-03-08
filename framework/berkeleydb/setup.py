#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os

from framework.berkeleydb.download import BerkeleyDbDownload
from framework.bitcoin.setup import BDB_DIR


def berkeleydb_setup_dir(directory):
    bdb_dir = os.path.join(directory, BDB_DIR)
    if not os.path.exists(str(bdb_dir)):
        os.makedirs(str(bdb_dir))
    downloader = BerkeleyDbDownload(bdb_dir)
    downloader.download()
    downloader.verify()
    downloader.unpack()
    return bdb_dir
