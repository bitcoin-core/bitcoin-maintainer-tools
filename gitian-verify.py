#!/usr/bin/env python3
'''
Verify all gitian signatures for a release and tabulate the outcome.
'''
import argparse
import collections
from enum import Enum, IntFlag
import gpg
import os
import re
import sys
from typing import Dict, List, Set, Optional, Tuple
import yaml

# workaround legacy issue where some yaml may contain !omap instead of !!omap
yaml.add_constructor("!omap", yaml.constructor.SafeConstructor.construct_yaml_omap, Loader=yaml.SafeLoader) # type: ignore

class Status(Enum):
    '''Verification status enumeration.'''
    OK = 0                 # Full match
    NO_FILE = 1            # Result file or sig file not found
    UNKNOWN_KEY = 2        # Name/key combination not in keys.txt
    MISSING_KEY = 3        # Unknown PGP key
    EXPIRED_KEY = 4        # PGP key is expired
    INVALID_SIG = 5        # Known key but invalid signature
    MISMATCH = 6           # Correct signature but mismatching file

class Missing(IntFlag):
    '''Bit field for missing keys,'''
    GPG = 1                # Missing from GPG
    KEYSTXT = 2            # Missing form keys.txt

class Attr:
    '''Terminal attributes.'''
    BOLD = '\033[1m'
    REVERSE = '\033[7m'
    RESET = '\033[0m'
    # Table entries
    # format is Status.X: (output, screen width*)
    # *can't use .len() due to ANSI formatting and unicode char width issues
    GLYPHS = {
        None:                  ('\x1b[90m-\x1b[0m', 1),
        Status.OK:             ('\x1b[92mOK\x1b[0m', 2),
        Status.NO_FILE:        ('\x1b[90m-\x1b[0m', 1),
        Status.MISSING_KEY:    ('\x1b[96mNo Key\x1b[0m', 6),
        Status.EXPIRED_KEY:    ('\x1b[96mExpired\x1b[0m', 7),
        Status.INVALID_SIG:    ('\x1b[91mBad\x1b[0m', 3),
        Status.MISMATCH:       ('\x1b[91mMismatch\x1b[0m', 8),
    }
    DIFF_OLD = '\033[91m'
    DIFF_NEW = '\033[92m'

VerificationResult = collections.namedtuple('VerificationResult', ['verify_ok', 'p_fingerprint', 's_fingerprint', 'error'])
class VerificationInterface:
    '''
    Interface to verify GPG signatures.
    '''
    # Error values from verify_detached
    MISSING_KEY = 0
    BAD = 1
    EXPIRED_KEY = 2

    def __init__(self) -> None:
        self.ctx = gpg.Context(offline=True)

    def verify_detached(self, sig: bytes, result: bytes) -> VerificationResult:
        '''
        Verify a detached GPG signature.
        This function takes a OS path to the signature, and to the signed data.
        It returns a VerificationResult tuple (verify_ok, p_fingerprint, s_fingerprint, error).
        - verify_ok is a bool specifying if the signature was correctly verified.
        - primary_key is the key fingerprint of the primary key (or None if not known)
        - sub_key is the key fingerprint of the signing subkey used (or None if not known)
        - error is a an error code (if !verify_ok) MISSING_KEY, EXPIRED_KEY or BAD
        '''
        try:
            (_, r) = self.ctx.verify(signed_data=result, signature=sig)
        except gpg.errors.BadSignatures as e:
            r = e.result
            verify_ok = False
        else:
            verify_ok = True

        assert(len(r.signatures) == 1) # we don't handle multiple signatures in one assert file
        p_fingerprint = None
        s_fingerprint = r.signatures[0].fpr
        error = None
        if r.signatures[0].summary & gpg.constants.sigsum.KEY_MISSING:
            error = VerificationInterface.MISSING_KEY
        else: # key is known to gnupg
            if r.signatures[0].summary & gpg.constants.sigsum.KEY_EXPIRED:
                error = VerificationInterface.EXPIRED_KEY
            elif not verify_ok: # verification failed, but no specific error to report
                error = VerificationInterface.BAD
            key = self.ctx.get_key(s_fingerprint)
            p_fingerprint = key.fpr

        return VerificationResult(
                verify_ok=verify_ok,
                p_fingerprint=p_fingerprint,
                s_fingerprint=s_fingerprint,
                error=error)

BuildInfo = collections.namedtuple('BuildInfo', ['build_name', 'dir_name', 'package_name'])

def get_builds_for(version: str) -> List[BuildInfo]:
    '''
    Get a list of builds for a version of bitcoin core. This is a list of
    BuildInfo(build_name, dir_name, package_name) tuples.
    '''
    BUILDS = [
    ("linux",        "bitcoin-core-linux-<major>"),
    ("osx-unsigned", "bitcoin-core-osx-<major>"),
    ("win-unsigned", "bitcoin-core-win-<major>"),
    ("osx-signed",   "bitcoin-dmg-signer"),
    ("win-signed",   "bitcoin-win-signer"),
    ]
    vsplit = version.split('.')
    major = vsplit[0] + '.' + vsplit[1]
    major_n = (int(vsplit[0]), int(vsplit[1]))
    result = []

    for build in BUILDS:
        dir_name = version + '-' + build[0]
        package_name = build[1].replace('<major>', major)
        if major_n < (0, 19):
            # before 0.19, package names were bitcoin- instead of bitcoin-core
            package_name = package_name.replace('bitcoin-core', 'bitcoin')
        result.append(BuildInfo(build_name=build[0], dir_name=dir_name, package_name=package_name))
    return result

def load_keys_txt(filename: str) -> List[Tuple[str, str]]:
    '''
    Load signer aliases and key fingerprints from a keys.txt file.
    '''
    keys = []
    with open(filename, 'r') as f:
        for line in f:
            m = re.match('([0-9A-F]+) .* \((.*)\)', line)
            if m:
                for name in m.group(2).split(','):
                    keys.append((m.group(1).upper(), name.strip().lower()))
    return keys

def parse_args() -> argparse.Namespace:
    '''Parse command line arguments.'''
    parser = argparse.ArgumentParser(description='Verify gitian signatures')

    parser.add_argument('--verbose', '-v', action='store_const', const=True, default=False, help='Be more verbose')
    parser.add_argument('--release', '-r', help='Release version (for example 0.21.0rc5)', required=True)
    parser.add_argument('--directory', '-d', help='Signatures directory', required=True)
    parser.add_argument('--keys', '-k', help='Path to keys.txt', required=True)
    parser.add_argument('--compare-to', '-c', help="Compare other manifests to COMPARE_TO's, if not given pick first")

    return parser.parse_args()

def validate_build(verifier: VerificationInterface,
        compare_to: str,
        release_path: str,
        result_file: str,
        sig_file: str,
        verbose: bool,
        keys: List[Tuple[str, str]]) -> Tuple[Dict[str, Status], Dict[Tuple[str, str], Missing]]:
    '''Validate a single build (directory in gitian.sigs).'''
    if not os.path.isdir(release_path):
        return ({}, {}, {})

    reference = None
    if compare_to is not None:
        # Load a specific 'golden' manifest to compare to
        result_path = os.path.join(release_path, compare_to, result_file)
        with open(result_path, 'r') as f:
            result = dict(yaml.safe_load(f))
        reference = result['out_manifest']

    results = {}
    mismatches = {}
    missing_keys: Dict[Tuple[str, str], Missing] = collections.defaultdict(lambda: Missing(0))
    for signer_name in os.listdir(release_path):
        if verbose:
            print(f'For { signer_name }...')
        signer_dir = os.path.join(release_path, signer_name)
        if not os.path.isdir(signer_dir):
            continue

        result_path = os.path.join(signer_dir, result_file)
        sig_path = os.path.join(signer_dir, sig_file)

        if not os.path.isfile(result_path) or not os.path.isfile(sig_path):
            results[signer_name] = Status.NO_FILE
            continue

        with open(sig_path, 'rb') as f:
            sig_data = f.read()
        with open(result_path, 'rb') as f:
            result_data = f.read()
        vres = verifier.verify_detached(sig_data, result_data)

        fingerprint = vres.p_fingerprint or vres.s_fingerprint
        # Check if the (signer, fingerprint) pair is specified in keys.txt (either the primary
        #   or subkey is allowed to be specified).
        #
        # It is important to check the specific combination, otherwise a person
        # could gitian-sign for someone else and it would be undetected.
        not_in_keys = False
        if (vres.p_fingerprint, signer_name.lower()) not in keys and (vres.s_fingerprint, signer_name.lower()) not in keys:
            missing_keys[(signer_name, fingerprint)] |= Missing.KEYSTXT
            not_in_keys = True

        if not vres.verify_ok: # Invalid signature or missing key
            if vres.error == VerificationInterface.MISSING_KEY:
                # missing key, store fingerprint for reporting
                missing_keys[(signer_name, fingerprint)] |= Missing.GPG
                results[signer_name] = Status.MISSING_KEY
            elif vres.error == VerificationInterface.EXPIRED_KEY:
                results[signer_name] = Status.EXPIRED_KEY
            else:
                results[signer_name] = Status.INVALID_SIG
            continue
        else: # Valid PGP signature
            # if the key, signer pair is not in keys.txt, we can't trust it so
            # skip out here
            if not_in_keys:
                results[signer_name] = Status.MISSING_KEY
                continue

            result = dict(yaml.safe_load(result_data))

            if reference is not None and result['out_manifest'] != reference:
                results[signer_name] = Status.MISMATCH
                mismatches[signer_name] = (result['out_manifest'], reference)
            else:
                results[signer_name] = Status.OK

            # if there is no reference, the first with a correct signature is the reference
            if reference is None:
                reference = result['out_manifest']

    if verbose:
        print(results[signer_name])

    return (results, missing_keys, mismatches)

