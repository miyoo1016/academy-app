#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from report_import_utils import INVENTORY_COLS, guess_from_filename, iter_report_files, nfc, write_csv_rows


DEFAULT_INPUT_DIR = Path("import_reports/2026_03_04")
DEFAULT_OUTPUT = Path("import_reports/report_inventory.csv")


def build_inventory(input_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for path in iter_report_files(input_dir):
        guessed = guess_from_filename(path)
        rows.append(
            {
                "source_file": nfc(str(path)),
                "guessed_student_name": guessed["guessed_student_name"],
                "guessed_month": guessed["guessed_month"],
                "file_ext": guessed["file_ext"],
                "needs_review": str(bool(guessed["needs_review"])),
                "note": guessed["note"],
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="성적표 파일 목록과 파일명 기반 이름/월 후보를 CSV로 저장합니다.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR), help="성적표 파일 폴더")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="inventory CSV 경로")
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        raise SystemExit(f"입력 폴더가 없습니다: {input_dir}")

    rows = build_inventory(input_dir)
    write_csv_rows(args.output, rows, INVENTORY_COLS)

    review_count = sum(1 for row in rows if row["needs_review"] == "True")
    print(f"saved {args.output} ({len(rows)} files, needs_review={review_count})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

