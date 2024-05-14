#!/usr/bin/env python3
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

def dat_name(type_, num) -> str:
    return '{}{:05d}.dat'.format(type_, num)

def link_blocks(src: str, dst: str):
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
        raise ValueError("Maximum block file {:05d} doesn't match maximum undo file {:05d}".format(blk_max, rev_max))
    print('Hard-linking all rev and blk files up to {:05d}'.format(blk_max))
    for i in range(blk_max):
        for type_ in ['rev','blk']:
            name = dat_name(type_, i)
            os.link(path.join(src, name), path.join(dst, name))
    print('Copying rev and blk files {:05d}'.format(blk_max))
    for type_ in ['rev','blk']:
        name = dat_name(type_, blk_max)
        shutil.copyfile(path.join(src, name), path.join(dst, name))

def link_leveldb(src: str, dst: str):
    ldb_files = []
    other_files = []
    for fname in os.listdir(src):
        if re.match('^[0-9]{6,}.ldb$', fname):
            ldb_files.append(fname)
        else:
            other_files.append(fname)
    print('Hard-linking {:d} leveldb files'.format(len(ldb_files)))
    for name in ldb_files:
        os.link(path.join(src, name), path.join(dst, name))
    print('Copying {:d} other files in leveldb dir'.format(len(other_files)))
    for name in other_files:
        shutil.copyfile(path.join(src, name), path.join(dst, name))

if len(sys.argv) != 3:
    print('Usage: {} reference_datadir destination_datadir'.format(path.basename(sys.argv[0])))
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
    print('warning: destination directory {} already exists'.format(dstdir))
os.makedirs(dst_blocks_index)
os.makedirs(dst_chainstate)

print('Copying blocks')
link_blocks(src_blocks, dst_blocks)
print('Copying block index')
link_leveldb(src_blocks_index, dst_blocks_index)
print('Copying chainstate')
link_leveldb(src_chainstate, dst_chainstate)
