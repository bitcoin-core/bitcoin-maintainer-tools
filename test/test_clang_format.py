#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import argparse

from framework.argparse.option import add_tmp_directory_option
from framework.test.exec import exec_cmd_no_error
from framework.test.exec import exec_cmd_error
from framework.test.exec import exec_cmd_json_no_error
from framework.test.exec import exec_cmd_json_error
from framework.test.exec import exec_modify_fixes_check
from framework.test.exec import exec_modify_doesnt_fix_check
from framework.bitcoin.setup import bitcoin_setup_repo
from framework.clang.setup import clang_setup_bin_dir
from framework.clang.setup import clang_setup_test_style_file
from framework.test.cmd import ScriptTestCmd


###############################################################################
# test
###############################################################################


def test_help(repository):
    cmd = 'bin/clang_format.py -h'
    print(exec_cmd_no_error(cmd))


def test_report(repository, test_bin_dir, test_style_file):
    cmd = 'bin/clang_format.py report -h'
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/clang_format.py report %s' % repository
    print(exec_cmd_no_error(cmd))
    cmd = ('bin/clang_format.py report -j3 %s/src/init.cpp %s/src/qt/' %
           (repository, repository))
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/clang_format.py report --json %s' % repository
    print(exec_cmd_json_no_error(cmd))
    cmd = 'bin/clang_format.py report -b %s %s' % (test_bin_dir, repository)
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/clang_format.py report -s %s %s' % (test_style_file, repository)
    print(exec_cmd_no_error(cmd))
    # no specified targets runs it on the path/repository it is invoked from:
    cmd = 'bin/clang_format.py report'
    original = os.getcwd()
    os.chdir(str(repository))
    print(exec_cmd_no_error(cmd))
    os.chdir(original)


def test_check(repository, test_bin_dir, test_style_file):
    cmd = 'bin/clang_format.py check -h'
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/clang_format.py check -j3 --force %s' % repository
    print("%d\n%s" % exec_cmd_error(cmd))
    cmd = 'bin/clang_format.py check --json --force %s' % repository
    e, out = exec_cmd_json_error(cmd)
    print("%d\n%s" % (e, out))
    cmd = ('bin/clang_format.py check --force %s/src/bench/bench_bitcoin.cpp' %
           repository)
    print(exec_cmd_no_error(cmd))
    cmd = 'bin/clang_format.py check --force -b %s %s' % (test_bin_dir,
                                                          repository)
    print("%d\n%s" % exec_cmd_error(cmd))
    cmd = 'bin/clang_format.py check -s %s %s' % (test_style_file, repository)
    print("%d\n%s" % exec_cmd_error(cmd))


def test_format(repository):
    cmd = 'bin/clang_format.py format -h'
    print(exec_cmd_no_error(cmd))
    check_cmd = "bin/clang_format.py check --force %s" % repository
    modify_cmd = "bin/clang_format.py format --force %s" % repository
    # Two rounds of 'format' are needed to adjust the style of
    # src/validation.cpp to match, so this fails.
    exec_modify_doesnt_fix_check(repository, check_cmd, modify_cmd)
    repository.reset_hard_head()
    check_cmd = ("bin/clang_format.py check --force %s/src/init.cpp" %
                 repository)
    modify_cmd = ("bin/clang_format.py format --force %s/src/init.cpp" %
                  repository)
    exec_modify_fixes_check(repository, check_cmd, modify_cmd)
    repository.reset_hard_head()


def tests(settings):
    test_help(settings.repository)
    test_report(settings.repository, settings.test_bin_dir,
                settings.test_style_file)
    test_check(settings.repository, settings.test_bin_dir,
               settings.test_style_file)
    test_format(settings.repository)


class TestClangFormatCmd(ScriptTestCmd):
    def __init__(self, settings):
        super().__init__(settings)
        self.title = __file__

    def _exec(self):
        return super()._exec(tests)

###############################################################################
# UI
###############################################################################

if __name__ == "__main__":
    description = ("Tests clang_format.py through its range of "
                   "subcommands and options.")
    parser = argparse.ArgumentParser(description=description)
    add_tmp_directory_option(parser)
    settings = parser.parse_args()
    settings.repository = bitcoin_setup_repo(settings.tmp_directory,
                                             branch="v0.14.0")
    settings.test_bin_dir = clang_setup_bin_dir(settings.tmp_directory)
    settings.test_style_file = (
        clang_setup_test_style_file(settings.tmp_directory))
    TestClangFormatCmd(settings).run()
