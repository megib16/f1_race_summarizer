"""List and selectively regenerate race summaries written under an older prompt.

Safe by default: with no flags this only LISTS stale summaries and makes no model
calls and no writes. Regeneration needs --apply, and an existing summary is only
overwritten after a new one was generated successfully.

    python regenerate_summaries.py                       # dry run: list stale summaries
    python regenerate_summaries.py --apply --ids 146,147 # regenerate those races
    python regenerate_summaries.py --apply --limit 2     # regenerate the 2 oldest stale ones
    python regenerate_summaries.py --apply               # regenerate all stale summaries
"""
import argparse
import sys

import summarizer
from database import SessionLocal


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--apply", action="store_true", help="make live model calls and overwrite stale summaries")
    parser.add_argument("--ids", help="comma-separated race_ids to regenerate (default: all stale)")
    parser.add_argument("--limit", type=int, help="regenerate at most this many")
    args = parser.parse_args(argv)
    race_ids = [int(i) for i in args.ids.split(",")] if args.ids else None

    db = SessionLocal()
    try:
        stale = summarizer.find_stale_summaries(db)
        print(f"Current prompt version: {summarizer.PROMPT_VERSION}. Stale summaries: {len(stale)}")
        for race, version in stale:
            print(f"  race_id={race.race_id} round={race.round} {race.date} {race.name} (prompt v{version})")
    finally:
        db.close()

    if not args.apply:
        print("Dry run: nothing changed. Re-run with --apply to regenerate (makes live API calls).")
        return 0

    regenerated, failed = summarizer.regenerate_stale_summaries(race_ids=race_ids, limit=args.limit)
    print(f"Regenerated: {len(regenerated)}  Failed (old summary kept, still stale): {len(failed)}")
    for name in failed:
        print(f"  failed: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
