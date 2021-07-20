#!/usr/bin/env python3
'''
Make a new release tag, performing a few checks.

Usage: make-tag.py <tag>
'''
import os
import subprocess
import re
import sys
import collections

import treehash512

GIT = os.getenv("GIT", "git")

# Full version specification
VersionSpec = collections.namedtuple('VersionSpec', ['major', 'minor', 'revision', 'build', 'rc'])

def version_name(spec):
    '''
    Short version name for comparison.
    '''
    if not spec.build:
        version = f"{spec.major}.{spec.minor}.{spec.revision}"
    else:
        version = f"{spec.major}.{spec.minor}.{spec.revision}.{spec.build}"
    if spec.rc:
        version += f"rc{spec.rc}"
    return version

def parse_tag(tag):
    '''
    Parse a version tag. Valid version tags are

    - v1.2.3
    - v1.2.3.4
    - v1.2.3rc4
    - v1.2.3.4rc5
    '''
    m = re.match("^v([0-9]+)\.([0-9]+)\.([0-9]+)(?:\.([0-9]+))?(?:rc([0-9])+)?$", tag)

    if m is None:
        print(f"Invalid tag {tag}", file=sys.stderr)
        sys.exit(1)

    major = m.group(1)
    minor = m.group(2)
    revision = m.group(3)
    build = m.group(4)
    rc = m.group(5)

    # Check for x.y.z.0 or x.y.zrc0
    if build == '0' or rc == '0':
        print('rc or build cannot be specified as 0 (leave them out instead)', file=sys.stderr)
        sys.exit(1)

    # Implicitly, treat no rc as rc0 and no build as build 0
    if build is None:
        build = 0
    if rc is None:
        rc = 0

    return VersionSpec(int(major), int(minor), int(revision), int(build), int(rc))

def check_configure_ac(spec):
    '''
    Parse configure.ac and return
    (major, minor, revision, build, rc)
    '''
    info = {}
    filename = 'configure.ac'
    with open(filename) as f:
        for line in f:
            m = re.match("define\(_CLIENT_VERSION_([A-Z_]+), ([0-9a-z]+)\)", line)
            if m:
                info[m.group(1)] = m.group(2)
    # check if IS_RELEASE is set
    if info["IS_RELEASE"] != "true":
        print(f'{filename}: IS_RELEASE is not set to true', file=sys.stderr)
        sys.exit(1)

    cfg_spec = VersionSpec(
            int(info['MAJOR']),
            int(info['MINOR']),
            int(info['REVISION']),
            int(info['BUILD']),
            int(info['RC']),
        )

    if cfg_spec != spec:
        print(f"{filename}: Version from tag {version_name(spec)} doesn't match specified version {version_name(cfg_spec)}", file=sys.stderr)
        sys.exit(1)

def check_msvc_config_h(spec):
    info = {}
    filename = 'build_msvc/bitcoin_config.h'
    with open(filename) as f:
        for line in f:
            m = re.match("#define ([A-Z_]+) (.+)$", line)
            if m:
                info[m.group(1)] = m.group(2)
    # check if IS_RELEASE is set
    if info["CLIENT_VERSION_IS_RELEASE"] != "true":
        print(f'{filename}: IS_RELEASE is not set to true', file=sys.stderr)
        sys.exit(1)

    package_name = info['PACKAGE_NAME'][1:-1]
    if info['PACKAGE_STRING'] != f'"{package_name} {spec.major}.{spec.minor}.{spec.revision}"':
        print(f'PACKAGE_STRING is not set correctly for msvc')
        sys.exit(1)

    if info['PACKAGE_VERSION'] != f'"{spec.major}.{spec.minor}.{spec.revision}"':
        print(f'PACKAGE_VERSION is not set correctly for msvc')
        sys.exit(1)

    msvc_spec = VersionSpec(
            int(info['CLIENT_VERSION_MAJOR']),
            int(info['CLIENT_VERSION_MINOR']),
            int(info['CLIENT_VERSION_REVISION']),
            int(info['CLIENT_VERSION_BUILD']),
            None, # RC is not specified here
        )

    if (msvc_spec.major != spec.major or
        msvc_spec.minor != spec.minor or
        msvc_spec.revision != spec.revision or
        msvc_spec.build != spec.build):
        print(f"{filename}: Version from tag {version_name(spec)} doesn't match specified version {version_name(msvc_spec)}", file=sys.stderr)
        sys.exit(1)

def main():
    try:
        tag = sys.argv[1]
    except IndexError:
        print("Usage: make-tag.py <tag>, e.g. v0.19.0 or v0.19.0rc3", file=sys.stderr)
        sys.exit(1)

    spec = parse_tag(tag)

    # Check that the script is called from repo root
    if not os.path.exists('.git'):
        print('Execute this script at the root of the repository', file=sys.stderr)
        sys.exit(1)

    # Check if working directory clean
    if subprocess.call([GIT, 'diff-index', '--quiet', 'HEAD']):
        print('Git working directory is not clean. Commit changes first.', file=sys.stderr)
        sys.exit(1)

    # Check version components against configure.ac in git tree
    check_configure_ac(spec)

    # Check version components against MSVC build config
    check_msvc_config_h(spec)

    # Generate base message
    if not spec.build:
        version = f"{spec.major}.{spec.minor}.{spec.revision}"
    else:
        version = f"{spec.major}.{spec.minor}.{spec.revision}.{spec.build}"
    if spec.rc:
        version += f" release candidate {spec.rc}"
    else:
        version += " final"
    msg = 'Bitcoin Core ' + version + '\n'

    # Add treehash header
    msg += "\n"
    msg += 'Tree-SHA512: ' + treehash512.tree_sha512sum() + '\n'

    # Finally, make the tag
    print(msg)
    return subprocess.call([GIT, "tag", "-s", tag, "-m", msg])

if __name__ == '__main__':
    sys.exit(main())
