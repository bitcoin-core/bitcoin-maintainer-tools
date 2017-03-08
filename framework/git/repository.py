#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import subprocess
import argparse

from framework.path.path import Path
from framework.repository.info import RepositoryInfo
from framework.git.path import GitPath


LS_TRACKED = "git ls-files"
CHECK_UNTRACKED_UNIGNORED = "git ls-files --exclude-standard --others"
CHECK_CHANGES = "git diff-index --quiet HEAD"
RESET_HARD = "git reset --hard %s"
FETCH = "git fetch"


class GitRepository(object):
    """
    Represents queries information, and performs actions on a git repository
    clone.
    """
    def __init__(self, repository_base):
        self.repository_base = str(Path(repository_base))
        git_path = GitPath(repository_base)
        git_path.assert_exists()
        git_path.assert_mode(os.R_OK)
        git_path.assert_in_git_repository()
        if str(self.repository_base) != str(git_path.repository_base()):
            sys.exit("*** %s is not the base of its repository" %
                     self.repository_base)
        self.repo_info = RepositoryInfo(self.repository_base)

    def __str__(self):
        return self.repository_base

    def tracked_files(self):
        orig = os.getcwd()
        os.chdir(self.repository_base)
        out = subprocess.check_output(LS_TRACKED.split(" "))
        os.chdir(orig)
        return [os.path.join(self.repository_base, f) for f in
                out.decode("utf-8").split('\n') if f != '']

    def assert_has_makefile(self):
        makefile = Path(os.path.join(self.repository_base, "Makefile"))
        if not makefile.exists():
            sys.exit("*** no Makefile found in %s. You must ./autogen.sh "
                     "and/or ./configure first" % self.repository_base)

    def _has_changes(self):
        orig = os.getcwd()
        os.chdir(self.repository_base)
        rc = subprocess.call(CHECK_CHANGES.split(" "))
        os.chdir(orig)
        return rc != 0

    def _has_untracked_or_unignored(self):
        orig = os.getcwd()
        os.chdir(self.repository_base)
        out = subprocess.check_output(CHECK_UNTRACKED_UNIGNORED.split(" "))
        os.chdir(orig)
        return out.decode("utf-8") != ""

    def _is_dirty(self):
        return self._has_changes() or self._has_untracked_or_unignored()

    def assert_not_dirty(self):
        if self._is_dirty():
            sys.exit("*** repository has uncommitted changes.")

    def assert_dirty(self):
        if not self._is_dirty():
            sys.exit("*** repository has no uncommitted changes.")

    def reset_hard(self, branch):
        orig = os.getcwd()
        os.chdir(self.repository_base)
        cmd = RESET_HARD % branch
        out = subprocess.check_output(cmd.split(" "))
        os.chdir(orig)

    def reset_hard_head(self):
        self.reset_hard('HEAD')

    def fetch(self, silent=False):
        orig = os.getcwd()
        os.chdir(self.repository_base)
        outfile = open(os.devnull, 'w') if silent else None
        rc = subprocess.call(FETCH.split(" "), stdout=outfile, stderr=outfile)
        os.chdir(orig)
