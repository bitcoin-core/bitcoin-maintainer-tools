Contents
========
This directory contains common infrastructure for bitcoin maintainer scripts.

File, Subdirectory and Namspace Convention
==========================================

The subdirectory, file and class names are meant to follow a semi-consistent pattern. This is not a strict requirement, but use it as guidance for keeping the layout reasonably modular, organized and intuitive.

To illustrate the convention, the class `GitRepository` is found in `git/repository.py`. The file and the class encapsulate the concept of a git repository and is placed in the `git` subdirectory with other git-related concepts. The `ClangTarball` class is therefore located in `clang/tarball.py` following the same convention.

Please attempt to follow this convention for new code.
