#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import argparse

from framework.git.repository import GitPath
from framework.git.repository import GitRepository


###############################################################################
# actions
###############################################################################

class GitRepositoryAction(argparse.Action):
    """
    Checks that the string points to a valid git repository.
    """
    def __call__(self, parser, namespace, values, option_string=None):
        if not isinstance(values, str):
            sys.exit("*** %s is not a string" % values)
        repository = GitRepository(values)
        repository.assert_has_makefile()
        namespace.repository = repository
        namespace.target_fnmatches = [os.path.join(str(repository), '*')]


class GitTrackedTargetsAction(argparse.Action):
    """
    Validate that 'values' is a list of strings that all represent files or
    directories under a git repository path.
    """
    def _check_values(self, values):
        if not isinstance(values, list):
            sys.exit("*** %s is not a list" % values)
        types = [type(value) for value in values]
        if len(set(types)) != 1:
            sys.exit("*** %s has multiple object types" % values)
        if not isinstance(values[0], str):
            sys.exit("*** %s does not contain strings" % values)

    def _get_targets(self, values):
        targets = [GitPath(value) for value in values]
        for target in targets:
            target.assert_exists()
            target.assert_mode(os.R_OK)
        return targets

    def _get_common_repository(self, targets):
        repositories = [str(target.repository_base()) for target in targets]
        if len(set(repositories)) > 1:
            sys.exit("*** targets from multiple repositories %s" %
                     set(repositories))
        for target in targets:
            target.assert_under_directory(repositories[0])
        return GitRepository(repositories[0])

    def __call__(self, parser, namespace, values, option_string=None):
        self._check_values(values)
        targets = self._get_targets(values)
        namespace.repository = self._get_common_repository(targets)

        target_files = [os.path.join(str(namespace.repository), str(t)) for t
                        in targets if t.is_file()]
        target_directories = [os.path.join(str(namespace.repository), str(t))
                              for t in targets if t.is_directory()]
        namespace.target_fnmatches = (target_files +
                                      [os.path.join(d, '*') for d in
                                       target_directories])


###############################################################################
# add args
###############################################################################


def add_git_repository_parameter(parser):
    repo_help = ("A source code repository for which the operation is to be "
                 "performed upon.")
    parser.add_argument("repository", type=str, action=GitRepositoryAction,
                        nargs='?', default='.', help=repo_help)


def add_git_tracked_targets_parameter(parser):
    t_help = ("A list of files and/or directories that select the subset of "
              "files for this action. If a directory is given as a target, "
              "all files contained in it and its subdirectories are "
              "recursively selected. All targets must be tracked in the same "
              "git repository clone. (default=The current directory)")
    parser.add_argument("target", type=str, action=GitTrackedTargetsAction,
                        nargs='*', default=['.'], help=t_help)
