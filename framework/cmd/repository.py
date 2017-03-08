#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import sys
import json


class RepositoryCmd(object):
    """
    Superclass for a command or subcommand that is targeted at a git
    repository. 'silent=True' instructs to only print what is produced by the
    _output() function.
    """
    def __init__(self, settings, silent=False):
        assert hasattr(settings, 'repository')
        self.settings = settings
        self.repository = settings.repository
        self.silent = silent
        self.title = "RepositoryCmd superclass"

    def _exec(self):
        return {}

    def _output(self, results):
        return json.dumps(results)

    def _shell_exit(self, results):
        return 0

    def _print(self, output, exit):
        if output:
            print(output)
        if self.silent and type(exit) is str:
            sys.exit(1)
        sys.exit(exit)

    def run(self):
        results = self._exec()
        self._print(self._output(results), self._shell_exit(results))


class RepositoryCmds(RepositoryCmd):
    """
    Superclass for aggregating several RepositoryCmd instances together for
    a single invocation. The individual instances are passed in as a
    dictionary.
    """
    def __init__(self, settings, repository_cmds, silent=False):
        super().__init__(settings, silent=silent)
        assert type(repository_cmds) is dict
        for k, v in repository_cmds.items():
            assert type(k) is str
            assert issubclass(type(v), RepositoryCmd)
        self.repository_cmds = repository_cmds
        self.title = "RepositoryCmds superclass"

    def _exec(self):
        results = super()._exec()
        for key, cmd in sorted(self.repository_cmds.items()):
            if not self.silent:
                print("Computing analysis of '%s'..." % cmd.title)
            results[key] = cmd._exec()
            if not self.silent:
                print("Done.")
        if not self.silent:
            print("")
        return results

    def _shell_exit(self, results):
        exits = [r._shell_exit(results[l]) for l, r in
                 sorted(self.repository_cmds.items())]
        if all(e == 0 for e in exits):
            return 0
        non_zero_ints = [e for e in exits if type(e) is int and not e == 0]
        strings = [e for e in exits if type(e) is str]
        if len(strings) == 0:
            return max(non_zero_ints)
        return '\n'.join(strings)
