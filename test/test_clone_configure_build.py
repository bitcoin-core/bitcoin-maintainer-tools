#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import argparse
import shutil

from framework.argparse.option import add_tmp_directory_option
from framework.test.exec import exec_cmd_no_error
from framework.test.exec import exec_cmd_error
from framework.test.exec import exec_cmd_json_no_error
from framework.test.exec import exec_cmd_json_error
from framework.test.exec import exec_modify_fixes_check
from framework.test.exec import exec_modify_doesnt_fix_check
from framework.bitcoin.setup import bitcoin_setup_build_ready_repo
from framework.clang.setup import clang_setup_bin_dir
from framework.clang.setup import clang_setup_test_style_file
from framework.test.cmd import ScriptTestCmd

###############################################################################
# test
###############################################################################


def tests(settings):
    bitcoin_clone_dir = os.path.join(settings.tmp_directory, "bitcoin-clone")
    elements_clone_dir = os.path.join(settings.tmp_directory, "elements-clone")
    cmd = 'bin/clone_configure_build.py -h'
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/clone_configure_build.py -j3 -b v0.14.0 %s' % bitcoin_clone_dir
    print(exec_cmd_no_error(cmd))
    shutil.rmtree(bitcoin_clone_dir)
    cmd = ("bin/clone_configure_build.py -u "
           "https://github.com/ElementsProject/elements -b elements-0.13.1 %s"
           % elements_clone_dir)
    print(exec_cmd_no_error(cmd))
    shutil.rmtree(elements_clone_dir)


class TestCloneConfigureBuildCmd(ScriptTestCmd):
    def __init__(self, settings):
        settings.repository = "No repository for this test"
        super().__init__(settings)
        self.title = __file__

    def _exec(self):
        return super()._exec(tests)


###############################################################################
# UI
###############################################################################

if __name__ == "__main__":
    description = ("Tests clone_configure_build.py through its range of "
                   "options.")
    parser = argparse.ArgumentParser(description=description)
    add_tmp_directory_option(parser)
    settings = parser.parse_args()
    TestCloneConfigureBuildCmd(settings).run()
