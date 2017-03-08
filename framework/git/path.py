#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import subprocess

from framework.path.path import Path


class GitPath(Path):
    """
    A Path that has some additional functions for awareness of the git
    repository that holds the path.
    """
    def _in_git_repository(self):
        cmd = 'git -C %s status' % self.directory()
        dn = open(os.devnull, 'w')
        return subprocess.call(cmd.split(' '), stderr=dn, stdout=dn) == 0

    def assert_in_git_repository(self):
        if not self._in_git_repository():
            sys.exit("*** %s is not inside a git repository" % self)

    def _is_repository_base(self):
        self.assert_is_directory()
        return Path(os.path.join(self.path, '.git/')).exists()

    def repository_base(self):
        directory = GitPath(self.directory())
        if directory._is_repository_base():
            return directory

        def recurse_repo_base_dir(git_path_arg):
            git_path_arg.assert_in_git_repository()
            d = GitPath(git_path_arg.containing_directory())
            if str(d) is '/':
                sys.exit("*** did not find underlying repo?")
            if d._is_repository_base():
                return d
            return recurse_repo_base_dir(d)

        return recurse_repo_base_dir(self)


GIT_LOG_CMD = "git log --follow --pretty=format:%%ai %s"


class GitFilePath(GitPath):
    """
    A GitPath for a particular file where additional specific information
    can be queried
    """
    def __init__(self, path):
        super().__init__(path)
        self.assert_is_file()
        self.assert_in_git_repository()
        self.repository = str(self.repository_base())

    def _git_log(self):
        cmd = (GIT_LOG_CMD % self).split(' ')
        orig = os.getcwd()
        os.chdir(self.repository)
        out = subprocess.check_output(cmd)
        os.chdir(orig)
        decoded = out.decode("utf-8")
        if decoded == '':
            return []
        return decoded.split('\n')

    def _git_change_years(self):
        git_log_lines = self._git_log()
        # timestamp is in ISO 8601 format. e.g. "2016-09-05 14:25:32 -0600"
        return [line.split(' ')[0].split('-')[0] for line in git_log_lines]

    def year_of_most_recent_change(self):
        return max(self._git_change_years())

    def change_year_range(self):
        years = self._git_change_years()
        return min(years), max(years)
