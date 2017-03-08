#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import re
import sys
import argparse
import json

from framework.print.buffer import PrintBuffer
from framework.file.filter import FileFilter
from framework.file.info import FileInfo
from framework.cmd.file_content import FileContentCmd
from framework.argparse.option import add_jobs_option
from framework.argparse.option import add_json_option
from framework.git.parameter import add_git_tracked_targets_parameter
from framework.git.path import GitFilePath


APPLIES_TO = ['*.h', '*.cpp', '*.py', '*.sh', '*.am', '*.m4', '*.include']

###############################################################################
# regexes
###############################################################################

YEAR = "20[0-9][0-9]"
YEAR_RANGE = '(?P<start_year>%s)(-(?P<end_year>%s))?' % (YEAR, YEAR)

YEAR_RANGE_COMPILED = re.compile(YEAR_RANGE)

###############################################################################
# header regex
###############################################################################

HOLDERS = [
    "Satoshi Nakamoto",
    "The Bitcoin Core developers",
    "Pieter Wuille",
    "Wladimir J\\. van der Laan",
    "Jeff Garzik",
    "BitPay Inc\\.",
    "MarcoFalke",
    "ArtForz -- public domain half-a-node",
    "Jeremy Rubin",
]
ANY_HOLDER = '|'.join([h for h in HOLDERS])
COPYRIGHT_LINE = (
    "(#|//|dnl) Copyright \\(c\\) %s (%s)" % (YEAR_RANGE, ANY_HOLDER))
LAST_TWO_LINES = ("(#|//|dnl) Distributed under the MIT software license, see "
                  "the accompanying\n(#|//|dnl) file COPYING or "
                  "http://www\\.opensource\\.org/licenses/mit-license\\.php\\."
                  "\n")

HEADER = "(%s\n)+%s" % (COPYRIGHT_LINE, LAST_TWO_LINES)

HEADER_COMPILED = re.compile(HEADER)


ISSUE_1 = {
    'description': "A valid header was expected, but the file does not match "
                   "the regex.",
    'resolution': """
A correct MIT License header copyrighted by 'The Bitcoin Core developers' in
the present year can be inserted into a file by running:

    $ ./copyright_header.py insert <filename>

If there was a preexisting invalid header in the file, that will need to be
manually deleted. If there is a new copyright holder for the MIT License, the
holder will need to be added to the HOLDERS list to include it in the regex
check.
"""
}

ISSUE_2 = {
    'description': "A valid header was found in the file, but it wasn't "
                   "expected.",
    'resolution': """
The header was not expected due to a setting. If a valid copyright header has
been added to the file, the filename can be removed from the
'no_copyright_header_expected' settings.
"""
}

ISSUE_3 = {
    'description': "Another 'copyright' occurrence was found, but it wasn't "
                   "expected.",
    'resolution': """
This file's body has a regular expression match for the (case-sensitive) words
"Copyright", "COPYRIGHT" or 'copyright". If this was an appropriate addition,
the file can be added to the 'other_copyright_occurrences_expected' settings.
"""
}

ISSUE_4 = {
    'description': "Another 'copyright' occurrence was expected, but wasn't "
                   "found.",
    'resolution': """
A use of the (case-sensitive) words "Copyright", "COPYRIGHT", or 'copyright'
outside of the regular copyright header was expected due to a setting but it
was not found. If this was an appropriate removal, it can be removed from the
'other_copyright_occurrences_expected' settings.
"""
}

NO_ISSUE = {
    'description': "Everything is excellent",
    'resolution': "(none)"
}

ISSUES = [ISSUE_1, ISSUE_2, ISSUE_3, ISSUE_4, NO_ISSUE]


SCRIPT_HEADER = ("# Copyright (c) %s The Bitcoin Core developers\n"
                 "# Distributed under the MIT software license, see the "
                 "accompanying\n# file COPYING or http://www.opensource.org/"
                 "licenses/mit-license.php.\n")

CPP_HEADER = ("// Copyright (c) %s The Bitcoin Core developers\n// "
              "Distributed under the MIT software license, see the "
              "accompanying\n// file COPYING or http://www.opensource.org/"
              "licenses/mit-license.php.\n")

OTHER_COPYRIGHT = "(Copyright|COPYRIGHT|copyright)"
OTHER_COPYRIGHT_COMPILED = re.compile(OTHER_COPYRIGHT)

###############################################################################
# file info
###############################################################################

