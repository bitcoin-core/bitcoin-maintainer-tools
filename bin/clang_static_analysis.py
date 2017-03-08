#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import sys
import os
import time
import argparse
import json

from framework.print.buffer import PrintBuffer
from framework.argparse.option import add_jobs_option
from framework.argparse.option import add_json_option
from framework.git.parameter import add_git_repository_parameter
from framework.cmd.repository import RepositoryCmd
from framework.clang.option import add_clang_options
from framework.clang.option import finish_clang_settings


###############################################################################
# cmd base class
###############################################################################

class ClangStaticAnalysisCmd(RepositoryCmd):
    """
    Superclass for a command that runs clang static analysis.
    """
    def __init__(self, settings):
        assert hasattr(settings, 'scan_build')
        super().__init__(settings)
        self.json = settings.json
        self.scan_build = settings.scan_build

    def _exec(self):
        start_time = time.time()
        self.scan_build.cleaner.run(silent=self.json)
        self.scan_build.run(silent=self.json)
        elapsed_time = time.time() - start_time
        directory, issues = self.scan_build.get_results()
        return {'elapsed_time':      time.time() - start_time,
                'results_directory': directory,
                'issues':            issues}

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        r = results
        b.separator()
        b.add("Took %.2f seconds to analyze with scan-build\n" %
              r['elapsed_time'])
        b.add("Found %d issues:\n" % len(r['issues']))
        b.separator()
        return str(b)

    def _shell_exit(self, results):
        return 0


###############################################################################
# report cmd
###############################################################################

class ReportCmd(ClangStaticAnalysisCmd):
    """
    'report' subcommand class.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.title = "Clang Static Analysis Report"

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        b.add(super()._output(results))
        r = results
        issue_no = 0
        for issue in r['issues']:
            b.add("%d: %s:%d:%d - %s\n" % (issue_no, issue['file'],
                                           issue['line'], issue['col'],
                                           issue['description']))
            issue_no = issue_no + 1
        if len(r['issues']) > 0:
            viewer = self.scan_build.viewer
            b.add(viewer.launch_instructions(r['results_directory']))
        return str(b)


def add_report_cmd(subparsers):
    report_help = ("Runs clang static analysis and produces a summary report "
                   "of the findings.")
    parser = subparsers.add_parser('report', help=report_help)
    parser.set_defaults(cmd=lambda o: ReportCmd(o))
    add_jobs_option(parser)
    add_json_option(parser)
    add_clang_options(parser, report_path=True)
    add_git_repository_parameter(parser)


###############################################################################
# check cmd
###############################################################################

class CheckCmd(ClangStaticAnalysisCmd):
    """
    'check' subcommand class.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.title = "Clang Static Analysis Check"

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        b.add(super()._output(results))
        r = results
        for issue in r['issues']:
            b.add("An issue has been found in ")
            b.add_red("%s:%d:%d\n" % (issue['file'], issue['line'],
                                      issue['col']))
            b.add("Type:         %s\n" % issue['type'])
            b.add("Description:  %s\n\n" % issue['description'])
            event_no = 0
            for event in issue['events']:
                b.add("%d: " % event_no)
                b.add("%s:%d:%d - " % (event['file'], event['line'],
                                       event['col']))
                b.add("%s\n" % event['message'])
                event_no = event_no + 1
            b.separator()
        if len(r['issues']) == 0:
            b.add_green("No static analysis issues found!\n")
            b.separator()
        else:
            viewer = self.scan_build.viewer
            b.add(viewer.launch_instructions(r['results_directory']))
        return str(b)

    def _shell_exit(self, results):
        return (0 if len(results['issues']) == 0 else
                "*** static analysis issues found.")


def add_check_cmd(subparsers):
    check_help = ("Runs clang static analysis and output details for each "
                  "discovered issue. Returns a non-zero shell status if any "
                  "issues are found.")
    parser = subparsers.add_parser('check', help=check_help)
    parser.set_defaults(cmd=lambda o: CheckCmd(o))
    add_jobs_option(parser)
    add_json_option(parser)
    add_clang_options(parser, report_path=True)
    add_git_repository_parameter(parser)


###############################################################################
# UI
###############################################################################

if __name__ == "__main__":
    description = ("A utility for running clang static analysis on a codebase "
                   "in a consistent way.")
    parser = argparse.ArgumentParser(description=description)
    subparsers = parser.add_subparsers()
    add_report_cmd(subparsers)
    add_check_cmd(subparsers)
    settings = parser.parse_args()
    if not hasattr(settings, "cmd"):
        parser.print_help()
        sys.exit("*** missing argument")
    finish_clang_settings(settings)
    settings.cmd(settings).run()
