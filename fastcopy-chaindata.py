#!/usr/bin/python3
# Copyright (c) 2017 Wladimir J. van der Laan
# Distributed under the MIT software license, see the accompanying
# file COPYING or http://www.opensource.org/licenses/mit-license.php.
'''
Fast local copy of Bitcoin Core blockchain state.

This utility hardlinks all but the last block data file (rev and blk),
and hardlinks all .ldb files to the destination. The last data files as well
as the other leveldb data files (such as the log) are copied.

This relies on the fact that block files (except the last) and ldb files
are read-only once they are written.

Warning: Hardlinking only works within a filesystem, and may not work for all
filesystems.
'''
import os,re,shutil,sys
from os import path

def dat_name(type_, num):
    return '%s%05d.dat' % (type_, num)

def link_blocks(src, dst):
    rev_max = -1
    blk_max = -1
    for fname in os.listdir(src):
        match = re.match('^rev([0-9]{5}).dat$', fname)
        if match:
            rev_max = max(rev_max, int(match.group(1)))
        match = re.match('^blk([0-9]{5}).dat$', fname)
        if match:
            blk_max = max(blk_max, int(match.group(1)))
    if blk_max != rev_max:
        raise ValueError("Maximum block file %05d doesn't match maximum undo file %05d" % (blk_max, rev_max))
    print('hard-link all rev and blk files up to %05d' % blk_max)
    for i in range(blk_max):
        for type_ in ['rev','blk']:
            name = dat_name(type_, i)
            os.link(path.join(src, name), path.join(dst, name))
    print('copying rev and blk files %05d' % blk_max)
    for type_ in ['rev','blk']:
        name = dat_name(type_, blk_max)
        shutil.copyfile(path.join(src, name), path.join(dst, name))

def link_leveldb(src, dst):
    ldb_files = []
    other_files = []
    for fname in os.listdir(src):
        if re.match('^[0-9]{6}.ldb$', fname):
            ldb_files.append(fname)
        else:
            other_files.append(fname)
    print('hard-linking %d ldb files' % len(ldb_files))
    for name in ldb_files:
        os.link(path.join(src, name), path.join(dst, name))
    print('copying %d other files in ldb dir' % len(other_files))
    for name in other_files:
        shutil.copyfile(path.join(src, name), path.join(dst, name))

if len(sys.argv) != 3:
    print('Usage: %s reference_datadir destination_datadir' % path.basename(sys.argv[0]))
    exit(1)
srcdir = sys.argv[1] # '/store2/tmp/testbtc'
dstdir = sys.argv[2] # '/store2/tmp/testbtc2'

src_blocks = path.join(srcdir, 'blocks')
dst_blocks = path.join(dstdir, 'blocks')
src_blocks_index = path.join(srcdir, 'blocks/index')
dst_blocks_index = path.join(dstdir, 'blocks/index')
src_chainstate = path.join(srcdir, 'chainstate')
dst_chainstate = path.join(dstdir, 'chainstate')

try:
    os.makedirs(dstdir)
except FileExistsError:
    print('warning: destination directory %s already exists' % dstdir)
os.makedirs(dst_blocks_index)
os.makedirs(dst_chainstate)

link_blocks(src_blocks, dst_blocks)
print('copy block index')
link_leveldb(src_blocks_index, dst_blocks_index)
print('copy chainstate')
link_leveldb(src_chainstate, dst_chainstate)
