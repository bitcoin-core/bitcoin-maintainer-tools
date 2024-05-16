#!/usr/bin/env python3
'''
Script to check the status of all Bitcoin Core DNS seeds.
Seeds are available from https://github.com/bitcoin/bitcoin/blob/master/src/kernel/chainparams.cpp
'''
import argparse
import dns.message
import dns.rdataclass
import dns.rdatatype
import dns.resolver
import dns.query
import selectors
import socket
import sys
import time

from termlib import textattr, tableprinter
from termlib.textattr import TextAttr
from termlib.tableprinter import Column, ColData, Align, TablePrinter

SEEDS_PER_NETWORK={
    'mainnet': [
        "seed.bitcoin.sipa.be.",
        "dnsseed.bluematt.me.",
        "dnsseed.bitcoin.dashjr-list-of-p2p-nodes.us.",
        "seed.bitcoinstats.com.",
        "seed.bitcoin.jonasschnelli.ch.",
        "seed.btc.petertodd.net.",
        "seed.bitcoin.sprovoost.nl.",
        "dnsseed.emzy.de.",
        "seed.bitcoin.wiz.biz.",
        "dnsseed.mainnet.bitcoin.achow101.com.",
    ],
    'testnet': [
        "testnet-seed.bitcoin.jonasschnelli.ch.",
        "seed.tbtc.petertodd.net.",
        "testnet-seed.bluematt.me.",
        "seed.testnet.bitcoin.sprovoost.nl.",
        "dnsseed.testnet.bitcoin.achow101.com.",
    ],
    'signet': [
        "seed.signet.bitcoin.sprovoost.nl.",
        "dnsseed.signet.bitcoin.achow101.com.",
    ],
}
DEFAULT_PORT = {
    'mainnet': 8333,
    'testnet': 18333,
    'signet': 38333,
}

def try_connect(addrs, port, timeout=1):
    '''Try connecting to addresses from name record, in parallel.'''
    NETWORK = {
        dns.rdatatype.A: socket.AF_INET,
        dns.rdatatype.AAAA: socket.AF_INET6,
    }
    sel = selectors.DefaultSelector()
    result = [False] * len(addrs)
    sockets = []
    try:
        for idx, addr in enumerate(addrs):
            sock = socket.socket(NETWORK[addr.rdtype], socket.SOCK_STREAM)
            sock.setblocking(0)
            try:
                sock.connect((addr.address, port))
            except BlockingIOError:
                pass
            except IOError as e:
                print(e)
                sock.close()
                continue
            sel.register(sock, selectors.EVENT_WRITE, idx)
            sockets.append(sock)

        # wait for events until timeout
        curtime = time.monotonic()
        deadline = curtime + timeout
        while curtime < deadline:
            for key, mask in sel.select(deadline - curtime):
                result[key.data] = True
            curtime = time.monotonic()
    finally: # clean up
        for sock in sockets:
            sock.close()

    return result

