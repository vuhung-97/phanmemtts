"""Cấp mã kích hoạt từ dòng lệnh (chạy trên máy owner).

Ví dụ:
    python tools\\license_tool\\license_cli.py -m 7K2QF-9M3XA -k 30
    python tools\\license_tool\\license_cli.py -m 7K2QF-9M3XA -k lifetime --record
    python tools\\license_tool\\license_cli.py -m 7K2QF-9M3XA -k custom --days 90
    python tools\\license_tool\\license_cli.py --list
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import common  # noqa: E402
import ledger  # noqa: E402
from core.licensing import shortcode  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Cấp mã kích hoạt 15 ký tự cho khách",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("-m", "--machine", help="mã máy 10 ký tự khách gửi")
    p.add_argument("-k", "--kind", default="30",
                   choices=sorted(common.KIND_CHOICES),
                   help="loại mã: 7 | 30 | lifetime | custom (mặc định 30)")
    p.add_argument("--days", type=int, help="số ngày khi --kind custom (1..3650)")
    p.add_argument("--customer", default="", help="tên khách")
    p.add_argument("--phone", default="", help="số điện thoại")
    p.add_argument("--note", default="", help="ghi chú")
    p.add_argument("--record", action="store_true", help="ghi vào sổ key")
    p.add_argument("--reissued-from", type=int, default=None,
                   help="id bản ghi cũ nếu cấp lại")
    p.add_argument("--list", action="store_true", help="liệt kê key đã cấp")
    p.add_argument("--json", action="store_true", help="in kết quả dạng JSON")
    p.add_argument("--key-file", help="file secret (mặc định keys/license_secret.bin)")
    return p


def _print_list() -> int:
    rows = ledger.recent(100)
    if not rows:
        print("(sổ key trống)")
        return 0
    print(f"{'ID':>4}  {'Mã máy':<13}  {'Loại':<12}  {'Hạn':<10}  {'Khách':<20}  Mã")
    print("-" * 96)
    for row in rows:
        kind = common.kind_text(int(row["kind"]), int(row["days"] or 0))
        expiry = ("Vĩnh viễn" if row["expiry_day"] is None
                  else _epoch_text(int(row["expiry_day"])))
        print(f"{row['id']:>4}  {common.format_machine(row['machine']):<13}  "
              f"{kind:<12}  {expiry:<10}  {(row['customer'] or '')[:20]:<20}  "
              f"{row['code']}")
    print(f"\nTổng: {ledger.count()} key")
    return 0


def _epoch_text(day_index: int) -> str:
    from datetime import timedelta

    return (shortcode.EPOCH + timedelta(days=int(day_index))).strftime("%d/%m/%Y")


def main() -> int:
    args = _parser().parse_args()

    if args.list:
        return _print_list()

    if not args.machine:
        print("Thiếu --machine (mã máy 10 ký tự của khách). Dùng --list để xem sổ key.")
        return 2

    kind = common.KIND_CHOICES[args.kind]
    days = args.days if kind == shortcode.KIND_CUSTOM else (
        0 if kind == shortcode.KIND_LIFETIME else shortcode.KIND_DAYS[kind])

    try:
        key = common.load_key(Path(args.key_file) if args.key_file else None)
        code, sc = common.create_code(args.machine, kind, days=args.days, key=key)
    except (ValueError, OSError) as exc:
        print(f"[LOI] {exc}")
        return 2

    machine = common.normalize_machine(args.machine)
    expiry = common.expiry_text(sc)
    result = {
        "code": code,
        "machine": common.format_machine(machine),
        "kind": common.kind_text(kind, args.days),
        "expiry": expiry,
        "lifetime": sc.is_lifetime,
    }

    if args.record:
        record_id = ledger.add(
            code=code,
            machine=machine,
            kind=kind,
            days=int(days or 0),
            issued_day=shortcode.day_index(shortcode.utc_today()),
            expiry_day=None if sc.is_lifetime else sc.expiry_day,
            customer=args.customer,
            phone=args.phone,
            note=args.note,
            reissued_from=args.reissued_from,
        )
        result["record_id"] = record_id

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Mã máy      : {result['machine']}")
        print(f"Loại        : {result['kind']}")
        print(f"Mã kích hoạt: {code}")
        print(f"Hạn         : {expiry}")
        if args.record:
            print(f"Đã ghi sổ   : #{result['record_id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
