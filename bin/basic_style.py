#!/usr/bin/env python3
# Copyright (c) 2017 The Bitcoin Core developers
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.

import re
import sys
import itertools
import argparse
import json

from framework.print.buffer import PrintBuffer
from framework.file.filter import FileFilter
from framework.file.info import FileInfo
from framework.file.style import FileStyleDiff, FileStyleScore
from framework.cmd.file_content import FileContentCmd
from framework.argparse.option import add_jobs_option
from framework.argparse.option import add_json_option
from framework.git.parameter import add_git_tracked_targets_parameter

###############################################################################
# style rules
###############################################################################

STYLE_RULES = [
    {'title':   'No tabstops',
     'applies': ['*.c', '*.cpp', '*.h', '*.py', '*.sh'],
     'regex':   '\t',
     'fix':     '    '},
    {'title':   'No trailing whitespace on a line',
     'applies': ['*.c', '*.cpp', '*.h', '*.py', '*.sh'],
     'regex':   ' \n',
     'fix':     '\n'},
    {'title':   'No more than three consecutive newlines',
     'applies': ['*.c', '*.cpp', '*.h', '*.py', '*.sh'],
     'regex':   '\n\n\n\n',
     'fix':     '\n\n\n'},
    {'title':   'Do not end a line with a semicolon',
     'applies': ['*.py'],
     'regex':   ';\n',
     'fix':     '\n'},
    {'title':   'Do not end a line with two semicolons',
     'applies': ['*.c', '*.cpp', '*.h'],
     'regex':   ';;\n',
     'fix':     ';\n'},
]

APPLIES_TO = list(set(itertools.chain(*[r['applies'] for r in STYLE_RULES])))


class BasicStyleRules(object):
    """
    Wrapping of the rules with helpers.
    """
    def __init__(self, repository):
        self.repository = repository
        self.rules = STYLE_RULES
        for rule in self:
            rule['regex_compiled'] = re.compile(rule['regex'])
            rule['filter'] = FileFilter()
            rule['filter'].append_include(rule['applies'],
                                          base_path=str(self.repository))

    def __iter__(self):
        return (rule for rule in self.rules)

    def rules_that_apply(self, file_path):
        return (rule for rule in self.rules if
                rule['filter'].evaluate(file_path))

    def rule_with_title(self, title):
        return next((rule for rule in self.rules if rule['title'] == title),
                    None)


###############################################################################
# file info
###############################################################################

class BasicStyleFileInfo(FileInfo):
    """
    Obtains and represents the information regarding a single file.
    """
    def __init__(self, repository, file_path, rules):
        super().__init__(repository, file_path)
        self.rules = rules
        self['rules_that_apply'] = list(self.rules.rules_that_apply(file_path))

    def _find_line_of_match(self, match):
        contents_before_match = self['content'][:match.start()]
        contents_after_match = self['content'][match.end() - 1:]
        line_start_char = contents_before_match.rfind('\n') + 1
        line_end_char = match.end() + contents_after_match.find('\n')
        return {'context':   self['content'][line_start_char:line_end_char],
                'number':    contents_before_match.count('\n') + 1,
                'character': match.start() - line_start_char + 1}

    def _find_issues(self, content):
        for rule in self['rules_that_apply']:
            matches = [match for match in
                       rule['regex_compiled'].finditer(content) if
                       match is not None]
            lines = [self._find_line_of_match(match) for match in matches]
            for line in lines:
                yield {'file_path':  self['file_path'],
                       'rule_title': rule['title'],
                       'line':       line}

    def _apply_fix(self, content, rule_title):
        # Multiple instances of a particular issue could be present. For
        # example, multiple spaces at the end of a line. So, we repeat the
        # search-and-replace until search matches are exhausted.
        fixed_content = content
        while True:
            rule = self.rules.rule_with_title(rule_title)
            fixed_content, subs = rule['regex_compiled'].subn(rule['fix'],
                                                              fixed_content)
            if subs == 0:
                break
        return fixed_content

    def _fix_content(self):
        fixed_content = self['content']
        issues = self['issues']
        # Multiple types of issues could be overlapping. For example, a tabstop
        # at the end of a line so the fix then creates whitespace at the end.
        # We repeat fix-up cycles until everything is cleared.
        while len(issues) > 0:
            fixed_content = self._apply_fix(fixed_content,
                                            issues[0]['rule_title'])
            issues = list(self._find_issues(fixed_content))
        return fixed_content

    def compute(self):
        self['issues'] = list(self._find_issues(self['content']))
        self['fixed_content'] = self._fix_content()
        self.set_write_content(self['fixed_content'])
        self.update(FileStyleDiff(self['content'], self['fixed_content']))
        self['matching'] = self['content'] == self['fixed_content']


###############################################################################
# cmd base class
###############################################################################

class BasicStyleCmd(FileContentCmd):
    """
    Common base class for the commands in this script.
    """
    def __init__(self, settings):
        settings.include_fnmatches = APPLIES_TO
        super().__init__(settings)
        self.rules = BasicStyleRules(self.repository)

    def _file_info_list(self):
        return [BasicStyleFileInfo(self.repository, f, self.rules) for f in
                self.files_targeted]


###############################################################################
# report cmd
###############################################################################

