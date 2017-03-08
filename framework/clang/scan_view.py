#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from framework.print.buffer import PrintBuffer


class ScanView(object):
    """
    Encapsulates clang's 'scan-view' utility which displays 'scan-build'
    results nicely in a broswer.
    """
    def __init__(self, binary):
        self.binary_path = binary['path']
        self.binary_version = binary['version']

    def launch_instructions(self, result_dir):
        b = PrintBuffer()
        b.separator()
        b.add("Full details can be seen in a browser by running:\n")
        b.add("    $ %s %s\n" % (self.binary_path, result_dir))
        b.separator()
        return str(b)
