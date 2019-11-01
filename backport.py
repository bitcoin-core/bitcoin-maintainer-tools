#!/usr/bin/env python3
'''
Script to do backports (pull ids listed in to_backport.txt or command line) in order of merge,
to minimize number of conflicts.
'''
import git
import re
import shlex
import subprocess
import os, sys

# External tools (can be overridden using environment)
GIT = os.getenv('GIT','git')
BASH = os.getenv('BASH','bash')
# Other configuration
SRCREPO = os.getenv('SRCREPO', '../bitcoin')

def ask_prompt(text):
    print(text,end=" ",file=sys.stderr)
    sys.stderr.flush()
    reply = sys.stdin.readline().rstrip()
    print("",file=sys.stderr)
    return reply

merge_re = re.compile('^Merge (#[0-9]+)')
if len(sys.argv) > 1:
    pulls = ['#'+x.strip() for x in sys.argv[1:]]
else:
    with open('to_backport.txt','r') as f:
        pulls = [x.strip() for x in f if x.strip()]

execute = True

pulls = set(pulls)
repo = git.Repo(SRCREPO)
head = repo.heads['master']

commit = head.commit
to_backport = []
while True:
    match = merge_re.match(commit.message)
    if match:
        prid = match.group(1)
        if prid in pulls:
            pulls.remove(prid)
            to_backport.append((prid, commit))
    if not pulls:
        break
    if not commit.parents:
        break
    commit = commit.parents[0]

if pulls:
    print('Missing: %s' % list(pulls))
    exit(1)

# Backport in reverse order
to_backport.reverse()

if execute:
    class Attr:
        hsh = "\x1b[90m"
        head = "\x1b[1;96m"
        head2 = "\x1b[94m"
        reset = "\x1b[0m"
else: # no colors if we're printing a bash script
    class Attr:
        head = ""
        head2 = ""
        reset = ""

if not execute:
    print('set -e')
for t in to_backport:
    msg = t[1].message.rstrip().splitlines()
    assert(msg[1] == '')
    print('{a.hsh}# {a.head}{}{a.reset}'.format(msg[0],a=Attr))
    # XXX get the commits in the merge from the actual commit data instead of from the commit message
    commits = []
    for line in msg[2:]:
        if not line: # stop at first empty line
            break
        cid,_,message = line.partition(' ')
        commits.append((cid,message))

    for (cid, message) in reversed(commits):
        print('{a.hsh}#   {a.head2}{}{a.reset}'.format(cid + ' '+ message,a=Attr))
        commit = repo.commit(cid)
        cmsg = commit.message
        cmsg += '\n'
        cmsg += 'Github-Pull: %s\n' % t[0]
        cmsg += 'Rebased-From: %s\n' % commit.hexsha
        if execute:
            if subprocess.call([GIT,'cherry-pick', commit.hexsha]):
                # fail - drop to shell
                print('Dropping to shell - run git cherry-pick --continue after fixing issues, or exit and choose abort/skip')
                if os.path.isfile('/etc/debian_version'): # Show pull number on Debian default prompt
                    os.putenv('debian_chroot',t[0])
                subprocess.call([BASH,'-i'])
                reply = ask_prompt("Type 'c' to continue, 'a' to abort, 's' to skip pull.")
                if reply == 'c':
                    pass
                elif reply == 'a':
                    exit(1)
                elif reply == 's':
                    subprocess.check_call([GIT,'cherry-pick', '--abort'])
                    continue

            # Sign
            subprocess.check_call([GIT,'commit','--amend','--gpg-sign','-q','-m',cmsg])
        else:
            print('git cherry-pick %s' % (commit.hexsha))
            print('git commit -q --amend -m %s' % (shlex.quote(cmsg)))
