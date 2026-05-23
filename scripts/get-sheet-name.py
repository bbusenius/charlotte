#!/usr/bin/env python3
"""Print the sheet name at a given 0-based position in an xlsx file."""

import argparse
import sys

import openpyxl


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print the sheet name at a given 0-based position in an xlsx file."
    )
    parser.add_argument("xlsx_path", help="Path to the xlsx workbook")
    parser.add_argument("index", type=int, help="0-based sheet index")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        wb = openpyxl.load_workbook(args.xlsx_path, read_only=True)
    except Exception as exc:
        print(f"failed to open workbook: {exc}", file=sys.stderr)
        return 2
    try:
        sheet_names = wb.sheetnames
    finally:
        wb.close()

    sheet_count = len(sheet_names)
    if args.index < 0 or args.index >= sheet_count:
        print(
            f"sheet index {args.index} out of range; workbook has {sheet_count} sheets",
            file=sys.stderr,
        )
        return 2

    print(sheet_names[args.index])
    return 0


if __name__ == "__main__":
    sys.exit(main())