def center(s: str, width: int, total_width: int) -> str:
    '''Center text.'''
    pad = max(total_width - width, 0)
    return (' ' * (pad // 2)) + s + (' ' * ((pad + 1) // 2))

def main() -> None:
    args = parse_args()

    builds = get_builds_for(args.release)
    keys = load_keys_txt(args.keys)
    verifier = VerificationInterface()

    # build descriptor is only used to determine the package name
    # maybe we could derive it otherwise (or simply look for *any* assert file)
    all_missing_keys: Dict[Tuple[str,str],int] = collections.defaultdict(int)
    all_results = {}
    all_mismatches = {}
    for build in builds:
        if args.verbose:
            print(f'Validate { build.build_name } build...')

        release_path = os.path.join(args.directory, build.dir_name)

        result_file = f'{build.package_name}-build.assert'
        sig_file = result_file + '.sig'

        # goal: create a matrix signer × variant → status
        #       keep a list of unknown key fingerprints
        (results, missing_keys, mismatches) = validate_build(verifier, args.compare_to, release_path, result_file, sig_file, args.verbose, keys)
        all_results[build.build_name] = results
        for k, v in missing_keys.items():
            all_missing_keys[k] |= v
        all_mismatches[build.build_name] = mismatches

    # Make a table of signer versus build
    all_signers_set: Set[str] = set()
    for result in all_results.values():
        all_signers_set.update(result.keys())
    all_signers = sorted(list(all_signers_set), key=str.casefold)

    if not all_signers:
        print(f'No build results were found in {args.directory} for release {args.release}', file=sys.stderr)
        exit(1)

    name_maxlen = max(max((len(name) for name in all_signers)), 8)
    build_maxlen = max(max(len(build.build_name) for build in builds),
                       max(glyph[1] for glyph in Attr.GLYPHS.values()))

    header = Attr.REVERSE + Attr.BOLD
    header += 'Signer'.ljust(name_maxlen)
    header += '  '
    for build in builds:
        pad = build_maxlen - len(build.build_name)
        header += center(build.build_name, len(build.build_name), build_maxlen)
        header += '  '
    header += Attr.RESET
    print(header)

    for name in all_signers:
        statuses = []
        for build in builds:
            r: Optional[Status]
            try:
                r = all_results[build.build_name][name]
            except KeyError:
                r = None
            statuses.append(r)

        line = name.ljust(name_maxlen)
        line += '  '
        for status in statuses:
            line += center(Attr.GLYPHS[status][0], Attr.GLYPHS[status][1], build_maxlen)
            line += '  '
        print(line)

    if all_missing_keys:
        print()
        print(f'{Attr.REVERSE}Missing keys{Attr.RESET}')
        for (name, fingerprint),bits in all_missing_keys.items():
            line = name.ljust(name_maxlen)
            line += '  '
            line += fingerprint or '???'
            line += '  '
            miss = []
            if bits & Missing.GPG:
                miss.append('from GPG')
            if bits & Missing.KEYSTXT:
                miss.append('from keys.txt')
            line += ', '.join(miss)
            print(line)

    if all_mismatches:
        print()
        print(f'{Attr.REVERSE}Mismatches{Attr.RESET}')
        for (build, m) in all_mismatches.items():
            for (signer, (result, reference)) in m.items():
                print(f'{signer} ({build}):')
                for (a, b) in zip(reference.split('\n'), result.split('\n')):
                    if a != b:
                        print(f'  -{Attr.DIFF_OLD}{a}{Attr.RESET}')
                        print(f'  +{Attr.DIFF_NEW}{b}{Attr.RESET}')

if __name__ == '__main__':
    main()
