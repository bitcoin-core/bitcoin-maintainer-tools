#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import sys
import os
from multiprocessing import Pool

from framework.file.io import read_file, write_file


class FileInfo(dict):
    """
    Superclass to represent a file, its contents, and computed information
    about the file.
    """
    def __init__(self, repository, file_path):
        super().__init__()
        self['repository'] = repository
        self['file_path'] = file_path
        self['filename'] = file_path.split(str(repository))[1]

    def read(self):
        self['content'] = read_file(self['file_path'])

    def compute(self):
        sys.exit("*** 'compute' function must be redefined by subclass")

    def set_write_content(self, write_content):
        self['write_content'] = write_content

    def write(self):
        if self['content'] == self['write_content']:
            return
        write_file(self['file_path'], self['write_content'])


def compute_file_info(file_info):
    file_info.compute()
    return file_info


class FileInfos(object):
    """
    A container for a set of files which can do the computing of the file info
    in parallel. I/O is done in serial because some VM setups can't gracefully
    schedule parallel, high-throughput file system I/O.
    """
    def __init__(self, jobs, file_info_iter):
        self.jobs = jobs
        self.pool = Pool(jobs)
        self.file_info_list = list(file_info_iter)

    def __iter__(self):
        for file_info in self.file_info_list:
            yield file_info

    def read_all(self):
        for file_info in self.file_info_list:
            file_info.read()

    def write_all(self):
        for file_info in self.file_info_list:
            file_info.write()

    def compute_all(self):
        self.file_info_list = self.pool.map(compute_file_info, self)