class CopyrightHeaderFileInfo(FileInfo):
    """
    Obtains and represents the information regarding a single file.
    """
    def __init__(self, repository, file_path, copyright_expected,
                 other_copyright_expected):
        super().__init__(repository, file_path)
        self['hdr_expected'] = copyright_expected
        self['other_copyright_expected'] = other_copyright_expected

    def _starts_with_shebang(self):
        if len(self['content']) < 2:
            return False
        return self['content'][:2] == '#!'

    def _header_match_in_correct_place(self, header_match):
        start = header_match.start(0)
        if start == 0:
            return not self['shebang']
        return self['shebang'] and (self['content'][:start].count('\n') == 1)

    def _has_header(self):
        header_match = HEADER_COMPILED.search(self['content'])
        if not header_match:
            return False
        return self._header_match_in_correct_place(header_match)

    def _has_copyright_in_region(self, content_region):
        return OTHER_COPYRIGHT_COMPILED.search(content_region) is not None

    def _has_other_copyright(self):
        # look for the OTHER_COPYRIGHT regex outside the normal header regex
        # match
        header_match = HEADER_COMPILED.search(self['content'])
        region = (self['content'][header_match.end():] if header_match else
                  self['content'])
        return self._has_copyright_in_region(region)

    def _evaluate(self):
        if not self['has_header'] and self['hdr_expected']:
            return ISSUE_1
        if self['has_header'] and not self['hdr_expected']:
            return ISSUE_2
        if self['has_other'] and not self['other_copyright_expected']:
            return ISSUE_3
        if not self['has_other'] and self['other_copyright_expected']:
            return ISSUE_4
        return NO_ISSUE

    def compute(self):
        self['shebang'] = self._starts_with_shebang()
        self['has_header'] = self._has_header()
        self['has_other'] = self._has_other_copyright()
        self['evaluation'] = self._evaluate()
        self['pass'] = self['evaluation'] is NO_ISSUE


###############################################################################
# cmd base class
###############################################################################

class CopyrightHeaderCmd(FileContentCmd):
    """
    Common base class for the commands in this script.
    """
    def __init__(self, settings):
        settings.include_fnmatches = APPLIES_TO
        super().__init__(settings)
        self.no_copyright_filter = FileFilter()
        repo_info = self.repository.repo_info
        self.no_copyright_filter.append_include(
            repo_info['no_copyright_header_expected']['fnmatches'],
            base_path=str(self.repository))
        self.other_copyright_filter = FileFilter()
        self.other_copyright_filter.append_include(
            repo_info['other_copyright_occurrences_expected']['fnmatches'],
            base_path=str(self.repository))

    def _copyright_expected(self, file_path):
        return not self.no_copyright_filter.evaluate(file_path)

    def _other_copyright_expected(self, file_path):
        return self.other_copyright_filter.evaluate(file_path)

    def _file_info_list(self):
        return [CopyrightHeaderFileInfo(self.repository, f,
                                        self._copyright_expected(f),
                                        self._other_copyright_expected(f))
                for f in self.files_targeted]


###############################################################################
# report cmd
###############################################################################

class ReportCmd(CopyrightHeaderCmd):
    """
    'report' subcommand class.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.title = "Copyright Header Report"

    def _exec(self):
        r = super()._exec()
        r['hdr_expected'] = sum(1 for f in self.file_infos if
                                f['hdr_expected'])
        r['no_hdr_expected'] = sum(1 for f in self.file_infos if not
                                   f['hdr_expected'])
        r['other_copyright_expected'] = sum(1 for f in self.file_infos if
                                            f['other_copyright_expected'])
        r['no_other_copyright_expected'] = sum(
            1 for f in self.file_infos if not f['other_copyright_expected'])
        r['passed'] = sum(1 for f in self.file_infos if f['pass'])
        r['failed'] = sum(1 for f in self.file_infos if not f['pass'])
        r['issues'] = {}
        for issue in ISSUES:
            r['issues'][issue['description']] = sum(
                1 for f in self.file_infos if
                f['evaluation']['description'] == issue['description'])
        return r

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        r = results
        b.add(super()._output(results))
        b.add("%-70s %6d\n" % ("Files expected to have header:",
                               r['hdr_expected']))
        b.add("%-70s %6d\n" % ("Files not expected to have header:",
                               r['no_hdr_expected']))
        b.add("%-70s %6d\n" %
              ("Files expected to have 'copyright' occurrence outside header:",
               r['other_copyright_expected']))
        b.add("%-70s %6d\n" %
              ("Files not expected to have 'copyright' occurrence outside "
               "header:", r['no_other_copyright_expected']))
        b.add("%-70s %6d\n" % ("Files passed:", r['passed']))
        b.add("%-70s %6d\n" % ("Files failed:", r['failed']))
        b.separator()
        for key, value in sorted(r['issues'].items()):
            b.add("%-70s %6d\n" % ('"' + key + '":', value))
        b.separator()
        return str(b)


def add_report_cmd(subparsers):
    report_help = ("Produces a report of copyright header notices within "
                   "selected targets to help identify files that don't meet "
                   "expectations.")
    parser = subparsers.add_parser('report', help=report_help)
    parser.set_defaults(cmd=lambda o: ReportCmd(o))
    add_jobs_option(parser)
    add_json_option(parser)
    add_git_tracked_targets_parameter(parser)


###############################################################################
# check cmd
###############################################################################

class CheckCmd(CopyrightHeaderCmd):
    """
    'check' subcommand class.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.title = "Copyright Header Check"

    def _exec(self):
        r = super()._exec()
        r['issues'] = [{'file_path':  f['file_path'],
                        'evaluation': f['evaluation']} for f in
                       self.file_infos if not f['pass']]
        return r

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        b.add(super()._output(results))
        r = results
        for issue in r['issues']:
            b.add("An issue was found with ")
            b.add_red("%s" % issue['file_path'])
            b.add('\n\n%s\n\n' % issue['evaluation']['description'])
            b.add('Info for resolution:\n')
            b.add(issue['evaluation']['resolution'])
            b.separator()
        if len(r['issues']) == 0:
            b.add_green("No copyright header issues found!\n")
        return str(b)

    def _shell_exit(self, results):
        return (0 if len(results['issues']) == 0 else
                "*** copyright header issue found")


def add_check_cmd(subparsers):
    check_help = ("Validates that selected targets do not have copyright "
                  "header issues, gives a per-file report and returns a "
                  "non-zero shell status if there are any issues discovered.")
    parser = subparsers.add_parser('check', help=check_help)
    parser.set_defaults(cmd=lambda o: CheckCmd(o))
    add_jobs_option(parser)
    add_json_option(parser)
    add_git_tracked_targets_parameter(parser)


###############################################################################
# update cmd
###############################################################################

COPYRIGHT = 'Copyright \\(c\\)'
HOLDER = 'The Bitcoin Core developers'
UPDATEABLE_LINE_COMPILED = re.compile(' '.join([COPYRIGHT, YEAR_RANGE,
                                                HOLDER]))


class UpdateCmd(CopyrightHeaderCmd):
    """
    'update' subcommand class.
    """
    def __init__(self, settings):
        settings.json = False
        settings.jobs = 1
        super().__init__(settings)
        self.title = "Copyright Header Update"

    def _updatable_copyright_line(self, file_lines):
        index = 0
        for line in file_lines:
            if UPDATEABLE_LINE_COMPILED.search(line) is not None:
                return index, line
            index = index + 1
        return None, None

    def _year_range_to_str(self, start_year, end_year):
        if start_year == end_year:
            return start_year
        return "%s-%s" % (start_year, end_year)

    def _updated_copyright_line(self, line, last_git_change_year):
        match = YEAR_RANGE_COMPILED.search(line)
        start_year = match.group('start_year')
        end_year = match.group('end_year')
        if end_year is None:
            end_year = start_year
        if end_year == last_git_change_year:
            return line
        new_range_str = self._year_range_to_str(start_year,
                                                last_git_change_year)
        return YEAR_RANGE_COMPILED.sub(new_range_str, line)

    def _update_header(self, file_info):
        file_lines = file_info['content'].split('\n')
        index, line = self._updatable_copyright_line(file_lines)
        if line is None:
            return file_info['content']
        last_git_change_year = file_info['change_years'][1]
        new_line = self._updated_copyright_line(line, last_git_change_year)
        if line == new_line:
            return file_info['content']
        file_lines[index] = new_line
        return'\n'.join(file_lines)

    def _compute_file_infos(self):
        super()._compute_file_infos()
        if not self.silent:
            print("Querying git for file update history...")
        for file_info in self.file_infos:
            file_path = GitFilePath(file_info['file_path'])
            file_info['change_years'] = file_path.change_year_range()
            updated = self._update_header(file_info)
            file_info['updated'] = updated != file_info['content']
            file_info.set_write_content(updated)
        if not self.silent:
            print("Done.")

    def _exec(self):
        super()._exec()
        self.file_infos.write_all()
        if not self.silent:
            print("Updated copyright header years in %d files." %
                  sum(1 for f in self.file_infos if f['updated']))

    def _output(self, results):
        return None


