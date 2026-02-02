#!/usr/bin/env python3
'''
Script to parse git commit list, extract github issues to create a changelog in
text and JSON format.

Run this in the root directory of the repository.

This requires an up-to-date checkout of https://github.com/zw/bitcoin-gh-meta.git
in the parent directory, or environment variable `GHMETA`.

It takes a range of commits and a .json file of PRs to exclude, for
example if these are already backported in a minor release. This can be the pulls.json
generated from a previous release.

Example usage:

    ../maintainer-tools/list-pulls.py v28.0 29 relnot/pulls-exclude.json > relnot/pulls.md

The output of this script is a first draft based on rough heuristics, and
likely needs to be extensively manually edited before ending up in the release
notes.
'''
# W.J. van der Laan 2017-2021
# The Bitcoin Core developers 2017-2021, 2025
# SPDX-License-Identifier: MIT
import subprocess
import re
import json
import sys, os
from collections import namedtuple, defaultdict

# == Global environment ==
GIT = os.getenv('GIT', 'git')
GHMETA = os.getenv('GHMETA', '../bitcoin-gh-meta')
DEFAULT_REPO = os.getenv('DEFAULT_REPO', 'bitcoin/bitcoin')

# == Label to category mapping ==
# See: https://github.com/bitcoin/bitcoin/labels
# this is priority ordering: the first label to be matched determines the
# category it is slotted to
# TODO: simply create titles for combinations of mappings, and leave it up to release note writer
# which one to choose? this automatic choosing based on "priority" kind of sucks.
LABEL_MAPPING = (
    # Consensus, mining and policy changes should come first
    ({'consensus'},
        'Consensus'),
    ({'tx fees and policy'},
        'Policy'),
    ({'mining'},
        'Mining'),
    # Privacy changes
    ({'privacy'},
        'Privacy'),
    # Backends
    ({'mempool', 'block storage', 'utxo db and indexes', 'validation'},
        'Block and transaction handling'),
    ({'p2p'},
        'P2P protocol and network code'),
    ({'wallet', 'descriptors'},
        'Wallet'),
    # Frontends
    ({'rpc/rest/zmq'},
        'RPC and other APIs'),
    ({'gui'},
        'GUI'),
    # Frameworks, infrastructure, building etcetera
    ({'build system'},
        'Build system'),
    ({'tests'},
        'Tests and QA'),
    ({'utils/log/libs', 'scripts and tools', 'upstream', 'utils and libraries'},
        'Miscellaneous'),
    # Documentation-only
    ({'docs and output', 'docs'},
        'Documentation'),
    ({'windows', 'unix', 'macos'},
        'Platform support'),
    # Ignore everything below this for pull list
    ({'refactoring'},
        'Refactoring'),  # Ignore pure refactoring for pull list
    ({'backport'},
        'Backports'),  # Ignore pure backports for pull list
)
UNCATEGORIZED = 'Uncategorized'

# == PR title prefix to category mapping ==
# this takes precedence over the above label mapping 
# handle (in all cases, ignoring including leading and trailing ' ')
# SPECIFY IN LOWERCASE
# set do_strip as False if the prefix adds information beyond what the category provides!
# '[prefix]:' '[prefix]' 'prefix:'
PREFIXES = [ 
    # (prefix, category, do_strip)
    ('bench', 'Tests and QA', False),
    ('build', 'Build system', True),
    ('ci', 'Tests and QA', False),
    ('cli', 'RPC and other APIs', False),
    ('consensus', 'Consensus', True),
    ('contrib', 'Miscellaneous', False),
    ('depends', 'Build system', True),
    ('doc', 'Documentation', True),
    ('docs', 'Documentation', True),
    ('gitian', 'Build system', False),
    ('gui', 'GUI', True),
    ('lint', 'Miscellaneous', False),
    ('logging', 'Miscellaneous', False),
    ('mempool', 'Block and transaction handling', True),
    ('txmempool', 'Block and transaction handling', True),
    ('moveonly', 'Refactoring', False),
    ('net', 'P2P protocol and network code', True),
    ('nit', 'Refactoring', True),
    ('p2p', 'P2P protocol and network code', True),
    ('policy', 'Policy', True),
    ('qa', 'Tests and QA', True),
    ('qt', 'GUI', True),
    ('refactor', 'Refactoring', True),
    ('release', 'Build system', False),
    ('rest', 'RPC and other APIs', False),
    ('rpc', 'RPC and other APIs', True),
    ('scripted-diff', 'Refactoring', False),
    ('script', 'Miscellaneous', False), # !!! this is unclear, 'script' could also be block/tx handling or even consensus
    ('scripts', 'Miscellaneous', False),
    ('shutdown', 'Miscellaneous', False),
    ('tests', 'Tests and QA', True),
    ('test', 'Tests and QA', True),
    ('travis', 'Tests and QA', False),
    ('trivial', 'Refactoring', True),
    ('ui', 'GUI', True),
    ('util', 'Miscellaneous', False),
    ('utils', 'Miscellaneous', False),
    ('validation', 'Block and transaction handling', True),
    ('wallet', 'Wallet', True),
]

