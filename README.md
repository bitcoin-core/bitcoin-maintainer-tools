External repository for Bitcoin Core related maintenance tools.

build_for_compare
--------------------

Build for binary comparison.

See `build_for_compare.py --help` for more information.

Builds from current directory, which is assumed to be a git clone of the bitcoin repository.

**DO NOT RUN this on working tree if you have any local additions, it will nuke all non-repository files, multiple times
over. Ideally this would close a git tree first to a temporary directory. Suffice to say, it doesn't.**

