#!/usr/bin/python3
'''
This is an utility to manually add a treehash to the top commit and
then gpg-sign it.
'''
from treehash512 import tree_sha512sum, GIT
import subprocess, sys
HDR = b'Tree-SHA512'
def main():
    commit = 'HEAD'
    h = tree_sha512sum(commit).encode()
    msg = subprocess.check_output([GIT, 'show', '-s', '--format=%B', commit]).rstrip()

    curh = None
    for line in msg.splitlines():
        if line.startswith(HDR+b':'):
            assert(curh is None) # no multiple treehashes
            curh = line[len(HDR)+1:].strip()

    if curh == h:
        print('Warning: already has a (valid) treehash')
        if subprocess.call([GIT, 'verify-commit', commit]) == 0:
            # already signed, too, just exit
            sys.exit(0)
    elif curh is not None:
        print('Error: already has a treehash, which mismatches. Something is wrong. Remove it first.')
        sys.exit(1)
    else: # no treehash
        msg += b'\n\n' + HDR + b': ' + h

    print(msg.decode())

    subprocess.check_call([GIT, 'commit', '--amend', '--gpg-sign', '-m', msg, '--no-edit'])
    rv = subprocess.call([GIT, 'verify-commit', commit])
    sys.exit(rv)

if __name__ == '__main__':
    main()
