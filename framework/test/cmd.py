#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import sys
import time
import json
import subprocess
import argparse

from framework.print.buffer import PrintBuffer
from framework.cmd.repository import RepositoryCmd


class ScriptTestCmd(RepositoryCmd):
    """
    Superclass for structuring a command that invokes a script in order to test
    it.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.title = "script test cmd superclass"

    def _exec(self, tests):
        start_time = time.time()
        tests(self.settings)
        return {'elapsed_time': time.time() - start_time}

    def _output(self, results):
        b = PrintBuffer()
        b.separator()
        b.add_green("%s passed!\n" % self.title)
        b.add("Elapsed time: %.2fs\n" % results['elapsed_time'])
        b.separator()
        return str(b)
