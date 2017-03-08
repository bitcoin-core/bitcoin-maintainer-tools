#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import sys
import argparse
import hashlib
import json

from framework.print.buffer import PrintBuffer
from framework.argparse.option import add_jobs_option
from framework.argparse.option import add_json_option
from framework.file.info import FileInfo
from framework.file.style import FileStyleDiff, FileStyleScore
from framework.cmd.file_content import FileContentCmd
from framework.git.parameter import add_git_tracked_targets_parameter
from framework.clang.option import add_clang_options
from framework.clang.option import finish_clang_settings


APPLIES_TO = ['*.cpp', '*.h']


###############################################################################
# gather file and diff info
###############################################################################

class ClangFormatFileInfo(FileInfo):
    """
    Obtains and represents the information regarding a single file obtained
    from clang-format.
    """
    def __init__(self, repository, file_path, clang_format, force):
        super().__init__(repository, file_path)
        self.clang_format = clang_format
        self.force = force

    def read(self):
        super().read()
        self['formatted'] = (
            self.clang_format.read_formatted_file(self['file_path']))
        self._exit_if_parameters_unsupported()
        self.set_write_content(self['formatted'])

    def _exit_if_parameters_unsupported(self):
        if self.force:
            return
        rejected_parameters = self.clang_format.style.rejected_parameters
        if len(rejected_parameters) > 0:
            b = PrintBuffer()
            b.add_red("\nERROR: ")
            b.add("clang-format version %s does not support all parameters "
                  "given in\n%s\n\n" % (self.clang_format.binary_version,
                                        self.clang_format.style))
            b.add("Unsupported parameters:\n")
            for parameter in rejected_parameters:
                b.add("\t%s\n" % parameter)
            # The applied formating has subtle differences that vary between
            # major releases of clang-format. The recommendation should
            # probably follow the latest widely-available stable release.
            repo_info = self['repository'].repo_info
            b.add("\nUsing clang-format version %s or higher is recommended\n"
                  % repo_info['clang_format_recommended']['min_version'])
            b.add("Use the --force option to override and proceed anyway.\n\n")
            b.flush()
            sys.exit("*** missing clang-format support.")

    def compute(self):
        self['matching'] = self['content'] == self['formatted']
        self['formatted_md5'] = (
            hashlib.md5(self['formatted'].encode('utf-8')).hexdigest())
        self.update(FileStyleDiff(self['content'], self['formatted']))


###############################################################################
# cmd base class
###############################################################################

class ClangFormatCmd(FileContentCmd):
    """
    Common base class for the commands in this script.
    """
    def __init__(self, settings):
        assert hasattr(settings, 'force')
        assert hasattr(settings, 'clang_format')
        settings.include_fnmatches = APPLIES_TO
        super().__init__(settings)
        self.force = settings.force
        self.clang_format = settings.clang_format

    def _file_info_list(self):
        return [ClangFormatFileInfo(self.repository, f, self.clang_format,
                                    self.force)
                for f in self.files_targeted]


###############################################################################
# report cmd
###############################################################################

class ReportCmd(ClangFormatCmd):
    """
    'report' subcommand class.
    """
    def __init__(self, settings):
        settings.force = True
        super().__init__(settings)
        self.title = "Clang Format Report"

    def _cumulative_md5(self):
        # nothing fancy, just hash all the hashes
        h = hashlib.md5()
        for f in self.file_infos:
            h.update(f['formatted_md5'].encode('utf-8'))
        return h.hexdigest()

    def _files_in_ranges(self):
        files_in_ranges = {}
        ranges = [(90, 99), (80, 89), (70, 79), (60, 69), (50, 59), (40, 49),
                  (30, 39), (20, 29), (10, 19), (0, 9)]
        for lower, upper in ranges:
            files_in_ranges['%2d%%-%2d%%' % (lower, upper)] = (
                sum(1 for f in self.file_infos if
                    f['score'].in_range(lower, upper)))
        return files_in_ranges

    def _exec(self):
        r = super()._exec()
        file_infos = self.file_infos
        r['clang_format_path'] = self.clang_format.binary_path
        r['clang_format_version'] = str(self.clang_format.binary_version)
        r['clang_style_path'] = str(self.clang_format.style_path)
        r['rejected_parameters'] = self.clang_format.style.rejected_parameters
        r['elapsed_time'] = self.elapsed_time
        r['lines_before'] = sum(f['lines_before'] for f in file_infos)
        r['lines_added'] = sum(f['lines_added'] for f in file_infos)
        r['lines_removed'] = sum(f['lines_removed'] for f in file_infos)
        r['lines_unchanged'] = sum(f['lines_unchanged'] for f in file_infos)
        r['lines_after'] = sum(f['lines_after'] for f in file_infos)
        score = FileStyleScore(r['lines_before'], r['lines_added'],
                               r['lines_removed'], r['lines_unchanged'],
                               r['lines_after'])
        r['style_score'] = float(score)
        r['slow_diffs'] = [{'file_path': f['file_path'],
                            'diff_time': f['diff_time']} for f in
                           file_infos if f['diff_time'] > 1.0]
        r['matching'] = sum(1 for f in file_infos if f['matching'])
        r['not_matching'] = sum(1 for f in file_infos if not f['matching'])
        r['formatted_md5'] = self._cumulative_md5()
        r['files_in_ranges'] = self._files_in_ranges()
        return r

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        b.add(super()._output(results))
        r = results
        b.add("%-30s %s\n" % ("clang-format bin:", r['clang_format_path']))
        b.add("%-30s %s\n" % ("clang-format version:",
                              r['clang_format_version']))
        b.add("%-30s %s\n" % ("Using style in:", r['clang_style_path']))
        b.separator()
        if len(r['rejected_parameters']) > 0:
            b.add_red("WARNING")
            b.add(" - This version of clang-format does not support the "
                  "following style\nparameters, so they were not used:\n\n")
            for param in r['rejected_parameters']:
                b.add("%s\n" % param)
            b.separator()
        b.add("%-30s %.02fs\n" % ("Elapsed time:", r['elapsed_time']))
        if len(r['slow_diffs']) > 0:
            b.add("Slowest diffs:\n")
            for slow in r['slow_diffs']:
                b.add("%6.02fs for %s\n" % (slow['diff_time'],
                                            slow['file_path']))
        b.separator()
        b.add("%-30s %4d\n" % ("Files scoring 100%:", r['matching']))
        b.add("%-30s %4d\n" % ("Files scoring <100%:", r['not_matching']))
        b.add("%-30s %s\n" % ("Formatted Content MD5:", r['formatted_md5']))
        b.separator()
        for score_range in reversed(sorted(r['files_in_ranges'].keys())):
            b.add("%-30s %4d\n" % ("Files scoring %s:" % score_range,
                                   r['files_in_ranges'][score_range]))
        b.separator()
        b.add("Overall scoring:\n\n")
        score = FileStyleScore(r['lines_before'], r['lines_added'],
                               r['lines_removed'], r['lines_unchanged'],
                               r['lines_after'])
        b.add(str(score))
        b.separator()
        return str(b)


