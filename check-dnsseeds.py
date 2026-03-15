#!/usr/bin/env python3
'''
Simple script to check the status of all Bitcoin Core DNS seeds.
Seeds are available from https://github.com/bitcoin/bitcoin/blob/master/src/kernel/chainparams.cpp
'''
import argparse
import subprocess
from itertools import combinations

NODE_NONE = 0
NODE_NETWORK = (1 << 0)
NODE_BLOOM = (1 << 2)
NODE_WITNESS = (1 << 3)
NODE_COMPACT_FILTERS = (1 << 6)
NODE_NETWORK_LIMITED = (1 << 10)
NODE_P2P_V2 = (1 << 11)


SEEDS_PER_NETWORK={
    'mainnet': [
        "seed.bitcoin.sipa.be",
        "dnsseed.bluematt.me",
        "seed.bitcoin.jonasschnelli.ch",
        "seed.btc.petertodd.net",
        "seed.bitcoin.sprovoost.nl",
        "dnsseed.emzy.de",
        "seed.bitcoin.wiz.biz",
        "seed.mainnet.achownodes.xyz",
    ],
    'testnet': [
        "testnet-seed.bitcoin.jonasschnelli.ch",
        "seed.tbtc.petertodd.net",
        "testnet-seed.bluematt.me",
        "seed.testnet.bitcoin.sprovoost.nl",
        "seed.testnet.achownodes.xyz",
    ],
    'testnet4': [
        "seed.testnet4.bitcoin.sprovoost.nl",
        "seed.testnet4.wiz.biz",
    ],
    'signet': [
        "seed.signet.bitcoin.sprovoost.nl",
        "seed.signet.achownodes.xyz"
    ],
}

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

def get_combinations(services):
   
    all_flags = services.values()
    all_combinations = []

    for i in range(1, len(all_flags) + 1):
        for combo in combinations(all_flags, i):
            combination_value = sum(combo)
            combination_hex = hex(combination_value)[2:].upper()
            combination_names = [service for service, flag in services.items() if flag in combo]
            all_combinations.append((combination_hex, combination_names))
  
    return all_combinations

def check_dns_support(combination_hex, provider):
    """
    Checks if a DNS provider supports a given combination of service flags.
    """
    
    domain = f"x{combination_hex}.{provider}"
    command = ["dig", domain]
    try:
        result = subprocess.run(command, capture_output=True, check=True)
        output = result.stdout.decode("utf-8")
        return "ANSWER SECTION" in output
    except subprocess.CalledProcessError:
        return False  

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Bitcoin Core Filter DNS Seeds')
    parser.add_argument('--filter-services', action='store_true', help='Scan which filters are in use')
    args = parser.parse_args()


    print("\nBitcoin Core DNS Seed Status Check:\n")

    for (network, seeds) in SEEDS_PER_NETWORK.items():
        print(f"\x1b[90m* \x1b[97m{network}\x1b[0m")

        for hostname in seeds:
            check_seed(hostname)

        print()

    print("\n")

    if args.filter_services:
        combinations = get_combinations({
            "NODE_NONE": NODE_NONE,
            "NODE_NETWORK": NODE_NETWORK,
            "NODE_BLOOM": NODE_BLOOM,
            "NODE_WITNESS": NODE_WITNESS,
            "NODE_COMPACT_FILTERS": NODE_COMPACT_FILTERS,
            "NODE_NETWORK_LIMITED": NODE_NETWORK_LIMITED,
            "NODE_P2P_V2": NODE_P2P_V2,
        })

        print("All possible combinations of node services and their bit flags in hexadecimal:")
        for combination_hex, service_names in combinations:
            print(f"  Bit flag (hex): {combination_hex} - Service: {', '.join(service_names)}")

            for (network, seeds) in SEEDS_PER_NETWORK.items():
                for hostname in seeds:
                    supports_combination = check_dns_support(combination_hex, hostname)
                    print(f" Network: {network}, Provider: {hostname} - Supports Service: {supports_combination}")

