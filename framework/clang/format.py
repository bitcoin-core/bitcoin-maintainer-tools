#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import re
import os
import sys
import subprocess

from framework.path.path import Path
from framework.file.io import read_file, write_file


class ClangFormatStyle(object):
    """
    Reads and parses a .clang-format style file to represent it. The style can
    have keys removed and it can be translated into a '--style' argument for
    invoking clang-format.
    """
    def __init__(self, file_path):
        p = Path(file_path)
        p.assert_exists()
        p.assert_is_file()
        p.assert_mode(os.R_OK)
        self.file_path = file_path
        self.raw_contents = read_file(file_path)
        self.parameters = self._parse_parameters()
        self.rejected_parameters = {}

    def __str__(self):
        return self.file_path

    def _parse_parameters(self):
        # Python does not have a built-in yaml parser, so here is a
        # hand-written one that *seems* to minimally work for this purpose.
        many_spaces = re.compile(': +')
        spaces_removed = many_spaces.sub(':', self.raw_contents)
        # split into a list of lines
        lines = [l for l in spaces_removed.split('\n') if l != '']
        # split by the colon separator
        split = [l.split(':') for l in lines]
        # present as a dictionary
        return {item[0]: ''.join(item[1:]) for item in split}

    def reject_parameter(self, key):
        if key not in self.rejected_parameters:
            self.rejected_parameters[key] = self.parameters.pop(key)

    def style_arg(self):
        return '-style={%s}' % ', '.join(["%s: %s" % (k, v) for k, v in
                                          self.parameters.items()])


class ClangFormat(object):
    """
    Facility to read in the formatted content of a file using a particular
    clang-format binary and style file.
    """
    def __init__(self, binary, style_path):
        self.binary_path = binary['path']
        self.binary_version = binary['version']
        self.style_path = style_path
        self.style = ClangFormatStyle(self.style_path)
        self.UNKNOWN_KEY_REGEX = re.compile("unknown key '(?P<key_name>\w+)'")

    def _parse_unknown_key(self, err):
        if len(err) == 0:
            return 0, None
        match = self.UNKNOWN_KEY_REGEX.search(err)
        if not match:
            return len(err), None
        return len(err), match.group('key_name')

    def _try_format_file(self, file_path):
        cmd = [self.binary_path, self.style.style_arg(), file_path]
        return subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)

    def read_formatted_file(self, file_path):
        while True:
            p = self._try_format_file(file_path)
            out = p.stdout.read().decode('utf-8')
            err = p.stderr.read().decode('utf-8')
            p.communicate()
            if p.returncode != 0:
                sys.exit("*** clang-format could not execute")
            # Older versions of clang don't support some style parameter keys,
            # so we work around by redacting any key that gets rejected until
            # we find a subset of parameters that can apply the format without
            # producing any stderr output.
            err_len, unknown_key = self._parse_unknown_key(err)
            if not unknown_key and err_len > 0:
                sys.exit("*** clang-format produced unknown output to stderr")
            if unknown_key:
                self.style.reject_parameter(unknown_key)
                continue
            return out

    def rejected_parameters(self):
        return self.style.rejected_parameters
