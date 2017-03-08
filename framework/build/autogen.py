#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

from framework.build.step import BuildStep


class Autogen(BuildStep):
    """
    Executes './autogen' on the source directory.
    """
    def _cmd(self):
        return "./autogen.sh"
