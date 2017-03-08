#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import argparse

from framework.argparse.option import add_tmp_directory_option
from framework.argparse.option import add_jobs_option
from framework.bitcoin.clone import DEFAULT_UPSTREAM_URL
from framework.bitcoin.setup import bitcoin_setup_build_ready_repo
from framework.build.make import Make


def add_url_option(parser):
    u_help = "upstream url to clone from (default=%s)" % DEFAULT_UPSTREAM_URL
    parser.add_argument('-u', "--clone-url", type=str,
                        default=DEFAULT_UPSTREAM_URL, help=u_help)


def add_branch_option(parser):
    b_help = "branch to checkout before building (default=master)"
    parser.add_argument('-b', "--git-branch", type=str, default='master',
                        help=b_help)


def add_directory_argument(parser):
    d_help = "Directory to hold the repository clone."
    parser.add_argument('directory', type=str, help=d_help)


if __name__ == "__main__":
    description = ("Clones and builds a bitcoin repository with standard "
                   "settings. BerkeleyDB 4.8 is also downloaded to the "
                   "temporary directory and built as part of the process.")
    parser = argparse.ArgumentParser(description=description)
    add_tmp_directory_option(parser)
    add_jobs_option(parser)
    add_url_option(parser)
    add_branch_option(parser)
    add_directory_argument(parser)
    settings = parser.parse_args()
    repository = (
        bitcoin_setup_build_ready_repo(settings.tmp_directory,
                                       clone_directory=settings.directory,
                                       upstream_url=settings.clone_url,
                                       branch=settings.git_branch))
    make_log = os.path.join(settings.tmp_directory, 'make.log')
    maker = Make(str(repository), make_log, jobs=settings.jobs)
    maker.run()
