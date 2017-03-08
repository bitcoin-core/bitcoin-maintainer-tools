#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import os
import sys
import subprocess

from framework.git.repository import GitRepository
from framework.path.path import Path


class GitClone(object):
    def __init__(self, upstream_url, silent=False):
        self.upstream_url = upstream_url
        self.silent = silent

    def clone(self, repository_base):
        cmd = "git clone %s %s" % (self.upstream_url, repository_base)
        outfile = open(os.devnull, 'w') if self.silent else None
        rc = subprocess.call(cmd.split(" "), stdout=outfile, stderr=outfile)
        if rc != 0:
            sys.exit("*** clone command '%s' failed" % cmd)
        return GitRepository(repository_base)

    def _fetch(self, repository_base):
        r = GitRepository(repository_base)
        r.fetch()
        return r

    def clone_or_fetch(self, repository_base):
        """
        Clones a fresh repository at the given base unless it exists already.
        If it exists already, it will fetch the latest upstream state (which is
        less abusive of the github servers than a full clone). The result will
        be returned as a GitRepository instance.
        """
        p = Path(repository_base)
        return (self._fetch(repository_base) if p.exists() else
                self.clone(repository_base))