def add_report_cmd(subparsers):
    report_help = ("Produces a report with the analysis of the code format "
                   "adherence of the selected targets taken as a group.")
    parser = subparsers.add_parser('report', help=report_help)
    parser.set_defaults(cmd=lambda o: ReportCmd(o))
    add_jobs_option(parser)
    add_json_option(parser)
    add_clang_options(parser, style_file=True)
    add_git_tracked_targets_parameter(parser)


###############################################################################
# check cmd
###############################################################################

class CheckCmd(ClangFormatCmd):
    """
    'check' subcommand class.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.title = "Clang Format Check"

    def _exec(self):
        r = super()._exec()
        r['failures'] = [{'file_path':       f['file_path'],
                          'style_score':     float(f['score']),
                          'lines_before':    f['lines_before'],
                          'lines_added':     f['lines_added'],
                          'lines_removed':   f['lines_removed'],
                          'lines_unchanged': f['lines_unchanged'],
                          'lines_after':     f['lines_after']}
                         for f in self.file_infos if not f['matching']]
        return r

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        b.add(super()._output(results))
        r = results
        for f in r['failures']:
            b.add("A code format issue was detected in ")
            b.add_red("%s\n\n" % f['file_path'])
            score = FileStyleScore(f['lines_before'], f['lines_added'],
                                   f['lines_removed'], f['lines_unchanged'],
                                   f['lines_after'])
            b.add(str(score))
            b.separator()
        if len(r['failures']) == 0:
            b.add_green("No format issues found!\n")
        else:
            b.add_red("These files can be formatted by running:\n")
            b.add("$ clang_format.py format [option [option ...]] "
                  "[target [target ...]]\n")
        b.separator()
        return str(b)

    def _shell_exit(self, results):
        return (0 if len(results['failures']) == 0 else
                "*** code format issue found")


def add_check_cmd(subparsers):
    check_help = ("Validates that the selected targets match the style, gives "
                  "a per-file report and returns a non-zero shell status if "
                  "there are any format issues discovered.")
    parser = subparsers.add_parser('check', help=check_help)
    parser.set_defaults(cmd=lambda o: CheckCmd(o))
    add_jobs_option(parser)
    add_json_option(parser)
    add_clang_options(parser, style_file=True, force=True)
    add_git_tracked_targets_parameter(parser)


###############################################################################
# format cmd
###############################################################################

class FormatCmd(ClangFormatCmd):
    """
    'format' subcommand class.
    """
    def __init__(self, settings):
        settings.json = False
        super().__init__(settings)
        self.title = "Clang Format"

    def _exec(self):
        super()._exec()
        self.file_infos.write_all()

    def _output(self, results):
        return None


def add_format_cmd(subparsers):
    format_help = ("Applies the style formatting to the target files.")
    parser = subparsers.add_parser('format', help=format_help)
    parser.set_defaults(cmd=lambda o: FormatCmd(o))
    add_clang_options(parser, style_file=True, force=True)
    add_git_tracked_targets_parameter(parser)


###############################################################################
# UI
###############################################################################


if __name__ == "__main__":
    description = ("A utility for invoking clang-format to look at the C++ "
                   "code formatting in the repository. It produces "
                   "reports of style metrics and also can apply formatting.")
    parser = argparse.ArgumentParser(description=description)
    subparsers = parser.add_subparsers()
    add_report_cmd(subparsers)
    add_check_cmd(subparsers)
    add_format_cmd(subparsers)
    settings = parser.parse_args()
    if not hasattr(settings, "cmd"):
        parser.print_help()
        sys.exit("*** missing argument")
    finish_clang_settings(settings)
    settings.cmd(settings).run()
