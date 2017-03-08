#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import difflib
import time


class FileStyleScore(object):
    """
    A crude calculation to give a percentage rating for adherence to a
    defined style.
    """
    def __init__(self, lines_before, lines_added, lines_removed,
                 lines_unchanged, lines_after):
        self.lines_before = lines_before
        self.lines_unchanged = lines_unchanged
        self.lines_added = lines_added
        self.lines_removed = lines_removed
        self.lines_after = lines_after
        self.score = (100.0 if (lines_added + lines_removed) == 0 else
                      min(abs(1.0 - (float(lines_before - lines_unchanged) /
                                     float(lines_before))) * 100, 99.999))

    def __str__(self):
        return (" +--------+         +------------+--------+---------+--------"
                "---+------------+\n"
                " | score  |         |     before |  added | removed | unchang"
                "ed |      after |\n"
                " +--------+ +-------+------------+--------+---------+--------"
                "---+------------+\n"
                " | %3.2f%% | | lines | %10d | %6d | %7d | %9d | %10d |\n"
                " +--------+ +-------+------------+--------+---------+--------"
                "---+------------+\n" % (self.score, self.lines_before,
                                         self.lines_added, self.lines_removed,
                                         self.lines_unchanged,
                                         self.lines_after))

    def __float__(self):
        return self.score

    def in_range(self, lower, upper):
        # inclusive:
        return (self.score >= lower) and (self.score <= upper)


DIFFER = difflib.Differ()


class FileStyleDiff(dict):
    """
    Computes metrics about a diff between two versions of content in a file.
    """
    def __init__(self, contents_before, contents_after):
        super().__init__()
        lines_before = contents_before.splitlines()
        lines_after = contents_after.splitlines()
        self['lines_before'] = len(lines_before)
        self['lines_after'] = len(lines_after)
        start_time = time.time()
        diff = DIFFER.compare(lines_before, lines_after)
        (self['lines_added'],
         self['lines_removed'],
         self['lines_unchanged']) = self._sum_lines_of_type(diff)
        self['score'] = FileStyleScore(self['lines_before'],
                                       self['lines_added'],
                                       self['lines_removed'],
                                       self['lines_unchanged'],
                                       self['lines_after'])
        self['diff_time'] = time.time() - start_time

    def _sum_lines_of_type(self, diff):
        def classify_diff_lines(diff):
            for l in diff:
                if l.startswith('+ '):
                    yield 1, 0, 0
                elif l.startswith('- '):
                    yield 0, 1, 0
                elif l.startswith('  '):
                    yield 0, 0, 1

        sums = [sum(c) for c in zip(*classify_diff_lines(diff))]
        return (sums[0], sums[1], sums[2]) if len(sums) == 3 else (0, 0, 0)
