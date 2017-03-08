#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import argparse
import tempfile

from framework.path.path import Path


class TmpDirectoryAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        if not isinstance(values, str):
            sys.exit("*** %s is not a single string" % values)
        if not str(values).startswith(tempfile.gettempdir()):
            sys.exit("*** %s is not under %s" % (p, tempfile.gettempdir()))
        namespace.tmp_directory = str(Path(values))
