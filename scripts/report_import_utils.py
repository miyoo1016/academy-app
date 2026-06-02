from __future__ import annotations

import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Iterable


SUPPORTED_EXTS = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}

SHEET_COLS = [
    "created_at",
    "year",
    "teacher_name",
    "student_name",
    "grade",
    "eval_month",
    "test_name",
    "test_round",
    "score",
    "class_avg",
    "total_students",
    "rank",
    "weak_points",
    "ai_comment",
    "memo",
]

REVIEW_COLS = SHEET_COLS + [
    "source_file",
    "source_page",
    "needs_review",
    "extraction_note",
]

INVENTORY_COLS = [
    "source_file",
    "guessed_student_name",
    "guessed_month",
    "file_ext",
    "needs_review",
    "note",
]


def nfc(value: object) -> str:
    return unicodedata.normalize("NFC", str(value or ""))


def clean_spaces(value: object) -> str:
    return re.sub(r"\s+", " ", nfc(value)).strip()


def parse_month(value: object) -> int:
    text = nfc(value).strip()
    if not text:
        return 0
    match = re.search(r"(?:^|[^0-9])0?([1-9]|1[0-2])\s*월", text)
    if match:
        return int(match.group(1))
    if "-" in text:
        for part in text.split("-"):
            try:
                month = int(part)
            except ValueError:
                continue
            if 1 <= month <= 12:
                return month
    try:
        month = int(re.sub(r"[^0-9]", "", text))
    except ValueError:
        return 0
    return month if 1 <= month <= 12 else 0


def normalize_grade_for_match(raw: object) -> str:
    text = nfc(raw).strip().replace(" ", "")
    if not text:
        return ""

    compact = text.replace("초등학교", "초등").replace("초등", "초")
    compact = compact.replace("학년", "")
    match = re.fullmatch(r"초?([1-6])", compact)
    if match:
        return f"초등{match.group(1)}학년"

    middle = text.replace("중학교", "중").replace("중등", "중").replace("학년", "")
    match = re.fullmatch(r"중([1-3])", middle)
    if match:
        return f"중학교{match.group(1)}학년"

    return text.lower()


def format_month(month: object) -> str:
    parsed = parse_month(month)
    return f"{parsed}월" if parsed else ""


def guess_from_filename(path: str | Path) -> dict[str, str | bool]:
    p = Path(path)
    stem = nfc(p.stem)
    ext = nfc(p.suffix.lower())

    month_matches = re.findall(r"(?<![0-9])0?([34])\s*월", stem)
    unique_months = sorted(set(month_matches))
    guessed_month = f"{unique_months[0]}월" if len(unique_months) == 1 else ""

    name_text = stem
    name_text = re.sub(r"20\d{2}\s*년?", " ", name_text)
    name_text = re.sub(r"(?<![0-9])0?[34]\s*월", " ", name_text)
    for token in ("성적표", "출력본", "미래학원", "수학", "report", "score"):
        name_text = re.sub(token, " ", name_text, flags=re.IGNORECASE)
    name_text = re.sub(r"[_\-\(\)\[\]\{\},.]+", " ", name_text)
    name_text = re.sub(r"[0-9A-Za-z]+", " ", name_text)
    candidates = re.findall(r"[가-힣]{2,5}", name_text)
    guessed_name = candidates[0] if candidates else ""

    notes: list[str] = []
    if not guessed_name:
        notes.append("파일명에서 원생명 후보를 찾지 못함")
    if not guessed_month:
        notes.append("파일명에서 3월/4월을 확정하지 못함")
    if len(unique_months) > 1:
        notes.append("파일명에 월 후보가 여러 개 있음")

    return {
        "guessed_student_name": guessed_name,
        "guessed_month": guessed_month,
        "file_ext": ext.lstrip("."),
        "needs_review": bool(notes),
        "note": "; ".join(notes),
    }


def iter_report_files(input_dir: str | Path) -> Iterable[Path]:
    base = Path(input_dir)
    for path in sorted(base.iterdir(), key=lambda item: nfc(item.name)):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            yield path


def read_csv_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def write_csv_rows(path: str | Path, rows: list[dict], fieldnames: list[str]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def resolve_source_file(source_file: str, input_dir: str | Path) -> Path:
    source = Path(nfc(source_file))
    if source.exists():
        return source
    base = Path(input_dir)
    direct = base / source.name
    if direct.exists():
        return direct
    wanted = nfc(source.name)
    for candidate in iter_report_files(base):
        if nfc(candidate.name) == wanted:
            return candidate
    return direct


def now_kst_string() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_bool(value: object) -> bool:
    return nfc(value).strip().lower() in {"1", "true", "t", "yes", "y", "검수", "필요"}


def normalize_score(value: object) -> str:
    text = nfc(value).strip()
    if not text:
        return ""
    match = re.search(r"\d+(?:\.\d+)?", text.replace(",", ""))
    return match.group(0) if match else ""


def make_sheet_row(row: dict[str, object], created_at: str | None = None) -> list[str]:
    values = {col: clean_spaces(row.get(col, "")) for col in SHEET_COLS}
    values["created_at"] = created_at or values.get("created_at") or now_kst_string()
    values["year"] = values.get("year") or "2026"
    values["eval_month"] = format_month(values.get("eval_month"))
    values["score"] = normalize_score(values.get("score"))
    values["class_avg"] = normalize_score(values.get("class_avg"))
    values["total_students"] = normalize_score(values.get("total_students"))
    values["rank"] = normalize_score(values.get("rank"))
    return [values[col] for col in SHEET_COLS]
