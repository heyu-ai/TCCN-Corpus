"""
依 corpus_schema.json 驗證語料記錄（單筆 dict 或 JSONL 檔案）。

CLI 用法：
    python -m schemas.validate data/raw/moc_ogd.jsonl [more.jsonl ...]

驗證失敗時印出帶欄位路徑的錯誤並回傳 exit code 1，用於鎖定 schema、
讓任何爬蟲產出都必須與 schemas/corpus_schema.json 對齊。
"""
from __future__ import annotations

import argparse
import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

import jsonschema
from jsonschema import Draft7Validator

SCHEMA_PATH = Path(__file__).with_name("corpus_schema.json")


@lru_cache(maxsize=1)
def load_schema() -> dict[str, Any]:
    """讀取並快取 corpus_schema.json。"""
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _validator() -> Draft7Validator:
    """
    建立並快取單一 validator，避免每筆記錄重跑 schema meta-validation。

    傳入 FORMAT_CHECKER 才會真正驗證 schema 宣告的 `format`（uri / date-time）；
    這些 checker 由 jsonschema[format-nongpl] 的 rfc3986-validator / rfc3339-validator 提供。
    """
    return Draft7Validator(load_schema(), format_checker=Draft7Validator.FORMAT_CHECKER)


def validate_record(record: dict[str, Any]) -> None:
    """驗證單筆記錄，不符 schema（含 format）時拋出 jsonschema.ValidationError。"""
    _validator().validate(record)


def _format_error(line_no: int, error: jsonschema.ValidationError) -> str:
    location = "/".join(str(part) for part in error.absolute_path) or "(root)"
    return f"第 {line_no} 行 [{location}]：{error.message}"


def validate_jsonl(path: Path) -> tuple[int, list[str]]:
    """
    逐行驗證 JSONL 檔案。

    回傳 (通過筆數, 錯誤訊息列表)。空行會被略過；無法解析的 JSON 亦記為錯誤。
    """
    passed = 0
    errors: list[str] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"第 {line_no} 行：JSON 解析失敗：{exc}")
                continue
            try:
                validate_record(record)
            except jsonschema.ValidationError as exc:
                errors.append(_format_error(line_no, exc))
            else:
                passed += 1
    return passed, errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="依 corpus_schema.json 驗證 JSONL 語料檔。")
    parser.add_argument("paths", nargs="+", help="待驗證的 JSONL 檔案路徑")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    total_passed = 0
    total_errors = 0
    for raw_path in args.paths:
        path = Path(raw_path)
        if not path.exists():
            print(f"[FAIL] 找不到檔案：{path}")
            total_errors += 1
            continue
        passed, errors = validate_jsonl(path)
        total_passed += passed
        total_errors += len(errors)
        status = "OK" if not errors else "FAIL"
        print(f"[{status}] {path}：通過 {passed} 筆，錯誤 {len(errors)} 筆")
        for message in errors:
            print(f"    - {message}")
    print(f"總計：通過 {total_passed} 筆，錯誤 {total_errors} 筆")
    return 1 if total_errors else 0


if __name__ == "__main__":
    sys.exit(main())
