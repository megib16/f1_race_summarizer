"""Fetch and store circuit maps for races that don't have one yet.

    python backfill_circuits.py                       # races with no stored lookup
    python backfill_circuits.py --retry-unavailable   # also retry lookups that found no data

Uses the network (MultiViewer circuit data via FastF1). Safe to re-run: existing
maps are never overwritten, and a failed lookup stores nothing so it is retried.
"""
import argparse
import sys

import pipeline


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--retry-unavailable", action="store_true")
    args = parser.parse_args(argv)
    missing = pipeline.backfill_circuit_maps(retry_unavailable=args.retry_unavailable)
    print("Races still without a circuit map: " + (", ".join(missing) if missing else "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
