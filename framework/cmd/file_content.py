#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import time
import json
import sys
from framework.print.buffer import PrintBuffer
from framework.file.filter import FileFilter
from framework.file.info import FileInfos
from framework.cmd.repository import RepositoryCmd


class FileContentCmd(RepositoryCmd):
    """
    Base class for commands that compute info on a set of files based on
    the content inside of the files. Provides a common way for indicating
    a subset of files that the operation is to apply to via lists of
    fnmatch expressions.
    """
    def __init__(self, settings):
        assert hasattr(settings, 'json')
        super().__init__(settings, silent=settings.json)
        assert hasattr(settings, 'jobs')
        assert hasattr(settings, 'include_fnmatches')
        assert hasattr(settings, 'target_fnmatches')
        self.title = "FileContentCmd superclass"
        self.json = settings.json
        self.jobs = settings.jobs
        self.tracked_files = self.repository.tracked_files()
        exclude_fnmatches = self.repository.repo_info['subtrees']['fnmatches']
        self.files_in_scope = list(
            self._files_in_scope(self.repository, self.tracked_files,
                                 settings.include_fnmatches,
                                 exclude_fnmatches))
        self.files_targeted = list(
            self._files_targeted(self.repository, self.files_in_scope,
                                 settings.include_fnmatches, exclude_fnmatches,
                                 settings.target_fnmatches))

    def _scope_filter(self, repository, include_fnmatches, exclude_fnmatches):
        file_filter = FileFilter()
        file_filter.append_include(include_fnmatches,
                                   base_path=str(repository))
        file_filter.append_exclude(exclude_fnmatches,
                                   base_path=str(repository))
        return file_filter

    def _files_in_scope(self, repository, tracked_files, include_fnmatches,
                        exclude_fnmatches):
        file_filter = self._scope_filter(repository, include_fnmatches,
                                         exclude_fnmatches)
        return (f for f in tracked_files if file_filter.evaluate(f))

    def _target_filter(self, repository, include_fnmatches, exclude_fnmatches,
                       target_fnmatches):
        file_filter = self._scope_filter(repository, include_fnmatches,
                                         exclude_fnmatches)
        file_filter.append_include(target_fnmatches, base_path=repository)
        return file_filter

    def _files_targeted(self, repository, tracked_files, include_fnmatches,
                        exclude_fnmatches, target_fnmatches):
        file_filter = self._target_filter(repository, include_fnmatches,
                                          exclude_fnmatches, target_fnmatches)
        return (f for f in tracked_files if file_filter.evaluate(f))

    def _read_file_infos(self):
        self.file_infos.read_all()

    def _compute_file_infos(self):
        self.file_infos.compute_all()

    def _read_and_compute_file_infos(self):
        start_time = time.time()
        self.file_infos = FileInfos(self.jobs, self._file_info_list())
        self._read_file_infos()
        self._compute_file_infos()
        self.elapsed_time = time.time() - start_time

    def _exec(self):
        self._read_and_compute_file_infos()
        r = super()._exec()
        r['tracked_files'] = len(self.tracked_files)
        r['files_in_scope'] = len(self.files_in_scope)
        r['files_targeted'] = len(self.files_targeted)
        r['jobs'] = self.jobs
        return r

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        r = results
        b.separator()
        b.add("%4d files tracked in repo\n" % r['tracked_files'])
        b.add("%4d files in scope according to .bitcoin_maintainer_tools.json "
              "settings\n" % r['files_in_scope'])
        b.add("%4d files examined according to listed targets\n" %
              r['files_targeted'])
        b.add("%4d parallel jobs for computing analysis\n" % r['jobs'])
        b.separator()
        return str(b)

    def _shell_exit(self, results):
        return 0
