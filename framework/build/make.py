#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from framework.build.step import BuildStep


class MakeClean(BuildStep):
    """
    Executes 'make clean' on the source directory.
    """
    def _cmd(self):
        return "make clean"


class Make(BuildStep):
    """
    Executes 'make' on the source directory.
    """
    def __init__(self, invocation_dir, output_file, jobs=1, target=None,
                 options=None):
        super().__init__(invocation_dir, output_file)
        self.jobs = jobs
        self.options = options
        self.target = target

    def _cmd(self):
        args = ""
        if self.jobs > 1:
            args = args + " -j%d" % self.jobs
        if self.options:
            args = args + " %s" % self.options
        if self.target:
            args = args + " %s" % self.target
        return "make%s" % args
