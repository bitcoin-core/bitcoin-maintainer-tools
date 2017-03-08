#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import hashlib

BUF_SIZE = 65536


class FileHash(object):
    """
    Calculates and represents the SHA256 hash of the contents of the file
    """
    def __init__(self, file_path):
        self.sha256 = hashlib.sha256()
        f = open(file_path, 'rb')
        while True:
            data = f.read(BUF_SIZE)
            if not data:
                break
            self.sha256.update(data)

    def __str__(self):
        return self.sha256.hexdigest()
