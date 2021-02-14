#!/usr/bin/env python3
'''
Watch sorted github notifications from the terminal.
'''
import argparse
from collections import namedtuple
import datetime
import json
import os
import re
import shutil
import sys
import subprocess
import webbrowser

from github import Github, GithubObject

from ghmeta import GhMeta
from termlib.input import Key
from termlib.tableprinter import Column, TablePrinter
from termlib.attr import Attr

DEFAULT_CONFIG = {
    'ghbase': 'https://github.com/',
    'ghtoken': '',

    # This specifies the action to invoke when clicking an issue number.
    # the default setting will invoke the operating system default browser.
    'browser': None,
    # Alternatively, it is possible to specify a command
    #'browser': ['firefox', '--new-tab'],

    # Repository with github metadata mirror (to get label data)
    'meta': {'bitcoin/bitcoin': '/path/to/bitcoin-gh-meta'},

    # Interval in seconds for an automatic update (git pull) of github metadata mirror, if greater than 0.
    'auto_update': 0,

    # Whether to enable ordering of notifications by {reason, time}.
    'sort_notifications': False,

    # Label priorities; the higher in this list, the higher the priority.
    # When a PR or issue has multiple labels, the one with the highest priority will be
    # shown. This is pretty arbitary, roughly going from specific to aspecific,
    # and not a value judgement with regard to importance of components.
    'label_prio': {'bitcoin/bitcoin': [
      'Consensus',
      'Mining',
      'Mempool',
      'TX fees and policy',
      'UTXO Db and Indexes',
      'Validation',
      'P2P',
      'Wallet',
      'RPC/REST/ZMQ',
      'Build system',
      'Scripts and tools',
      'Settings',
      'Utils/log/libs',
      'Tests',
      'GUI',
      'Docs',
      'Descriptors',
      'PSBT',
      'Privacy',
      'Resource usage',
      'Block storage',
      'Data corruption',
      'Interfaces',
      'Refactoring',
    ]},
}

# Priority list of notification reasons, from highest to lowest
REASON_PRIO = ["assign", "review_requested", "mention", "author", "comment", "invitation",
               "manual", "team_mention", "security_alert", "state_change", "subscribed"]

# A clickable link UI element
ButtonInfo = namedtuple('ButtonInfo', ['x0', 'y0', 'x1', 'y1', 'url'])

class Theme:
    '''
    Application theming.
    '''
    # Default attribute for row
    HEADER = Attr.BOLD + Attr.REVERSE
    ROW = ''
    # Attribute for timestamp
    DATETIME = '' # Attr.fg_hex('#ffffff')

    # Attributes for PR/issue states
    REF = {
        'unknown': '',
        'open':   Attr.fg_hex('#3fb950') + Attr.bg_hex('#12221d'),
        'closed': Attr.fg_hex('#f85149') + Attr.bg_hex('#22141a'),
        'merged': Attr.fg_hex('#a371f7') + Attr.bg_hex('#1f1d2f'),
    }

    # Attributes for notification reasons
    # see https://docs.github.com/en/rest/reference/activity#notification-reasons
    REASON_GLYPHS = {
        'assign':           (Attr.fg_hex('#808080'), 'as'),
        'author':           (Attr.fg_hex('#c000ff'), 'au'),
        'comment':          (Attr.fg_hex('#808080'), 'co'),
        'invitation':       (Attr.fg_hex('#808080'), 'in'),
        'manual':           (Attr.fg_hex('#808080'), 'ma'),
        'mention':          (Attr.fg_hex('#ff00ff'), 'me'),
        'review_requested': (Attr.fg_hex('#808080'), 'rr'),
        'security_alert':   (Attr.fg_hex('#808080'), 'sa'),
        'state_change':     (Attr.fg_hex('#808080'), 'sc'),
        'subscribed':       (Attr.fg_hex('#3c3c3c'), 'su'),
        'team_mention':     (Attr.fg_hex('#808080'), 'tm'),
    }
    UNK_REASON = (ROW, '??')

def pick_label(label_prio, repo, labels):
    '''
    Pick the most appropriate (highest priority) label to show.
    '''
    try:
        label_prio = label_prio[repo]
    except KeyError: # if no specific prioritization for this repo, return the first label
        if len(labels) > 0:
            return labels[0]
        else:
            return None

    res = None
    res_prio = len(label_prio) + 1
    for label in labels:
        try:
            prio = -label_prio.index(label['name'])
        except ValueError:
            prio = -len(label_prio)

        if res is None or prio > res_prio:
            res = label
            res_prio = prio

    return res

