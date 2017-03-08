Contents
========
This directory contains regression tests for the scripts under `bin/`.

Tests
=====
There should be a `test_<script>.py` file corresponding for every script in the `bin` directory. Each should cover the basic invocation options of the script to protect against breakage. They should also all be called from TravisCI.

test\_all.py
============

This script is the exception, since it invokes every other test script. It runs in serial, so it takes a long time.
