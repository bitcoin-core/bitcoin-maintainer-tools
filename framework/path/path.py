#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import sys
import os


class Path(object):
    """
    Base class for representing and validating command-line arguments that
    are strings but are supposed to be a file system path with particular
    properties.
    """
    def __init__(self, path):
        self.path = self._get_real_path(str(path))

    def __str__(self):
        return self.path

    def _get_real_path(self, path):
        return os.path.realpath(os.path.abspath(path))

    def exists(self):
        return os.path.exists(self.path)

    def assert_exists(self):
        if not self.exists():
            sys.exit("*** does not exist: %s" % self.path)

    def assert_mode(self, flags):
        if not os.access(self.path, flags):
            sys.exit("*** %s does not have mode: %x" % (self.path, flags))

    def is_file(self):
        return os.path.isfile(self.path)

    def assert_is_file(self):
        if not self.is_file():
            sys.exit("*** %s is not a file" % self.path)

    def is_directory(self):
        return os.path.isdir(self.path)

    def assert_is_directory(self):
        if not self.is_directory():
            sys.exit("*** %s is not a directory" % self.path)

    def assert_under_directory(self, directory):
        real_directory = self._get_real_path(directory)
        if not self.path.startswith(real_directory):
            sys.exit("*** %s is not under directory %s" % (self.path,
                                                           real_directory))

    def filename(self):
        self.assert_is_file()
        return os.path.basename(self.path)

    def has_filename(self, filename):
        return filename == self.filename()

    def assert_has_filename(self, filename):
        if not self.has_filename(filename):
            sys.exit("*** %s does not have filename %s" % (self.path,
                                                           filename))

    def containing_directory(self):
        return os.path.dirname(self.path)

    def directory(self):
        return self.containing_directory() if self.is_file() else self.path

    def extension(self):
        _, ext = os.path.splitext(self.filename())
        return ext

    def extension_is_one_of(self, extensions):
        return self.extension() in extensions

    def assert_extension_is_one_of(self, extensions):
        if not self.extension_is_one_of(extensions):
            sys.exit("*** %s does not have extension %s" % (self.path,
                                                            extensions))