# Per-repository information
REPO_INFO = {
    'bitcoin/bitcoin': {
        'label_mapping': LABEL_MAPPING,
        'prefixes': PREFIXES,
        'default_category': UNCATEGORIZED,
        'ghmeta': GHMETA,
    },
    # For now, GUI repository pulls are automatically categorized into the GUI category.
    'bitcoin-core/gui': {
        'label_mapping': (),
        'prefixes': [],
        'default_category': 'GUI',
        'ghmeta': None,
    },
}

# == Utilities ==

def remove_last_if_empty(l):
    '''Remove empty last member of list'''
    if l[-1]==b'' or l[-1]=='':
        return l[0:-1]
    else:
        return l

# Valid chars in github names
VALIDNAMECHARS = '[0-9a-zA-Z\-_]'
# For parsing owner/repo#id
FQID_RE = re.compile('^(' + VALIDNAMECHARS + '+)/(' + VALIDNAMECHARS + '+)#([0-9]+)$')
# For parsing non-qualified #id
PR_RE = re.compile('^#?([0-9]+)$')

class FQId:
    '''Fully qualified PR id.'''
    def __init__(self, owner: str, repo: str, pr: int):
        self.owner = owner
        self.repo = repo
        self.pr = pr

    @property
    def _key(self):
        return (self.owner, self.repo, self.pr)

    def __eq__(self, o):
        return self._key == o._key

    def __lt__(self, o):
        return self._key < o._key

    def __hash__(self):
        return hash(self._key)

    def __str__(self):
        return f'{self.owner}/{self.repo}#{self.pr}'

    def __repr__(self):
        return f'FQId({repr(self.owner)}, {repr(self.repo)}, {repr(self.pr)})'

    @classmethod
    def parse(cls, pull, default_repo):
        '''Return FQId from 'owner/repo#id' or '#id' or 'id' string.'''
        m = FQID_RE.match(pull)
        if m:
            return cls(m.group(1), m.group(2), int(m.group(3)))
        m = PR_RE.match(pull)
        if m:
            (owner, repo) = default_repo.split('/')
            return cls(owner, repo, int(m.group(1)))
        raise ValueError(f'Cannot parse {pull} as PR specification.')

def tests():
    '''Quick internal sanity tests.'''
    assert(FQId.parse('bitcoin/bitcoin#1234', 'bitcoin/bitcoin') == FQId('bitcoin', 'bitcoin', 1234))
    assert(FQId.parse('bitcoin-core/gui#1235', 'bitcoin/bitcoin') == FQId('bitcoin-core', 'gui', 1235))
    assert(FQId.parse('#1236', 'bitcoin/bitcoin') == FQId('bitcoin', 'bitcoin', 1236))
    assert(FQId.parse('1237', 'bitcoin/bitcoin') == FQId('bitcoin', 'bitcoin', 1237))
    assert(str(FQId('bitcoin', 'bitcoin', 1239)) == 'bitcoin/bitcoin#1239')
    assert(FQId('bitcoin', 'bitcoin', 1239) < FQId('bitcoin', 'bitcoin', 1240))
    assert(not (FQId('bitcoin', 'bitcoin', 1240) < FQId('bitcoin', 'bitcoin', 1239)))
    assert(FQId('bitcoin', 'bitcoin', 1240) < FQId('bitcoin-core', 'gui', 1239))
    assert(not (FQId('bitcoin-core', 'gui', 1239) < FQId('bitcoin', 'bitcoin', 1240)))

# == Main program ==
tests()
ref_from = sys.argv[1] # 'v29.1rc1'
ref_to = sys.argv[2] # 'master'

# read exclude file
exclude_pulls = set()

if len(sys.argv) >= 4:
    exclude_file = sys.argv[3]
    try:
        with open(exclude_file, 'r') as f:
            d = json.load(f)
            exclude_pulls = set(FQId.parse(str(p['id']), DEFAULT_REPO) for p in d['pulls'])
        print(f'Excluding {", ".join(str(p) for p in exclude_pulls)}')
        print()
    except IOError as e:
        print(f'Unable to read exclude file {exclude_file}', file=sys.stderr)
        exit(1)

# set of all commits
commits = subprocess.check_output([GIT, 'rev-list', '--reverse', '--topo-order', ref_from+'..'+ref_to])
commits = commits.decode()
commits = remove_last_if_empty(commits.splitlines())
commits_list = commits
commits = set(commits)

CommitData = namedtuple('CommitData', ['sha', 'message', 'title', 'parents'])
commit_data = {}

# collect data
for commit in commits:
    info = subprocess.check_output([GIT, 'show', '-s', '--format=%B%x00%P', commit])
    info = info.decode()
    (message, parents) = info.split('\0')
    title = message.rstrip().splitlines()[0]
    parents = parents.rstrip().split(' ')
    commit_data[commit] = CommitData(commit, message, title, parents)

class CommitMetaData:
    pull = None
    rebased_from = None

    def __repr__(self):
        return 'CommitMetadata(pull=%s,rebased_from=%s)' % (self.pull,self.rebased_from)

def parse_commit_message(msg):
    '''
    Parse backport commit message.
    '''
    retval = CommitMetaData()
    for line in msg.splitlines():
        if line.startswith('Github-Pull:'):
            param = line[12:].strip()
            if param.startswith('#'): # compensate for incorrect #bitcoin-core/gui#148
                param = param[1:]
            retval.pull = FQId.parse(param, DEFAULT_REPO)
        if line.startswith('Rebased-From:'):
            retval.rebased_from = line[13:].strip().split()
    if retval.pull is not None:
        return retval
    else:
        return None

# traverse merge commits
pulls = {}
PullData = namedtuple('PullData', ['id', 'merge', 'commits', 'index'])
orphans = set(commits)
MERGE_RE = re.compile('Merge (.*?):')
for c in commit_data.values():
    # is merge commit
    if len(c.parents)>1:
        assert(len(c.parents)==2)
        match = MERGE_RE.match(c.title)
        if match: # merges a pull request
            if c.sha in orphans:
                orphans.remove(c.sha)
            #print('removing ', c.sha)
            sub_commits = subprocess.check_output([GIT, 'rev-list', c.parents[0]+'..'+c.parents[1]])
            sub_commits = sub_commits.decode()
            sub_commits = set(sub_commits.rstrip().splitlines())
            pull = FQId.parse(match.group(1), DEFAULT_REPO)

            # remove commits that are not in the global list
            sub_commits = sub_commits.intersection(commits)
            for cs in sub_commits:
                if cs in orphans:
                    orphans.remove(cs)

            if not pull in exclude_pulls:
                # if any sub-commits left, report them
                if sub_commits:
                    # only report pull if any new commit went into the release
                    index = commits_list.index(c.sha)
                    pulls[pull] = PullData(pull, c.sha, sub_commits, index)

                    # look up commits and see if they point to master pulls
                    # (=backport pull)
                    # add those too
                    sub_pulls = defaultdict(list)
                    for cid in sub_commits:
                        md = parse_commit_message(commit_data[cid].message)
                        if md:
                            sub_pulls[md.pull].append(cid)

                    if not sub_pulls and 'backport' in c.title.lower():
                        # just information for manual checking
                        print(f'{pull}: Merge PR title {repr(c.title)} contains \'backport\' but there are no sub-pulls')

                    for (sub_pull, sub_pull_commits) in sub_pulls.items():
                        pulls[sub_pull] = PullData(sub_pull, sub_pull_commits[0], sub_pull_commits, index)
        else:
            print(f'{c.sha}: Merge commit does not merge a PR: {c.title}')