def add_update_cmd(subparsers):
    update_help = ('Updates the end year of the copyright headers of '
                   '"The Bitcoin Core developers" in files amongst the '
                   'selected targets which have been changed more recently '
                   'than the year that is listed.')
    parser = subparsers.add_parser('update', help=update_help)
    parser.set_defaults(cmd=lambda o: UpdateCmd(o))
    add_git_tracked_targets_parameter(parser)


###############################################################################
# insert cmd
###############################################################################

ALL_EXTS = [s[1:] for s in APPLIES_TO if s[0] is '*']

SCRIPT_HEADER = ("# Copyright (c) %s The Bitcoin Core developers\n"
                 "# Distributed under the MIT software license, see the "
                 "accompanying\n# file COPYING or http://www.opensource.org/"
                 "licenses/mit-license.php.\n")

SCRIPT_EXTS = ['.py', '.sh', '.am', '.include']

M4_HEADER = ("dnl Copyright (c) %s The Bitcoin Core developers\n"
             "dnl Distributed under the MIT software license, see the "
             "accompanying\ndnl file COPYING or http://www.opensource.org/"
             "licenses/mit-license.php.\n")

M4_EXTS = ['.m4']

CPP_HEADER = ("// Copyright (c) %s The Bitcoin Core developers\n// "
              "Distributed under the MIT software license, see the "
              "accompanying\n// file COPYING or http://www.opensource.org/"
              "licenses/mit-license.php.\n")

CPP_EXTS = ['.h', '.cpp']

assert set(ALL_EXTS) == set(SCRIPT_EXTS + M4_EXTS + CPP_EXTS)


class InsertCmd(CopyrightHeaderCmd):
    """
    'insert' subcommand class.
    """
    def __init__(self, settings):
        settings.json = False
        settings.jobs = 1
        super().__init__(settings)
        self.title = "Copyright Header Insert"

    def _year_range_string(self, start_year, end_year):
        if start_year == end_year:
            return start_year
        return "%s-%s" % (start_year, end_year)

    def _header(self, file_path, start_year, end_year):
        file_path.assert_extension_is_one_of(ALL_EXTS)
        year_range = self._year_range_string(start_year, end_year)
        if file_path.extension_is_one_of(SCRIPT_EXTS):
            return SCRIPT_HEADER % year_range
        if file_path.extension_is_one_of(M4_EXTS):
            return CPP_HEADER % year_range
        else:
            return M4_HEADER % year_range

    def _content_with_header(self, file_info):
        file_path = GitFilePath(file_info['file_path'])
        start_year, end_year = file_path.change_year_range()
        header = self._header(file_path, start_year, end_year)
        insertion_point = (file_info['content'].find('\n') + 1 if
                           file_info['shebang'] else 0)
        content = file_info['content']
        return content[:insertion_point] + header + content[insertion_point:]

    def _compute_file_infos(self):
        super()._compute_file_infos()
        for file_info in self.file_infos:
            header_needed = (file_info['hdr_expected'] and not
                             file_info['has_header'])
            to_write = (self._content_with_header(file_info) if
                        header_needed else file_info['content'])
            file_info['hdr_added'] = header_needed
            file_info.set_write_content(to_write)

    def _exec(self):
        super()._exec()
        self.file_infos.write_all()
        if not self.silent:
            print("Added copyright header to %d files." %
                  sum(1 for f in self.file_infos if f['hdr_added']))

    def _output(self, results):
        return None


def add_insert_cmd(subparsers):
    insert_help = ('Inserts a correct MIT-licence copyright header for "The '
                   'Bitcoin Core developers" at the top of files amongst the '
                   'selected targets where the header is expected but not '
                   'currently found.')
    parser = subparsers.add_parser('insert', help=insert_help)
    parser.set_defaults(cmd=lambda o: InsertCmd(o))
    add_git_tracked_targets_parameter(parser)


###############################################################################
# UI
###############################################################################

if __name__ == "__main__":
    description = ("utilities for managing copyright headers of 'The Bitcoin "
                   "Core developers' in repository source files")
    parser = argparse.ArgumentParser(description=description)
    subparsers = parser.add_subparsers()
    add_report_cmd(subparsers)
    add_check_cmd(subparsers)
    add_update_cmd(subparsers)
    add_insert_cmd(subparsers)
    settings = parser.parse_args()
    if not hasattr(settings, "cmd"):
        parser.print_help()
        sys.exit("*** missing argument")
    settings.cmd(settings).run()
