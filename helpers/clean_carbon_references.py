#!/usr/bin/env python3
"""
clean_carbon_references.py

Removes faulty tests from a webperf_core result file (e.g. test type 22,
carbon/CO2). A test is considered faulty when its data node contains
"total-byte-weight": -1, which indicates the measurement did not go through.

Example of a faulty node that gets removed:
    "data": {
        "total-byte-weight": -1,
        "co2": -6.028619827702642e-7,
        "cleaner_than": 99
    }

Usage:
    # Dry run - only shows what would be removed, writes nothing:
    python clean_carbon_references.py data/carbon-references.json --dry-run

    # For real - writes back to the same file, taking a .bak copy first:
    python clean_carbon_references.py data/carbon-references.json

    # Write to a new file instead of in-place:
    python clean_carbon_references.py data/carbon-references.json -o data/carbon-references.clean.json
"""

import argparse
import json
import shutil
import sys
from pathlib import Path


# Sentinel value that marks a failed measurement.
BAD_BYTE_WEIGHT = -1


def is_bad_entry(entry):
    """
    Returns True if the entry should be removed.

    We are deliberately conservative: we ONLY remove entries where
    data.total-byte-weight is explicitly -1. A missing data node or a
    missing key does NOT count as faulty (so we don't discard valid data
    by mistake) - it is treated as "uncertain" and kept instead.
    """
    if not isinstance(entry, dict):
        return False
    data = entry.get("data")
    if not isinstance(data, dict):
        return False
    return data.get("total-byte-weight") == BAD_BYTE_WEIGHT


def find_entry_list(doc):
    """
    Locates the list of test results regardless of whether the top level is:
      - a list directly:          [ {...}, {...} ]
      - a dict wrapping it:       { "results": [ {...}, ... ] } (or a similar key)

    Returns a tuple (container, key) where:
      - container[key] is the list, or
      - (doc, None) if the top level already is the list.
    Raises ValueError if no list is found.
    """
    if isinstance(doc, list):
        return doc, None

    if isinstance(doc, dict):
        # Find the first key whose value is a list of dict objects.
        for key, value in doc.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                return doc, key
        # Empty dict or no lists - fall through to a clear error.
    raise ValueError(
        "Could not find a list of test results at the top level. "
        "Expected a JSON list or a dict wrapping a list."
    )


def clean(entries):
    """Splits the entries into (kept, removed)."""
    kept, removed = [], []
    for entry in entries:
        (removed if is_bad_entry(entry) else kept).append(entry)
    return kept, removed


def describe(entry):
    """Short description of an entry for logging."""
    if not isinstance(entry, dict):
        return repr(entry)
    site_id = entry.get("site_id", "?")
    data = entry.get("data", {}) if isinstance(entry.get("data"), dict) else {}
    co2 = data.get("co2", "?")
    return f"site_id={site_id}  co2={co2}"


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Removes faulty CO2 tests (total-byte-weight == -1) from a webperf_core result file."
    )
    parser.add_argument("input", type=Path, help="Path to the JSON file, e.g. data/carbon-references.json")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Write the result to this file instead of in-place.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Only show what would be removed; write no file.",
    )
    parser.add_argument(
        "--no-backup", action="store_true",
        help="Do NOT create a .bak copy on in-place writes (not recommended).",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="List every removed entry.",
    )
    args = parser.parse_args(argv)

    if not args.input.is_file():
        parser.error(f"File does not exist: {args.input}")

    try:
        doc = json.loads(args.input.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        parser.error(f"Could not parse JSON in {args.input}: {exc}")

    try:
        container, key = find_entry_list(doc)
    except ValueError as exc:
        parser.error(str(exc))

    entries = container if key is None else container[key]
    total = len(entries)
    kept, removed = clean(entries)

    print(f"Total entries:    {total}")
    print(f"Faulty (removed): {len(removed)}")
    print(f"Kept:             {len(kept)}")

    if args.verbose and removed:
        print("\nRemoved entries:")
        for entry in removed:
            print(f"  - {describe(entry)}")

    if not removed:
        print("\nNo faulty entries found - nothing to do.")
        return 0

    if args.dry_run:
        print("\n[dry-run] No file was written.")
        return 0

    # Rebuild the cleaned document with the same top-level structure as the original.
    if key is None:
        new_doc = kept
    else:
        container[key] = kept
        new_doc = container

    target = args.output if args.output is not None else args.input

    # Backup on in-place writes.
    if args.output is None and not args.no_backup:
        backup = args.input.with_suffix(args.input.suffix + ".bak")
        shutil.copy2(args.input, backup)
        print(f"\nBackup created: {backup}")

    target.write_text(
        json.dumps(new_doc, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote cleaned file: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
