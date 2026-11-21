"""File kho v1.2 (Contract): {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]}.

Đọc: từ chối kho đếm kiểu cũ / sai schema / id trùng hoặc rỗng / kind lạ / fresh ngoài [0, 100] (BadInput -> mã 2).
Ghi: sắp theo id, qua file tạm cùng thư mục rồi thay thế, byte-ổn-định.
"""

import json
import math
import os
import tempfile

from .errors import BadInput
from .ids import sort_by_id

KINDS_P1 = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung", "ca_keo", "keo_neo")


def validate_items(items, kinds=KINDS_P1):
    if not isinstance(items, list):
        raise BadInput("items phải là mảng cá thể (v1.2)")
    seen = set()
    out = []
    for it in items:
        if not isinstance(it, dict) or set(it.keys()) != {"id", "kind", "fresh"}:
            raise BadInput("mỗi cá thể trong items phải có đúng khóa id, kind, fresh")
        iid = it["id"]
        if not isinstance(iid, str) or not iid:
            raise BadInput("id cá thể phải là chuỗi khác rỗng")
        if iid in seen:
            raise BadInput(f"id cá thể trùng: {iid}")
        seen.add(iid)
        kind = it["kind"]
        if kind not in kinds:
            raise BadInput(f"nguyên liệu lạ: {kind}")
        fresh = it["fresh"]
        if isinstance(fresh, bool) or not isinstance(fresh, (int, float)) or not math.isfinite(fresh) or not (0 <= fresh <= 100):
            raise BadInput(f"độ tươi không hợp lệ cho {iid}: {fresh!r}")
        out.append({"id": iid, "kind": kind, "fresh": fresh})
    return sort_by_id(out)


def read_inventory(path: str, kinds=KINDS_P1) -> list:
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list) -> list:
    """Khoang (mảng cá thể theo thứ tự nhặt) -> mảng cá thể sắp theo id."""
    return sort_by_id([{"id": it["id"], "kind": it["kind"], "fresh": it["fresh"]} for it in hold])


def write_inventory(path: str, items: list):
    items = sort_by_id([{"id": it["id"], "kind": it["kind"], "fresh": it["fresh"]} for it in items])
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump({"items": items}, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise
