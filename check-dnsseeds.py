#!/usr/bin/env python3
'''
Simple script to check status of all bitcoin DNS seeds.
'''
import subprocess

SEEDS_MAINNET=["seed.bitcoin.sipa.be","dnsseed.bluematt.me","dnsseed.bitcoin.dashjr.org","seed.bitcoinstats.com","bitseed.xf2.org","seed.bitcoin.jonasschnelli.ch"]
SEEDS_TESTNET=["testnet-seed.bitcoin.jonasschnelli.ch","seed.tbtc.petertodd.org","testnet-seed.bluematt.me"]

def check_seed(x):
    p = subprocess.Popen(["host",x], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (out,err) = p.communicate(None)
    out = out.strip()

    # Parse matching lines
    addresses = []
    for line in out.split(b"\n"):
        if b"has address" in line or b"has IPv6 address" in line:
            addresses.append(line)

    if addresses:
        print("\x1b[94mOK\x1b[0m   {} ({} results)".format(x, len(addresses)))
    else:
        print("\x1b[91mFAIL\x1b[0m {}".format(x))

if __name__ == '__main__':
    print("\x1b[90m* \x1b[97mMainnet\x1b[0m")

    for hostname in SEEDS_MAINNET:
        check_seed(hostname)

    print()
    print("\x1b[90m* \x1b[97mTestnet\x1b[0m")

    for hostname in SEEDS_TESTNET:
        check_seed(hostname)