# Extract remaining pull numbers from orphans, if they're backports
for o in set(orphans):
    c = commit_data[o]
    md = parse_commit_message(commit_data[o].message)
    if md:
        pulls[md.pull] = PullData(md.pull, c.sha, [], commits_list.index(c.sha))
        orphans.remove(o)

# Sort by index in commits list
# This results in approximately chronological order
pulls_order = list(pulls.values())
pulls_order.sort(key=lambda p:p.index)
pulls_order = [p.id for p in pulls_order]
# pulls_order = sorted(pulls.keys())

def guess_category_from_labels(repo_info, labels):
    '''
    Guess category for a PR from github labels.
    '''
    labels = [l.lower() for l in labels]
    for (label_list, category) in repo_info['label_mapping']:
        for l in labels:
            if l in label_list:
                return category
    return repo_info['default_category']

def get_category(repo_info, labels, message):
    '''
    Guess category for a PR from repository, labels and message prefixes.
    Strip category from message.
    '''
    category = guess_category_from_labels(repo_info, labels)
    message = message.strip()

    for (prefix, p_category, do_strip) in repo_info['prefixes']:
        for variant in [('[' + prefix + ']:'), ('[' + prefix + ']'), (prefix + ':')]:
            if message.lower().startswith(variant):
                category = p_category
                message = message[len(variant):].lstrip()
                if not do_strip: # if strip is not requested, re-add prefix in sanitized way
                    message = prefix + ': ' + message.capitalize()

    return (category, message)

pull_meta = {}
pull_labels = {}
per_category = defaultdict(list)
for pull in pulls_order:
    repo_info = REPO_INFO[f'{pull.owner}/{pull.repo}']

    # Find github metadata for PR, if available
    data0 = None
    data1 = {'title': '{Not found}', 'user': {'login':'unknown'}}
    if repo_info['ghmeta'] is not None:
        filename = f'{repo_info["ghmeta"]}/issues/{pull.pr//100}xx/{pull.pr}.json'
        try:
            with open(filename, 'r') as f:
                data0 = json.load(f)
        except IOError as e:
            pass

        filename = f'{repo_info["ghmeta"]}/issues/{pull.pr//100}xx/{pull.pr}-PR.json'
        try:
            with open(filename, 'r') as f:
                data1 = json.load(f)
        except IOError as e:
            pass

    message = data1['title']
    author = data1['user']['login']
    if data0 is not None:
        labels = [l['name'] for l in data0['labels']]
    else:
        labels = ['Missing']

    # nightmarish UTF tweaking to fix broken output of export script
    message = message.encode('ISO-8859-1', errors='replace').decode(errors='replace')

    # consistent ellipsis
    message = message.replace('...', '…')
    # no '.' at end
    if message.endswith('.'):
        message = message[0:-1]

    # determine category and new message from message
    category, message = get_category(repo_info, labels, message)
    data1['title'] = message

    per_category[category].append((pull, message, author))
    pull_labels[pull] = labels 
    pull_meta[pull] = data1
    
for _,category in LABEL_MAPPING:
    if not per_category[category]:
        continue
    print('### %s' % category)
    for dd in per_category[category]:
        print(f'- {dd[0]} {dd[1]} ({dd[2]})')
    print()

if per_category[UNCATEGORIZED]:
    print('### %s' % UNCATEGORIZED)
    for dd in per_category[UNCATEGORIZED]:
        print(f'- {dd[0]} {dd[1]} ({dd[2]}) (labels: {pull_labels[dd[0]]})')
    print()

print('### Orphan commits')
for o in orphans:
    c = commit_data[o]
    print('- `%s` %s' % (o[0:7], c.title))

# write to json structure for postprocessing
commits_d = []
for c in commits_list:
    commits_d.append(commit_data[c])

pulls_d = []
for pull in sorted(pulls.keys()):
    pd = pulls[pull]
    pulls_d.append(
            {'id': str(pd.id),
            'merge': pd.merge,
            'commits': list(pd.commits),
            'meta': pull_meta[pd.id]})

data_out = {
    'commits': commits_d,
    'pulls': pulls_d,
    'orphans': list(orphans),
}

with open('pulls.json','w') as f:
    json.dump(data_out, f, sort_keys=True,
                           indent=4, separators=(',', ': '))
