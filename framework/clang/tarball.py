#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import platform


class ClangTarball(object):
    """
    Matches the current platform to the LLVM download. Only works for platforms
    that have been explicitly tested but it should be straightforward to add
    more as needed.
    """
    def __init__(self):
        self.supported = self._supported()

    def _supported_debian(self, version):
        return version.startswith("8.")

    def _supported_ubuntu(self, id):
        return id in ['trusty', 'xenial']

    def _supported(self):
        if platform.system() != "Linux":
            print(platform.system())
            return False
        if platform.machine() != "x86_64":
            return False
        self.distname, self.version, self.id = platform.linux_distribution()
        if self.distname not in ['debian', 'Ubuntu']:
            return False
        if self.distname == 'debian':
            return self._supported_debian(self.version)
        else:
            return self._supported_ubuntu(self.id)

    def url(self):
        if not self.supported:
            return None
        return "http://releases.llvm.org/3.9.0/%s" % self.filename()

    def filename(self):
        if not self.supported:
            return None
        return ("%s.tar.xz" % self.unpacked_directory())

    def unpacked_directory(self):
        if not self.supported:
            return None
        if self.distname == 'debian':
            return "clang+llvm-3.9.0-x86_64-linux-gnu-debian8"
        else:
            if self.id == 'trusty':
                return "clang+llvm-3.9.0-x86_64-linux-gnu-ubuntu-14.04"
            else:
                return "clang+llvm-3.9.0-x86_64-linux-gnu-ubuntu-16.04"

    def sha256(self):
        if not self.supported:
            return None
        if self.distname == 'debian':
            return ("916e2c2c1411e7e568e856e614408a8072c1884339865e8cfabc71880"
                    "f28a804")
        else:
            if self.id == 'trusty':
                return ("6eba6f834424086a40ca95e7b013765d8bcbfdce193b5ab7da42e"
                        "2ff5beadf3e")
            else:
                return ("e189a9e605ec035bfa1cfebf37374a92109b61291dc17c6f71239"
                        "8ecccb3498a")
