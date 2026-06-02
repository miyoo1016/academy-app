#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

from report_import_utils import (
    SHEET_COLS,
    clean_spaces,
    make_sheet_row,
    normalize_bool,
    normalize_grade_for_match,
    parse_month,
    read_csv_rows,
)


DEFAULT_REVIEW_CSV = Path("import_reports/extracted_scores_review.csv")

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")


def load_secrets() -> dict[str, Any]:
    try:
        import streamlit as st

        return {
            "GOOGLE_SHEET_ID": str(st.secrets.get("GOOGLE_SHEET_ID", "") or ""),
            "gcp_service_account": dict(st.secrets.get("gcp_service_account", {})),
        }
    except Exception:
        pass

    secrets_path = Path(".streamlit/secrets.toml")
    if not secrets_path.exists():
        return {}
    try:
        import toml

        data = toml.load(secrets_path)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_scores_worksheet():
    secrets = load_secrets()
    sheet_id = str(secrets.get("GOOGLE_SHEET_ID", "") or "").strip()
    service_account = secrets.get("gcp_service_account") or {}
    if not sheet_id or not service_account:
        raise RuntimeError("Google Sheets secrets를 찾지 못했습니다.")

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(dict(service_account), scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    return sh.worksheet("scores")


def upgrade_sheet_if_needed(ws) -> None:
    data = ws.get("A:O")
    if not data:
        ws.update([SHEET_COLS], range_name="A1:O1", value_input_option="USER_ENTERED")
        return
    header = [str(c).strip() for c in data[0]]
    if "year" in header:
        return

    new_rows = [SHEET_COLS]
    for raw_row in data[1:]:
        if len(raw_row) == 1 and "\t" in raw_row[0]:
            raw_row = raw_row[0].split("\t")
        padded = raw_row + [""] * (len(header) - len(raw_row))
        record = dict(zip(header, padded))
        row_year = str(record.get("year", "")).strip()
        if not row_year:
            created = str(record.get("created_at", "")).strip()
            row_year = created.split("-")[0] if created and "-" in created else ""
        record["year"] = row_year
        new_rows.append([str(record.get(col, "")) for col in SHEET_COLS])

    ws.batch_clear(["A:O"])
    ws.update(new_rows, range_name="A1", value_input_option="USER_ENTERED")


def dedupe_scores_sheet(ws) -> None:
    data = ws.get("A:O")
    if not data or len(data) < 2:
        return

    rows = data[1:]
    groups = defaultdict(list)
    for r in rows:
        if any(str(c).strip() for c in r):
            if len(r) == 1 and "\t" in r[0]:
                r = r[0].split("\t")
            padded = (r + [""] * 15)[:15]
            key = (
                str(padded[1]).strip(),
                str(padded[3]).replace(" ", "").strip(),
                normalize_grade_for_match(padded[4]),
                parse_month(padded[5]),
            )
            groups[key].append(padded)

    deduped_rows = []
    for group_rows in groups.values():
        group_rows.sort(key=lambda x: str(x[0]).strip(), reverse=True)
        deduped_rows.append(group_rows[0])

    if len(deduped_rows) < len(rows):
        last_row = 1 + max(len(rows), len(deduped_rows))
        ws.batch_clear([f"A2:O{last_row}"])
        if deduped_rows:
            ws.update(deduped_rows, range_name=f"A2:O{1 + len(deduped_rows)}", value_input_option="USER_ENTERED")


def sort_scores_sheet(ws) -> None:
    data = ws.get("A:O")
    if not data or len(data) < 2:
        return
    rows = data[1:]
    padded_rows = [
        (r + [""] * 15)[:15]
        for r in rows
        if any(str(c).strip() for c in r)
    ]
    idx = {col: i for i, col in enumerate(SHEET_COLS)}

    def round_int(value: str) -> int:
        text = str(value).strip()
        return int(text) if text.isdigit() else 0

    padded_rows.sort(
        key=lambda r: (
            str(r[idx["year"]]).strip(),
            str(r[idx["student_name"]]).strip().lower(),
            normalize_grade_for_match(r[idx["grade"]]),
            parse_month(r[idx["eval_month"]]),
            str(r[idx["test_name"]]).strip().lower(),
            round_int(r[idx["test_round"]]),
            str(r[idx["created_at"]]).strip(),
        )
    )
    last_row = 1 + max(len(data) - 1, len(padded_rows))
    ws.batch_clear([f"A2:O{last_row}"])
    if padded_rows:
        ws.update(padded_rows, range_name=f"A2:O{1 + len(padded_rows)}", value_input_option="USER_ENTERED")


def row_key(row_values: list[str]) -> tuple[str, str, str, int]:
    return (
        str(row_values[1]).strip(),
        str(row_values[3]).replace(" ", "").strip(),
        normalize_grade_for_match(row_values[4]),
        parse_month(row_values[5]),
    )


def existing_index(ws) -> dict[tuple[str, str, str, int], int]:
    data = ws.get("A:O")
    if data and data[0]:
        header = [str(c).strip() for c in data[0]]
        if header and "year" not in header:
            upgrade_sheet_if_needed(ws)
            data = ws.get("A:O")

    result: dict[tuple[str, str, str, int], int] = {}
    if not data or len(data) < 2:
        return result
    for i, raw_row in enumerate(data[1:], start=2):
        if len(raw_row) == 1 and "\t" in raw_row[0]:
            raw_row = raw_row[0].split("\t")
        padded = (raw_row + [""] * 15)[:15]
        key = row_key(padded)
        if key not in result:
            result[key] = i
    return result


def prepare_rows(review_rows: list[dict], allow_needs_review: bool) -> tuple[list[list[str]], list[str]]:
    prepared: list[list[str]] = []
    errors: list[str] = []
    seen_keys: set[tuple[str, str, str, int]] = set()
    for index, row in enumerate(review_rows, start=2):
        if normalize_bool(row.get("needs_review")) and not allow_needs_review:
            errors.append(f"CSV {index}행: needs_review=True")
            continue

        values = make_sheet_row(row)
        key = row_key(values)
        missing = []
        if not key[0]:
            missing.append("year")
        if not key[1]:
            missing.append("student_name")
        if not key[2]:
            missing.append("grade")
        if not key[3]:
            missing.append("eval_month")
        if missing:
            errors.append(f"CSV {index}행: 고유키 누락({', '.join(missing)})")
            continue
        if not clean_spaces(values[8]):
            errors.append(f"CSV {index}행: score 누락")
            continue

        if key in seen_keys:
            errors.append(f"CSV {index}행: 검수 CSV 내부 중복 키 {key}")
            continue
        seen_keys.add(key)
        prepared.append(values)
    return prepared, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="검수 완료 CSV를 scores 시트에 dry-run 또는 commit upsert 합니다.")
    parser.add_argument("--review-csv", default=str(DEFAULT_REVIEW_CSV), help="검수 CSV 경로")
    parser.add_argument("--commit", action="store_true", help="실제로 Google Sheets에 upsert")
    parser.add_argument("--allow-needs-review", action="store_true", help="needs_review=True 행도 업로드 허용")
    parser.add_argument("--limit", type=int, default=0, help="앞에서부터 N개 행만 처리")
    args = parser.parse_args()

    review_path = Path(args.review_csv)
    if not review_path.exists():
        raise SystemExit(f"검수 CSV가 없습니다: {review_path}")

    review_rows = read_csv_rows(review_path)
    if args.limit and args.limit > 0:
        review_rows = review_rows[: args.limit]

    prepared, errors = prepare_rows(review_rows, args.allow_needs_review)
    print(f"review rows={len(review_rows)}, uploadable={len(prepared)}, blocked={len(errors)}")
    for message in errors[:20]:
        print(f"blocked: {message}")
    if len(errors) > 20:
        print(f"blocked: ... {len(errors) - 20} more")

    if args.commit and errors:
        raise SystemExit("--commit 중단: blocked 행이 있습니다. 검수 후 needs_review를 False로 바꾸거나 --allow-needs-review를 사용하세요.")

    ws = get_scores_worksheet()
    existing = existing_index(ws)
    updates = []
    appends = []
    for values in prepared:
        key = row_key(values)
        if key in existing:
            updates.append((existing[key], values))
        else:
            appends.append(values)

    mode = "COMMIT" if args.commit else "DRY-RUN"
    print(f"{mode}: update={len(updates)}, append={len(appends)}")
    if not args.commit:
        print("dry-run 완료: Google Sheets에는 쓰지 않았습니다.")
        return 0

    upgrade_sheet_if_needed(ws)
    for row_number, values in updates:
        ws.update([values], range_name=f"A{row_number}:O{row_number}", value_input_option="USER_ENTERED")
    for values in appends:
        ws.append_row(values, value_input_option="USER_ENTERED", table_range="A1")

    dedupe_scores_sheet(ws)
    sort_scores_sheet(ws)
    print("commit 완료: upsert 후 dedupe_scores_sheet, sort_scores_sheet 실행")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
