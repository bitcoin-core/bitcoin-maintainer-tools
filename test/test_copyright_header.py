#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import argparse

from framework.argparse.option import add_tmp_directory_option
from framework.bitcoin.setup import bitcoin_setup_repo
from framework.test.exec import exec_cmd_no_error
from framework.test.exec import exec_cmd_error
from framework.test.exec import exec_cmd_json_no_error
from framework.test.exec import exec_cmd_json_error
from framework.test.exec import exec_modify_fixes_check
from framework.test.exec import exec_modify_doesnt_fix_check
from framework.test.cmd import ScriptTestCmd

###############################################################################
# test
###############################################################################


def test_help(repository):
    cmd = 'bin/copyright_header.py -h'
    print(exec_cmd_no_error(cmd))


def test_report(repository):
    cmd = 'bin/copyright_header.py report -h'
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/copyright_header.py report %s' % repository
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/copyright_header.py report -j3 %s' % repository
    print(exec_cmd_no_error(cmd))
    cmd = ('bin/copyright_header.py report -j3 %s/src/init.cpp %s/src/qt/' %
           (repository, repository))
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/copyright_header.py report --json %s' % repository
    print(exec_cmd_json_no_error(cmd))
    cmd = ('bin/copyright_header.py report --json %s/src/init.cpp %s/src/qt/' %
           (repository, repository))
    print(exec_cmd_json_no_error(cmd))
    # no specified targets runs it on the path/repository it is invoked from:
    cmd = 'bin/copyright_header.py report'
    original = os.getcwd()
    os.chdir(str(repository))
    print(exec_cmd_no_error(cmd))
    os.chdir(original)


def test_check(repository):
    cmd = 'bin/copyright_header.py check -h'
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/copyright_header.py check -j3 %s' % repository
    e, out = exec_cmd_error(cmd)
    print("%d\n%s" % (e, out))
    cmd = 'bin/copyright_header.py check --json %s' % repository
    e, out = exec_cmd_json_error(cmd)
    print("%d\n%s" % (e, out))
    cmd = 'bin/copyright_header.py check %s/src/init.cpp' % repository
    print(exec_cmd_no_error(cmd))


def test_update(repository):
    cmd = 'bin/copyright_header.py update -h'
    print(exec_cmd_no_error(cmd))
    check_cmd = "bin/copyright_header.py check %s" % repository
    modify_cmd = "bin/copyright_header.py update %s" % repository
    exec_modify_doesnt_fix_check(repository, check_cmd, modify_cmd)
    repository.reset_hard_head()


def test_insert(repository):
    cmd = 'bin/copyright_header.py insert -h'
    print(exec_cmd_no_error(cmd))
    check_cmd = "bin/copyright_header.py check %s" % repository
    modify_cmd = "bin/copyright_header.py insert %s/src/" % repository
    exec_modify_doesnt_fix_check(repository, check_cmd, modify_cmd)
    repository.reset_hard_head()
    # results in no-op if already has a valid header
    cmd = "bin/copyright_header.py insert %s/src/init.cpp" % repository
    print(exec_cmd_no_error(cmd))
    repository.assert_not_dirty()


def tests(settings):
    test_help(settings.repository)
    test_report(settings.repository)
    test_check(settings.repository)
    test_update(settings.repository)
    test_insert(settings.repository)


class TestCopyrightHeaderCmd(ScriptTestCmd):
    def __init__(self, settings):
        super().__init__(settings)
        self.title = __file__

    def _exec(self):
        return super()._exec(tests)

###############################################################################
# UI
###############################################################################

if __name__ == "__main__":
    description = ("Tests copyright_header.py through its range of "
                   "subcommands and options.")
    parser = argparse.ArgumentParser(description=description)
    add_tmp_directory_option(parser)
    settings = parser.parse_args()
    settings.repository = bitcoin_setup_repo(settings.tmp_directory,
                                             branch="v0.14.0")
    TestCopyrightHeaderCmd(settings).run()
