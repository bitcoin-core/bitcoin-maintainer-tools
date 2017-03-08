#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import argparse

from framework.argparse.option import add_tmp_directory_option
from framework.cmd.repository import RepositoryCmds
from test_basic_style import TestBasicStyleCmd
from test_copyright_header import TestCopyrightHeaderCmd
from test_clang_format import TestClangFormatCmd
from test_clang_static_analysis import TestClangStaticAnalysisCmd
from test_reports import TestReportsCmd
from test_checks import TestChecksCmd
from test_clone_configure_build import TestCloneConfigureBuildCmd
from framework.bitcoin.setup import bitcoin_setup_build_ready_repo
from framework.clang.setup import clang_setup_bin_dir
from framework.clang.setup import clang_setup_test_style_file


class TestAll(RepositoryCmds):
    """
    Invokes several underlying RepositoryCmd check command instances and
    aggregates the results.
    """
    def __init__(self, settings):
        repository_cmds = {
            'basic_style':           TestBasicStyleCmd(settings),
            'copyright_header':      TestCopyrightHeaderCmd(settings),
            'clang_format':          TestClangFormatCmd(settings),
            'clang_static_analysis': TestClangStaticAnalysisCmd(settings),
            'reports':               TestReportsCmd(settings),
            'checks':                TestChecksCmd(settings),
            'clone_configure_build': TestCloneConfigureBuildCmd(settings),
        }
        super().__init__(settings, repository_cmds)

    def _output(self, results):
        reports = [(self.repository_cmds[l].title + ":\n" +
                    self.repository_cmds[l]._output(r)) for l, r in
                   sorted(results.items())]
        return '\n'.join(reports)


if __name__ == "__main__":
    description = ("Runs all test scripts in serial to make sure they all "
                   "pass.")
    parser = argparse.ArgumentParser(description=description)
    add_tmp_directory_option(parser)
    settings = parser.parse_args()
    settings.repository = (
        bitcoin_setup_build_ready_repo(settings.tmp_directory,
                                       branch="v0.14.0"))
    settings.test_bin_dir = clang_setup_bin_dir(settings.tmp_directory)
    settings.test_style_file = (
        clang_setup_test_style_file(settings.tmp_directory))
    TestAll(settings).run()
