External repository for Bitcoin Core related maintenance tools.

clang-format
------------

A script to format cpp source code according to the .clang-format file in the bitcoin repo.
This should only be applied to new files or files which are currently not actively developed on.
Also, git subtrees are not subject to formatting.

Note: The script is currently untested and unmaintained, but kept for archival reasons, in
case it is planned to be used some day.

build-for-compare
--------------------

Build for binary comparison.

See `build-for-compare.py --help` for more information.

Builds from current directory, which is assumed to be a git clone of the bitcoin repository.

**DO NOT RUN this with the nocopy=1 flag set on working tree if you have any local additions, it will nuke all
non-repository files, multiple times over. By leaving nocopy off (default) the git tree is copied to a temporary
directory and all operations are performed there.**

Example:
```bash
git clone https://github.com/bitcoin/bitcoin.git bitcoin-compare
cd bitcoin-compare
../bitcoin-maintainer-tools/build-for-compare.py 4731cab 2f71490
sha256sum /tmp/compare/bitcoind.*.stripped
git diff -W --word-diff /tmp/compare/4731cab /tmp/compare/2f71490
```

backport
--------

Script to backport pull requests in order of merge, to minimize number of conflicts.
Pull ids are listed in `to_backport.txt` or given on the command line.

Requires `pip3 install gitpython` or similar.

unittest-statistics
--------------------------

`unittest-statistics.py` can be used to print a table of the slowest 20 unit tests.

Usage:
```bash
unittest-statistics.py </path/to/test_bitcoin> [<subtest>]
```

For example:
```bash
unittest-statistics.py src/test/test_bitcoin wallet_tests
```

treehash512
--------------

This script will show the SHA512 tree has for a certain commit, or HEAD
by default.

Usage:

```bash
treehash512.py [<commithash>]
```

This should match the Tree-SHA512 commit metadata field added by
github-merge.

signoff
----------

This is an utility to manually add a treehash to the HEAD commit and then
gpg-sign it. This is useful when there is the need to manually add a commit.

Usage:

```bash
signoff.py
```
(no command line arguments)

When there is already a treehash on the HEAD commit, it is compared against
what is computed. If this matches, it continues. If the treehash mismatches an
error is thrown. If there is no treehash it adds the "Tree-SHA512:" header with
the computed hash to the commit message.

After making sure the treehash is correct it verifies whether the commit is
signed. If so it just displays the signature, if not, it is signed.

subtree updates
---------------

Bitcoin Core comes with several subtrees (c.f. https://github.com/bitcoin/bitcoin/blob/master/contrib/devtools/README.md#git-subtree-checksh)
To update the subtree, make sure to fetch the remote of the subtree.
Then a simple call should pull in and squash the changes:

```sh
git subtree pull --prefix src/${prefix} ${remote_repo} ${ref} --squash
```

For setting up a subtree, refer to `git help subtree`.

check-dnsseeds
---------------

Sanity-check the DNS seeds used by Bitcoin Core.

Usage:

```bash
check-dnsseeds.py
```

Example output:

```bash
* Mainnet
OK   seed.bitcoin.sipa.be (40 results)
OK   dnsseed.bluematt.me (33 results)
OK   dnsseed.bitcoin.dashjr.org (38 results)
OK   seed.bitcoinstats.com (50 results)
OK   bitseed.xf2.org (13 results)
FAIL seed.bitcoin.jonasschnelli.ch

* Testnet
FAIL testnet-seed.bitcoin.jonasschnelli.ch
OK   seed.tbtc.petertodd.org (38 results)
OK   testnet-seed.bluematt.me (3 results)
```

fastcopy-chaindata
-------------------

Fast local copy of Bitcoin Core blockchain state.

```bash
fastcopy-chaindata.py ~/.bitcoin /path/to/temp/datadir
```

This utility hardlinks all but the last block data file (rev and blk),
and hardlinks all .ldb files to the destination. The last data files as well
as the other leveldb data files (such as the log) are copied.

This relies on the fact that block files (except the last) and ldb files
are read-only once they are written.

Warning: Hardlinking only works within a filesystem, and may not work for all
filesystems.

