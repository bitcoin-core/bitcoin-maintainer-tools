#!/usr/bin/env python3
'''
Script to parse git commit list, extract github issues to create a changelog in
text and json format.

Run this in the root directory of the repository.

This requires an up-to-date checkout of https://github.com/zw/bitcoin-gh-meta.git
in the parent directory, or environment variable `GHMETA`.

It takes a range of commits and a .json file of PRs to exclude, for
example if these are already backported in a minor release. This can be the pulls.json
generated from a previous release.

Example usage:

    ../maintainer-tools/list-pulls.py v0.18.0 0.19 relnot/pulls-exclude.json > relnot/pulls.md

The output of this script is a first draft based on rough heuristics, and
likely needs to be extensively manually edited before ending up in the release
notes.
'''
# W.J. van der Laan 2017-2019 (license: MIT)
import subprocess
import re
import json
import time
import sys, os
from collections import namedtuple, defaultdict

# == Global environment ==
GIT = os.getenv('GIT', 'git')
GHMETA = os.getenv('GHMETA', '../bitcoin-gh-meta')

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
    ({'wallet'},
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
    ('wallet', 'Wallet', True),
]

def remove_last_if_empty(l):
    '''Remove empty last member of list'''
    if l[-1]==b'' or l[-1]=='':
        return l[0:-1]
    else:
        return l

ref_from = sys.argv[1] # 'v0.10.0rc1'
ref_to = sys.argv[2] # 'master'

# read exclude file
exclude_pulls = set()

if len(sys.argv) >= 4:
    exclude_file = sys.argv[3]
    try:
        with open(exclude_file, 'r') as f:
            d = json.load(f)
            exclude_pulls = set(p['id'] for p in d['pulls'])
        print('Excluding ', exclude_pulls)
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
        m = re.match('Github-Pull: #?(\d+)', line, re.I)
        if m:
            retval.pull = int(m.group(1))
        m = re.match('Rebased-From: (.*)', line, re.I)
        if m:
            retval.rebased_from = m.group(1).strip().split()
    if retval.pull is not None:
        return retval
    else:
        return None

# traverse merge commits
pulls = {}
PullData = namedtuple('PullData', ['id', 'merge', 'commits', 'index'])
orphans = set(commits)
pullreq_re = re.compile('#([0-9]+)')
for c in commit_data.values():
    # is merge commit
    if len(c.parents)>1:
        assert(len(c.parents)==2)
        match = pullreq_re.search(c.title)
        if match: # merges a pull request
            if c.sha in orphans:
                orphans.remove(c.sha)
            #print('removing ', c.sha)
            sub_commits = subprocess.check_output([GIT, 'rev-list', c.parents[0]+'..'+c.parents[1]])
            sub_commits = sub_commits.decode()
            sub_commits = set(sub_commits.rstrip().splitlines())
            pull = int(match.group(1))

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

                    if not sub_pulls and 'backport' in c.message.lower():
                        # TODO could check pull label instead, but we don't know that here yet
                        print('#%i: Merge commit message contains \'backport\' but there are no sub-pulls' % (pull))

                    for (sub_pull, sub_pull_commits) in sub_pulls.items():
                        pulls[sub_pull] = PullData(sub_pull, sub_pull_commits[0], sub_pull_commits, index)

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

def guess_category_from_labels(labels):
    '''
    Guess category for a PR from github labels.
    '''
    labels = [l.lower() for l in labels]
    for (label_list, category) in LABEL_MAPPING:
        for l in labels:
            if l in label_list:
                return category
    return UNCATEGORIZED

def get_category(labels, message):
    '''
    Guess category for a PR from labels and message.
    Strip category from message.
    '''
    category = guess_category_from_labels(labels)
    message = message.strip()

    for (prefix, p_category, do_strip) in PREFIXES:
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
    filename = '%s/issues/%ixx/%i.json' % (GHMETA, pull/100, pull)
    try:
        with open(filename, 'r') as f:
            data0 = json.load(f)
    except IOError as e:
        data0 = None

    filename = '%s/issues/%ixx/%i-PR.json' % (GHMETA, pull/100, pull)
    try:
        with open(filename, 'r') as f:
            data1 = json.load(f)
    except IOError as e:
        data1 = {'title': '{Not found}', 'user': {'login':'unknown'}}

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
    category, message = get_category(labels, message)
    data1['title'] = message

    per_category[category].append((pull, message, author))
    pull_labels[pull] = labels 
    pull_meta[pull] = data1
    
for _,category in LABEL_MAPPING:
    if not per_category[category]:
        continue
    print('### %s' % category)
    for dd in per_category[category]:
        print('- #%i %s (%s)' % dd)
    print()

if per_category[UNCATEGORIZED]:
    print('### %s' % UNCATEGORIZED)
    for dd in per_category[UNCATEGORIZED]:
        print('- #%i %s (%s) (labels: %s)' % (dd+(pull_labels[dd[0]],)))
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
            {'id': pd.id,
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