def check_seed(tp, ns, seed_name, service_flags=9, port=DEFAULT_PORT['mainnet'], ntries=3):
    '''Check one DNS seed, print a row to table printer.'''
    full_seed_name = f'x{service_flags}.{seed_name}'
    qname = dns.name.from_text(full_seed_name)

    error = False
    per_nettype = {}
    addresses = []
    for rectype in [dns.rdatatype.A, dns.rdatatype.AAAA]:
        q = dns.message.make_query(qname, rectype, flags=dns.flags.AD | dns.flags.RD)
        n = 0
        while True:
            try:
                r = dns.query.udp(q, ns, raise_on_truncation=True)
            except dns.message.Truncated:
                r = dns.query.tcp(q, ns)

            n += 1
            if r.rcode() != dns.rcode.SERVFAIL or n >= ntries: # only SERVFAIL warrants retrying
                break
            # Retry after sleep
            time.sleep(0.1)

        if r.rcode() != dns.rcode.NOERROR:
            error = True
            per_nettype[rectype] = [0, 0, None, 0, f'{dns.rcode.to_text(r.rcode())}']
            continue
        try:
            a_res = r.find_rrset(r.answer, qname, dns.rdataclass.IN, rectype)
            ttl = a_res.ttl
            addresses.extend(a_res)
        except KeyError: # no RRset at all
            ttl = None

        per_nettype[rectype] = [0, 0, ttl, r.flags, None]

    # Check connectability.
    statuses = try_connect(addresses, port)

    # Compute totals.
    total_results = 0
    total_connectable = 0
    for addr, connectable in zip(addresses, statuses):
        per_nettype[addr.rdtype][0] += 1
        total_results += 1
        if connectable:
            per_nettype[addr.rdtype][1] += 1
            total_connectable += 1

    # Make row.
    columns = []
    if error:
        columns.append(ColData(attr=TextAttr(fg='#ff6060'), val='ERR'))
    elif total_connectable == 0:
        columns.append(ColData(attr=TextAttr(fg='#c0c0c0'), val='NONE'))
    else:
        columns.append(ColData(attr=TextAttr(fg='#60ff60'), val='OK'))
    columns.append(ColData(val=seed_name))
    dnssec = all((rec[3] & dns.flags.AD) != 0 for rec in per_nettype.values())
    columns.append(ColData(val=[' ', '✓'][dnssec]))
    columns.append(ColData(val=f"{total_connectable}/{total_results}"))
    for (addresses, connectable, ttl, flags, errmsg) in [per_nettype[dns.rdatatype.A], per_nettype[dns.rdatatype.AAAA]]:
        if errmsg is not None:
            columns.append(ColData(ncol=2, val=errmsg))
        else:
            if flags & dns.flags.AD: # authenticated green
                attr = TextAttr(fg='#80ff80')
            else:
                attr = None
            columns.append(ColData(attr=attr, val=f"{connectable}/{addresses}"))
            if ttl is not None:
                columns.append(ColData(attr=attr, val=f"{ttl}"))
            else:
                columns.append(ColData(attr=attr, val=""))

    tp.print_row(columns)

def parse_args():
    parser = argparse.ArgumentParser(description="Bitcoin DNS seeds checker")
    parser.add_argument("--service-flags", "-s", type=int, default=9,
            help='Service flags to query for (default: 9 which is NODE_NETWORK and NODE_WITNES)')
    parser.add_argument("--network", "-n", default=None,
            help="Query for specific network.")
    return parser.parse_args()

def main():
    args = parse_args()

    # Get default DNS server.
    default = dns.resolver.get_default_resolver()
    ns = default.nameservers[0]

    print(f'Flags: x{args.service_flags}')

    base_attr = TextAttr(fg='#8060ff')
    name_attr = TextAttr(fg='#a080ff')

    columns = [
        Column('status',    6,  Align.LEFT, base_attr),
        Column('name',      40, Align.LEFT, name_attr),
        Column('sec',       1,  Align.CENTER, name_attr),
        Column('totals',    10, Align.LEFT, base_attr),
        Column('ipv4_stat', 10, Align.LEFT, base_attr),
        Column('ipv4_ttl',  10, Align.RIGHT, base_attr),
        Column('ipv6_stat', 10, Align.LEFT, base_attr),
        Column('ipv6_ttl',  10, Align.RIGHT, base_attr),
    ]
    tp = TablePrinter(sys.stdout, textattr.RESET, columns)

    hdr_attr = TextAttr.reset(fg='#808080', reverse=True, bold=True)
    tp.print_row([
        (1, hdr_attr, "Status"),
        (1, hdr_attr, "DNS name"),
        (1, hdr_attr, "S"),
        (1, hdr_attr, "Totals"),
        (2, hdr_attr, "IPv4"),
        (2, hdr_attr, "IPv6"),
    ])
    tp.print_row([
        (1, hdr_attr, ""),
        (1, hdr_attr, ""),
        (1, hdr_attr, ""),
        (1, hdr_attr, "nconn/n"),
        (1, hdr_attr, "nconn/n"),
        (1, hdr_attr, "TTL"),
        (1, hdr_attr, "nconn/n"),
        (1, hdr_attr, "TTL"),
    ])

    for (network, seeds) in SEEDS_PER_NETWORK.items():
        if args.network is not None and network != args.network:
            continue
        print(f"\x1b[90m* \x1b[97m{network}\x1b[0m")

        for hostname in seeds:
            check_seed(tp, ns, hostname, service_flags=args.service_flags, port=DEFAULT_PORT[network])

        print()

if __name__ == '__main__':
    main()

