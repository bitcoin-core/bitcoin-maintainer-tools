#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import re
import os
import fnmatch


class FileFilter(object):
    """
    Wraps and utilizes regular expression to quickly evaluate whether a path
    is included or excluded from a desired set of files. The desired set of
    files to include or exclude is indicated by appending a list of fnmatch
    expressions. The expressions are evaluated is the order that they are
    added.
    """
    def __init__(self):
        self.layers = []

    def _append(self, layer_type, regex):
        self.layers.append({'layer_type': layer_type,
                            'regex':      regex})

    def _compile(self, fnmatches, base_path):
        if base_path:
            fnmatches = [os.path.join(base_path, f) for f in fnmatches]
        return re.compile('|'.join([fnmatch.translate(f) for f in fnmatches]))

    def append_include(self, fnmatches, base_path=None):
        if len(fnmatches) == 0:
            return
        self._append('include', self._compile(fnmatches, base_path))

    def append_exclude(self, fnmatches, base_path=None):
        if len(fnmatches) == 0:
            return
        self._append('exclude', self._compile(fnmatches, base_path))

    def _matches_regex(self, path, regex):
        return regex.match(path) is not None

    def _evaluate_layers(self, path):
        for layer in self.layers:
            if layer['layer_type'] is 'include':
                yield self._matches_regex(path, layer['regex'])
            if layer['layer_type'] is 'exclude':
                yield not self._matches_regex(path, layer['regex'])

    def evaluate(self, path):
        return False not in self._evaluate_layers(path)
