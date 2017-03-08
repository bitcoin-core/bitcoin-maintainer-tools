#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import argparse

from framework.cmd.repository import RepositoryCmds
from clang_static_analysis import ReportCmd as ClangStaticAnalysisReport
from basic_style import ReportCmd as BasicStyleReport
from copyright_header import ReportCmd as CopyrightHeaderReport
from clang_format import ReportCmd as ClangFormatReport
from framework.argparse.option import add_jobs_option
from framework.argparse.option import add_json_option
from framework.clang.option import add_clang_options
from framework.clang.option import finish_clang_settings
from framework.git.parameter import add_git_tracked_targets_parameter


class Reports(RepositoryCmds):
    """
    Invokes several underlying RepositoryCmd report command instances and
    aggregates them into a single report.
    """
    def __init__(self, settings):
        repository_cmds = {
            'copyright_header':      CopyrightHeaderReport(settings),
            'basic_style':           BasicStyleReport(settings),
            'clang_format':          ClangFormatReport(settings),
            'clang_static_analysis': ClangStaticAnalysisReport(settings),
        }
        self.json = settings.json
        super().__init__(settings, repository_cmds, silent=settings.json)

    def _output(self, results):
        if self.json:
            return super()._output(results)
        reports = [(self.repository_cmds[l].title + ":\n" +
                    self.repository_cmds[l]._output(r)) for l, r in
                   sorted(results.items())]
        return '\n'.join(reports)


if __name__ == "__main__":
    description = ("Wrapper to invoke a collection of scripts that produce "
                   "data from analyzing a repository.")
    parser = argparse.ArgumentParser(description=description)
    add_jobs_option(parser)
    add_json_option(parser)
    add_clang_options(parser, report_path=True, style_file=True)
    add_git_tracked_targets_parameter(parser)
    settings = parser.parse_args()
    finish_clang_settings(settings)
    reports = Reports(settings)
    reports.run()
