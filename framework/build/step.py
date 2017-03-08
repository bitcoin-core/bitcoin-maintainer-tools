#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import subprocess

from framework.path.path import Path


class BuildStep(object):
    """
    Superclass for running build operations on a git repository. The output
    is routed to a specified file.
    """
    def __init__(self, invocation_dir, output_file):
        path = Path(output_file)
        containing_directory = Path(path.containing_directory())
        if not os.path.exists(str(containing_directory)):
            os.makedirs(str(containing_directory))
        containing_directory.assert_exists()
        containing_directory.assert_mode(os.R_OK | os.W_OK)
        self.invocation_dir = invocation_dir
        self.output_file = str(path)

    def __str__(self):
        return self._cmd()

    def _cmd(self):
        sys.exit("*** subclass must override _cmd() method.")

    def run(self, silent=False):
        if not silent:
            print("Running command:     %s" % str(self))
            print("stderr/stdout to:    %s" % self.output_file)
            print("This might take a few minutes...")
        cmd = self._cmd()
        original_dir = os.getcwd()
        os.chdir(self.invocation_dir)
        f = open(os.path.abspath(self.output_file), 'w')
        if subprocess.call(cmd.split(' '), stdout=f, stderr=f) != 0:
            sys.exit("*** '%s' returned a non-zero status. log in %s" %
                     (cmd, self.output_file))
        f.close()
        os.chdir(original_dir)
        if not silent:
            print("Done.")
