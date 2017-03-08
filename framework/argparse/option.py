#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import tempfile
import os

from framework.argparse.action import TmpDirectoryAction


def add_jobs_option(parser):
    j_help = "parallel jobs (default=4)"
    parser.add_argument("-j", "--jobs", type=int, default=4, help=j_help)


def add_json_option(parser):
    j_help = "print output in json format (default=False)"
    parser.add_argument("--json", action='store_true', help=j_help)


DEFAULT_TMP_DIR = os.path.join(tempfile.gettempdir(),
                               'bitcoin-maintainer-tools/')


def add_tmp_directory_option(parser):
    r_help = ("path for the maintainer tools to write temporary files."
              "(default=%s)" % DEFAULT_TMP_DIR)
    parser.add_argument("-t", "--tmp-directory", default=DEFAULT_TMP_DIR,
                        type=str, action=TmpDirectoryAction, help=r_help)
