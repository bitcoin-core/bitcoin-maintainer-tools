#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

GREEN = '\033[92m'
RED = '\033[91m'
ENDC = '\033[0m'


class PrintBuffer(object):
    '''
    A class for appending to a string without printing it yet. Also provides
    a few amenities for constructing report output.
    '''
    def __init__(self):
        self.report = []

    def __str__(self):
        return ''.join(self.report)

    def add(self, string):
        self.report.append(string)

    def add_red(self, string):
        self.add(RED + string + ENDC)

    def add_green(self, string):
        self.add(GREEN + string + ENDC)

    def separator(self):
        self.add('-' * 80 + '\n')

    def flush(self):
        print(str(self), end='')
        self.report = []