class ReportCmd(BasicStyleCmd):
    """
    'report' subcommand class.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.title = "Basic Style Report"

    def _exec(self):
        r = super()._exec()
        file_infos = self.file_infos
        r['jobs'] = self.jobs
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
        r['matching'] = sum(1 for f in file_infos if f['matching'])
        r['not_matching'] = sum(1 for f in file_infos if not f['matching'])

        all_issues = list(itertools.chain.from_iterable(
            file_info['issues'] for file_info in file_infos))

        r['rule_evaluation'] = {}
        for rule in self.rules:
            examined = sum(1 for f in file_infos if
                           rule['filter'].evaluate(f['file_path']))
            occurrence_count = len([f for f in all_issues if
                                    f['rule_title'] == rule['title']])
            file_count = len(set([f['file_path'] for f in all_issues if
                                  f['rule_title'] == rule['title']]))
            r['rule_evaluation'][rule['title']] = (
                {'extensions': rule['applies'], 'examined': examined,
                 'files': file_count, 'occurrences': occurrence_count})
        return r

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        b.add(super()._output(results))
        r = results
        b.add("%-32s %8.02fs\n" % ("Elapsed time:", r['elapsed_time']))
        b.separator()
        for title, evaluation in sorted(r['rule_evaluation'].items()):
            b.add('"%s":\n' % title)
            b.add('  %-30s %s\n' % ("Applies to:", evaluation['extensions']))
            b.add('  %-30s %8d\n' % ("Files examined:",
                                     evaluation['examined']))
            b.add('  %-30s %8d\n' % ("Occurrences of issue:",
                                     evaluation['occurrences']))
            b.add('  %-30s %8d\n\n' % ("Files with issue:",
                                       evaluation['files']))
        b.separator()
        b.add("%-32s %8d\n" % ("Files scoring 100%", r['matching']))
        b.add("%-32s %8d\n" % ("Files scoring <100%", r['not_matching']))
        b.separator()
        b.add("Overall scoring:\n\n")
        score = FileStyleScore(r['lines_before'], r['lines_added'],
                               r['lines_removed'], r['lines_unchanged'],
                               r['lines_after'])
        b.add(str(score))
        b.separator()
        return str(b)


def add_report_cmd(subparsers):
    report_help = ("Validates that the selected targets do not have basic "
                   "style issues, give a per-file report and returns a "
                   "non-zero shell status if there are any basic style issues "
                   "discovered.")
    parser = subparsers.add_parser('report', help=report_help)
    parser.set_defaults(cmd=lambda o: ReportCmd(o))
    add_jobs_option(parser)
    add_json_option(parser)
    add_git_tracked_targets_parameter(parser)


###############################################################################
# check cmd
###############################################################################

class CheckCmd(BasicStyleCmd):
    """
    'check' subcommand class.
    """
    def __init__(self, settings):
        super().__init__(settings)
        self.title = "Basic Style Check"

    def _exec(self):
        r = super()._exec()
        file_infos = self.file_infos
        r['issues'] = list(
            itertools.chain.from_iterable(f['issues'] for f in file_infos))
        return r

    def _output(self, results):
        if self.json:
            return super()._output(results)
        b = PrintBuffer()
        b.add(super()._output(results))
        r = results
        for issue in r['issues']:
            b.separator()
            b.add("An issue was found with ")
            b.add_red("%s\n" % issue['file_path'])
            b.add('Rule: "%s"\n\n' % issue['rule_title'])
            b.add('line %d:\n' % issue['line']['number'])
            b.add("%s" % issue['line']['context'])
            b.add(' ' * (issue['line']['character'] - 1))
            b.add_red("^\n")
        b.separator()
        if len(r['issues']) == 0:
            b.add_green("No style issues found!\n")
        else:
            b.add_red("These issues can be fixed automatically by running:\n")
            b.add("$ basic_style.py fix [target [target ...]]\n")
        b.separator()
        return str(b)

    def _shell_exit(self, results):
        return (0 if len(results['issues']) == 0 else "*** style issue found")


def add_check_cmd(subparsers):
    check_help = ("Validates that the selected targets do not have basic "
                  "style issues, give a per-file report and returns a "
                  "non-zero shell status if there are any basic style issues "
                  "discovered.")
    parser = subparsers.add_parser('check', help=check_help)
    parser.set_defaults(cmd=lambda o: CheckCmd(o))
    add_jobs_option(parser)
    add_json_option(parser)
    add_git_tracked_targets_parameter(parser)


###############################################################################
# fix cmd
###############################################################################

class FixCmd(BasicStyleCmd):
    """
    'fix' subcommand class.
    """
    def __init__(self, settings):
        settings.json = False
        super().__init__(settings)
        self.title = "Basic Style Fix"

    def _exec(self):
        super()._exec()
        self.file_infos.write_all()

    def _output(self, results):
        return None


def add_fix_cmd(subparsers):
    fix_help = ("Applies basic style fixes to the target files.")
    parser = subparsers.add_parser('fix', help=fix_help)
    parser.set_defaults(cmd=lambda o: FixCmd(o))
    add_jobs_option(parser)
    add_git_tracked_targets_parameter(parser)


###############################################################################
# UI
###############################################################################


if __name__ == "__main__":
    description = ("A utility for checking some basic style regexes against "
                   "the contents of source files in the repository. It "
                   "produces reports of style metrics and also can fix issues"
                   "with simple search-and-replace logic.")
    parser = argparse.ArgumentParser(description=description)
    subparsers = parser.add_subparsers()
    add_report_cmd(subparsers)
    add_check_cmd(subparsers)
    add_fix_cmd(subparsers)
    settings = parser.parse_args()
    if not hasattr(settings, "cmd"):
        parser.print_help()
        sys.exit("*** missing argument")
    settings.cmd(settings).run()