def parse_args() -> argparse.Namespace:
    '''Parse command line arguments.'''
    parser = argparse.ArgumentParser(description='Display github notifications')

    parser.add_argument('--exclude-reasons', '-x', help='Reasons to exclude (comma-separated) from: assign, author, comment, invitation, manual, mention, review_requested, security_alert, state_change, subscribed, team_mention)')
    parser.add_argument('--all', '-a', action='store_const', const=True, default=False, help='Show all notifications, also those that are read')
    parser.add_argument('--days', '-d', type=int, default=7, help='Number of days to look back (default: 7)')
    parser.add_argument('--refresh-time', '-r', type=int, default=600, help='Refresh time in seconds in interactive mode (default: 600)')
    parser.add_argument('--default-config', action='store_const', const=True, default=False, help='Generate a default configuration file in ~/.config/ghwatch')
    parser.add_argument('--sort', '-s', action='store_true', default=None, help="Sort notifications by reasons (and then time). Overrides 'sort_notifications' in the configuration file")
    parser.add_argument('--no-sort', dest='sort', action='store_false', help="Don't sort notifications. Overrides 'sort_notifications' in the configuration file")

    return parser.parse_args()

config_dir: str = f'{os.path.expanduser("~")}/.config/ghwatch'
config_file: str = f'{config_dir}/ghwatch.conf'

def parse_config_file(generate=False):
    config = DEFAULT_CONFIG
    if generate:
        os.makedirs(config_dir, exist_ok=True)
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=4)
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            # TODO: merge with default config instead of overwrite here
            config = json.load(f)
    else:
        print(f'No configuration file {config_file}, use --default-config to generate a default one.', file=sys.stderr)
        sys.exit(1)
    return config

def get_html_url(ghbase, rec):
    '''
    Get the browser URL for a notification object.

    I think the "proper" way to do this would be to fetch rec.subject.url and get
    'html_url' from the returned object. But to avoid another roundtrip to github,
    this implements the logic locally.
    '''
    m = re.match('.*\/([0-9a-f]+)$', rec.subject.url)
    if not m:
        return None
    idx = m.group(1)
    if rec.subject.type == 'PullRequest':
        return f'{ghbase}{rec.repository.full_name}/pull/{idx}'
    if rec.subject.type == 'Issue':
        return f'{ghbase}{rec.repository.full_name}/issues/{idx}'
    elif rec.subject.type == 'Commit':
        return f'{ghbase}{rec.repository.full_name}/commit/{idx}'
    else: # TODO: releases and other things
        return None

def priority_sort_key(item):
    return (-REASON_PRIO.index(item.reason), item.updated_at)

def draw():
    sys.stdout.write(Attr.CLEAR)
    pr.print_header(Theme.HEADER)
    issue_column = pr.column_info(4)

    # TODO:
    # "Notifications are optimized for polling with the Last-Modified header. If
    # there are no new notifications, you will see a 304 Not Modified response,
    # leaving your current rate limit untouched. There is an X-Poll-Interval header
    # that specifies how often (in seconds) you are allowed to poll. In times of
    # high server load, the time may increase. Please obey the header."

    since = datetime.datetime.utcnow() - datetime.timedelta(days=args.days)
    row = 0
    get_all = True if args.all else GithubObject.NotSet
    buttons = []
    issues = list(u.get_notifications(all=get_all, since=since))

    if sort_notifications:
        issues.sort(key=priority_sort_key, reverse=True)

    for rec in issues:
        if rec.reason in exclude_reasons:
            continue
        # rec.subject.type  : PullRequest, Issue, Commit
        # rec.reason : comment, subscribed, mention, author, state_change, review_requested see https://docs.github.com/en/rest/reference/activity#notification-reasons
        #   state_change is only for self-initiated state changed, not any monitored issue/PR
        if rec.subject.type in {'PullRequest', 'Issue'}:
            # PullRequest: https://api.github.com/repos/bitcoin-core/secp256k1/pulls/875
            # Issue: https://api.github.com/repos/bitcoin/bitcoin/issues/20935
            m = re.match('.*\/([0-9]+)$', rec.subject.url)
            issue = int(m.group(1))
            meta = ghmeta.get((rec.repository.full_name, issue))
            ref_str = str(issue)
        elif rec.subject.type == 'Commit':
            # Commit: https://api.github.com/repos/bitcoin/bitcoin/commits/54ce4fac80689621dcbcc76169b2b00b179ee743
            m = re.match('.*\/([0-9a-f]+)$', rec.subject.url)
            ref_str = m.group(1)
            issue = None
            meta = None
        else:
            # Release: https://api.github.com/repos/bitcoin-core/HWI/releases/34442950
            # RepositoryInvitation: ?
            if rec.subject.type not in {'Release', 'RepositoryInvitation'}: # Huh
                print(rec.subject.type, rec.subject.url)
                assert(False)
            issue = None
            meta = None

        label_t = (Theme.ROW, '')
        state = 'unknown'
        if meta is not None:
            label = pick_label(config['label_prio'], rec.repository.full_name, meta['labels'])
            if label is not None:
                label_t = (Attr.bg_hex(label['color']) + Attr.fg(0, 0, 0), label['name'])

            state = meta['state']
            if meta['pr'] is not None and meta['pr']['merged']:
                state = 'merged'

        pr.print_row([
            (Theme.DATETIME, rec.updated_at),
            Theme.REASON_GLYPHS.get(rec.reason, Theme.UNK_REASON),
            (Theme.ROW, rec.repository.full_name),
            (Theme.ROW, rec.subject.type),
            (Theme.REF.get(state, ''), ref_str),
            label_t,
            (Theme.ROW, rec.subject.title),
            ])

        buttons.append(ButtonInfo(
            x0 = issue_column.x,
            y0 = row + 1,
            x1 = issue_column.x + issue_column.width,
            y1 = row + 2,
            url = get_html_url(config['ghbase'], rec),
        ))

        row += 1
        if row == N:
            break

    return buttons

