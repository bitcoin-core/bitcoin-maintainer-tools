Contents
========
This directory contains executable scripts for bitcoin developers and maintainers.

All scripts have a `-h` option which gives a detailed description of usage and options.

The scripts may write to `/tmp/bitcoin-maintainer-tools/` to hold state when needed.

Operations that generate information have a `--json` option to assist programmatic uses of the data.

clone\_configure\_build.py
==========================
Clones, configures builds a bitcoin repository to a given directory from scratch. This includes downloading and building BerkelyDB 4.8. It assumes the local environment has the rest of the dependency packages installed.

The upstream url and branch can be given as options.

It follows the most straightforward configuration path as described by `doc/build_unix.md` in `https://github.com/bitcoin/bitcoin`. If a non-default configuration is required, manual configuration is the best option.

clang\_format.py
================

Provides a set of subcommands for using the `clang-format` tool to operate on on source files.

clang\_format.py report
-----------------------
Generates a report with format metrics on the target repository or target files.

clang\_format.py check
-----------------------
Validates that the target repository or target files match a particular format.

clang\_format.py format
-----------------------
Applies formatting to a target repository or target files.

basic\_style.py
===============
Provides a set of subcommands that does some basic source file coding style checking and reporting. The style rules are defined inside the script as regex expressions.

basic\_style.py report
----------------------
Generates a report with metrics on the target repository or target files.

basic\_style.py check
---------------------
Validates that the target repository or target files match the style rules.

basic\_style.py fix
-------------------
Performs basic regex search-and-replace to fix the style issues that are found in the repo or in target files.

clang\_static\_analysis.py
==========================
Provides a set of subcommmands for running `scan-build` on the repository and revealing any issues.

clang\_static\_analysis.py report
---------------------------------
Runs `scan-build` and generates a summary report of the results.

clang\_static\_analysis.py check
---------------------------------
Runs `scan-build` and validates that there are no issues found. If there are issues found, details are displayed.

copyright\_header.py
====================
Provides a set of subcommands that analyze and assist managing the set of copyright headers of source files of the repository.

copyright\_header.py report
---------------------------
Generates a report with copyright header metrics of the target repository or target files.

copyright\_header.py check
--------------------------
Validates that the copyright headers of the target repository or target files are in an expected state.

copyright\_header.py update
---------------------------
Adjusts the end year of the copyright headers of the target repository or target files to make it match the year of the last edit, as determined by the `git log` output.

copyright\_header.py insert
---------------------------
Inserts a properly-formatted `The Bitcoin Core developers`-held MIT License copyright header in target files where it is currently missing.

reports.py
==========
Runs the suite of `report` subcommands provided by other scripts in this directory upon a target.

checks.py
=========
Runs the suite of `check` subcommands provided by other scripts in this directory upon a target.

