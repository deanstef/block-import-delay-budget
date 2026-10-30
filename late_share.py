#!/usr/bin/env python3
"""How much more often would Ethereum nodes import a block after the attestation deadline if block
import took X ms longer? Computed from Xatu's public beacon_api_eth_v1_events_block table.

Usage:
    python3 late_share.py [--date 2026-09-30] [--added 10,25,50,100,250,1000]

Reads data/beacon_api_eth_v1_events_block-<date>.parquet, downloading it from Xatu's public
parquet store if it is not there yet, and prints a markdown table. See README.md for the method.
"""
import argparse, os, urllib.request
import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = "beacon_api_eth_v1_events_block"
URL = "https://data.ethpandaops.io/xatu/mainnet/databases/default/" + TABLE + "/{y}/{m}/{d}.parquet"
DEADLINE_MS = 4000          # attestation deadline, 1/3 of a 12 s slot


def fetch(date):
    path = os.path.join(HERE, "data", f"{TABLE}-{date}.parquet")
    if not os.path.exists(path):
        y, m, d = (int(x) for x in date.split("-"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        # The host rejects urllib's default User-Agent.
        req = urllib.request.Request(URL.format(y=y, m=m, d=d), headers={"User-Agent": "curl/8"})
        with urllib.request.urlopen(req) as r, open(path + ".part", "wb") as f:
            f.write(r.read())
        os.replace(path + ".part", path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="2026-09-30", help="UTC day, YYYY-MM-DD")
    ap.add_argument("--added", default="10,25,50,100,250,1000", help="added import delays, ms")
    args = ap.parse_args()
    added = [int(x) for x in args.added.split(",")]

    con = duckdb.connect()
    # One row per (node, slot): the node's import time of the slot's block, in ms from slot start.
    # min() guards against duplicate events for the same slot.
    con.execute("""create temp table ns as
        select meta_client_name node, slot, min(propagation_slot_start_diff) ms
        from read_parquet(?) group by 1, 2""", [fetch(args.date)])
    nodes, slots, rows = con.execute(
        "select count(distinct node), count(distinct slot), count(*) from ns").fetchone()

    def late(x):
        return 100 * con.execute("select avg((ms + ? > ?)::int) from ns", [x, DEADLINE_MS]).fetchone()[0]

    base = late(0)
    print(f"{args.date}: {nodes} nodes, {slots} slots, {rows} node-slots\n")
    print("| Added delay (ms) | Late imports (%) | Increase (pp) |")
    print("| ---: | ---: | ---: |")
    print(f"| 0 | {base:.2f} | |")
    for x in added:
        v = late(x)
        print(f"| {x:,} | {v:.2f} | {v - base:.2f} |")


if __name__ == "__main__":
    main()