def handle_mouse_click(b, config):
    '''
    Handle click action on button element.
    '''
    if b.url is not None:
        if config['browser'] is None:
            webbrowser.open(b.url)
        else:
            subprocess.call(config['browser'] + [b.url], stdout = subprocess.PIPE, stderr = subprocess.PIPE)

def set_window_size():
    global pr, N

    (cols, rows) = shutil.get_terminal_size((80, 25))
    W = cols - 70
    N = rows - 2
    if W < 10 or N < 5:
        print('Terminal size too small')
        sys.exit(1)

    pr = TablePrinter(sys.stdout, Attr, [
        Column('date', 19),
        Column('r', 2),
        Column('repository', 24),
        Column('k', 1),
        Column('#', 5),
        Column('label', 12),
        Column('title', W),
    ])

def pull_repositories(config):
    '''
    Use subprocess to "git pull" the configured metadata-repositories.
    '''
    try:
        for repo, repo_path in config['meta'].items():
            subprocess.run(['git','pull'], check=True, cwd=repo_path, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(e.stderr.decode())
        raise

def main():
    global args, config, exclude_reasons, ghmeta, sort_notifications, u

    args = parse_args()
    config = parse_config_file(args.default_config)
    if not config['ghtoken']:
        print(f'A github token is required to be set as "ghtoken" in {config_file}', file=sys.stderr)
        exit(1)
    auto_update = config.get('auto_update', 0)
    ghmeta = GhMeta(config['meta'])
    g = Github(config['ghtoken'])
    u = g.get_user()

    exclude_reasons = set()
    if args.exclude_reasons:
        exclude_reasons.update(args.exclude_reasons.split(','))

    if args.sort is None:
        sort_notifications = config.get('sort_notifications', False)
    else:
        sort_notifications = args.sort

    if auto_update:
        pull_repositories(config)

    set_window_size()
    buttons = draw()

    Key.start(hide_cursor=True)

    refr_t = 0
    meta_t = 0
    try:
        while True:
            # auto-refresh periodically
            if refr_t >= args.refresh_time:
                buttons = draw()
                refr_t = 0

            # auto-update (git pull) metadata-repo(s)
            if auto_update and meta_t >= auto_update:
                meta_t = 0
                pull_repositories(config)

            # handle key input
            k = Key.get()
            if not k:
                Key.input_wait(1.0)
                refr_t += 1
                meta_t += 1
                continue
            if k == 'escape':
                break
            if k == 'mouse_click':
                # TODO: highlight button when clicked for a bit of feedback?
                for b in buttons:
                    if b.x0 <= Key.mouse_pos[0] < b.x1 and b.y0 <= Key.mouse_pos[1] < b.y1:
                        handle_mouse_click(b, config)
            if k == 'resize':
                set_window_size()
                buttons = draw()
    finally:
        Key.stop()

if __name__ == "__main__":
    main()
