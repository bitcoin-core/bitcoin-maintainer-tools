#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from framework.build.step import BuildStep


class Configure(BuildStep):
    """
    Executes './configure' on the source directory.
    """
    def __init__(self, invocation_dir, output_file, script=None, options=None):
        super().__init__(invocation_dir, output_file)
        self.options = options
        self.script = script

    def _cmd(self):
        if not self.script:
            self.script = "./configure"
        if not self.options:
            self.options = ""
        return "%s %s" % (self.script, self.options)
