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
    cmd = 'bin/basic_style.py -h'
    print(exec_cmd_no_error(cmd))


def test_report(repository):
    cmd = 'bin/basic_style.py report -h'
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/basic_style.py report %s' % repository
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/basic_style.py report -j3 %s' % repository
    print(exec_cmd_no_error(cmd))
    cmd = ('bin/basic_style.py report -j3 %s/src/init.cpp %s/src/qt/' %
           (repository, repository))
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/basic_style.py report --json %s' % repository
    print(exec_cmd_json_no_error(cmd))
    cmd = ('bin/basic_style.py report --json %s/src/init.cpp %s/src/qt/' %
           (repository, repository))
    print(exec_cmd_json_no_error(cmd))
    # no specified targets runs it on the path/repository it is invoked from:
    cmd = 'bin/basic_style.py report'
    original = os.getcwd()
    os.chdir(str(repository))
    print(exec_cmd_no_error(cmd))
    os.chdir(original)


def test_check(repository):
    cmd = 'bin/basic_style.py check -h'
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/basic_style.py check -j3 %s' % repository
    e, out = exec_cmd_error(cmd)
    print("%d\n%s" % (e, out))
    cmd = 'bin/basic_style.py check --json %s' % repository
    e, out = exec_cmd_json_error(cmd)
    print("%d\n%s" % (e, out))
    cmd = 'bin/basic_style.py check %s/src/init.cpp' % repository
    print(exec_cmd_no_error(cmd))


def test_fix(repository):
    cmd = 'bin/basic_style.py fix -h'
    print(exec_cmd_no_error(cmd))
    check_cmd = "bin/basic_style.py check %s" % repository
    modify_cmd = "bin/basic_style.py fix %s" % repository
    exec_modify_fixes_check(repository, check_cmd, modify_cmd)
    repository.reset_hard_head()


def tests(settings):
    test_help(settings.repository)
    test_report(settings.repository)
    test_check(settings.repository)
    test_fix(settings.repository)


class TestBasicStyleCmd(ScriptTestCmd):
    def __init__(self, settings):
        super().__init__(settings)
        self.title = __file__

    def _exec(self):
        return super()._exec(tests)


###############################################################################
# UI
###############################################################################

if __name__ == "__main__":
    description = ("Tests basic_style.py through its range of subcommands and "
                   "options.")
    parser = argparse.ArgumentParser(description=description)
    add_tmp_directory_option(parser)
    settings = parser.parse_args()
    settings.repository = bitcoin_setup_repo(settings.tmp_directory,
                                             branch="v0.14.0")
    TestBasicStyleCmd(settings).run()
