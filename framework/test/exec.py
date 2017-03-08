#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import json
import subprocess

from framework.git.path import GitPath


###############################################################################
# helpers
###############################################################################

def prep(cmd):
    """
    Splits the command string into the list and finds the absolute path of
    the script being invoked.
    """
    l = cmd.split(" ")
    gp = GitPath(os.path.abspath(os.path.realpath(__file__)))
    l[0] = os.path.join(str(gp.repository_base()), l[0])
    return l


###############################################################################
# test actions that run a command
###############################################################################


def exec_cmd_no_error(cmd):
    return subprocess.check_output(prep(cmd)).decode('utf-8')


def exec_cmd_error(cmd):
    try:
        subprocess.check_output(prep(cmd))
    except subprocess.CalledProcessError as e:
        assert e.returncode == 1
        output = e.output.decode('utf-8')
        assert "Traceback" not in output
        return e.returncode, output
    sys.exit("*** command unexpectedly succeeded")


def exec_cmd_json_no_error(cmd):
    out = subprocess.check_output(prep(cmd)).decode('utf-8')
    return json.dumps(json.loads(out))


def exec_cmd_json_error(cmd):
    try:
        subprocess.check_output(prep(cmd))
    except subprocess.CalledProcessError as e:
        assert e.returncode == 1
        output = e.output.decode('utf-8')
        assert "Traceback" not in output
        return e.returncode, json.dumps(json.loads(output))
    sys.exit("*** command unexpectedly succeeded")


###############################################################################
# test actions that that modify a repo
###############################################################################


def exec_modify_fixes_check(repo, check_cmd, modify_cmd):
    _ = exec_cmd_error(check_cmd)
    _ = subprocess.check_output(prep(modify_cmd)).decode('utf-8')
    repo.assert_dirty()
    _ = exec_cmd_no_error(check_cmd)


def exec_modify_doesnt_fix_check(repo, check_cmd, modify_cmd):
    _ = exec_cmd_error(check_cmd)
    _ = subprocess.check_output(prep(modify_cmd)).decode('utf-8')
    repo.assert_dirty()
    _ = exec_cmd_error(check_cmd)
