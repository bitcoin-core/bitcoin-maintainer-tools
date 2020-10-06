#!/usr/bin/env python3
'''
Simple script to check the status of all Bitcoin Core DNS seeds.
Seeds are available from https://github.com/bitcoin/bitcoin/blob/master/src/chainparams.cpp
'''
import subprocess

SEEDS_MAINNET=["seed.bitcoin.sipa.be","dnsseed.bluematt.me","dnsseed.bitcoin.dashjr.org",
        "seed.bitcoinstats.com","seed.bitcoin.jonasschnelli.ch","seed.btc.petertodd.org",
        "seed.bitcoin.sprovoost.nl", "dnsseed.emzy.de","seed.bitcoin.wiz.biz"]
SEEDS_TESTNET=["testnet-seed.bitcoin.jonasschnelli.ch","seed.tbtc.petertodd.org",
        "testnet-seed.bluematt.me","seed.testnet.bitcoin.sprovoost.nl"]

def check_seed(x):
    p = subprocess.run(["host",x], capture_output=True, universal_newlines=True)
    out = p.stdout

    # Parse matching lines
    addresses = []
    for line in out.splitlines():
        if "has address" in line or "has IPv6 address" in line:
            addresses.append(line)

    if addresses:
        print(f"\x1b[94mOK\x1b[0m   {x} ({len(addresses)} results)")
    else:
        print(f"\x1b[91mFAIL\x1b[0m {x}")

if __name__ == '__main__':
    print("\x1b[90m* \x1b[97mMainnet\x1b[0m")

    for hostname in SEEDS_MAINNET:
        check_seed(hostname)

    print()
    print("\x1b[90m* \x1b[97mTestnet\x1b[0m")

    for hostname in SEEDS_TESTNET:
        check_seed(hostname)
