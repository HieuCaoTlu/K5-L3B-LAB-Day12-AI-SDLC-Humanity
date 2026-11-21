"""File kho. Hai phiên bản (bên đọc chọn theo contract: có khối `freshness` ⇒ v1.2).

v1.0/v1.1 (Contract G): {"items": {kind: số nguyên >= 0}}  — kho đếm theo loại.
v1.2 (Mùa Nước Nổi):    {"items": [{"id": "I1", "kind": "ca_linh", "fresh": 100}, ...]} — kho cá thể.

Đọc: từ chối sai schema / kind lạ / số âm / id trùng / fresh ngoài [0,100] (BadInput -> mã 2).
v1.2 từ chối file kho đếm (và ngược lại).
Ghi: qua file tạm cùng thư mục rồi thay thế nguyên tử, byte-ổn-định.
`fresh` đọc thành Fraction (chính xác, nhánh ở ngưỡng 30 không bị lệch); ghi làm tròn 6 chữ số thập phân.
"""

import json
import math
import os
import tempfile
from fractions import Fraction

from .errors import BadInput
from .ids import id_key

KINDS_P1 = ("ca_loc", "ca_linh", "bong_dien_dien", "bong_sung", "ca_keo", "keo_neo")  # v1.1 thêm ca_keo, keo_neo


def validate_items(items, kinds=KINDS_P1):
    if not isinstance(items, dict):
        raise BadInput("items phải là object")
    out = {}
    for k, v in items.items():
        if k not in kinds:
            raise BadInput(f"nguyên liệu lạ: {k}")
        if isinstance(v, bool) or not isinstance(v, int) or v < 0:
            raise BadInput(f"số lượng không hợp lệ cho {k}: {v!r}")
        if v > 0:
            out[k] = v
    return out


def parse_fresh(v, where="fresh"):
    """Số hữu hạn trong [0,100] -> Fraction (chính xác theo biểu diễn thập phân của số đã đọc)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not (0 <= v <= 100):
        raise BadInput(f"{where} phải là số hữu hạn trong [0, 100], đang là {v!r}")
    return Fraction(str(v))


def validate_item_list(items, kinds=KINDS_P1):
    """Kho cá thể v1.2 -> list {id, kind, fresh: Fraction}. Sai schema / id trùng / kind lạ / fresh sai -> BadInput."""
    if not isinstance(items, list):
        raise BadInput("v1.2: items phải là mảng cá thể {id, kind, fresh}")
    out, seen = [], set()
    for i, it in enumerate(items):
        if not isinstance(it, dict) or set(it) != {"id", "kind", "fresh"}:
            raise BadInput(f"items[{i}] phải có đúng các khóa id, kind, fresh")
        if not isinstance(it["id"], str) or not it["id"]:
            raise BadInput(f"items[{i}].id phải là chuỗi khác rỗng")
        if it["id"] in seen:
            raise BadInput(f"id trùng: {it['id']}")
        seen.add(it["id"])
        if it["kind"] not in kinds:
            raise BadInput(f"nguyên liệu lạ: {it['kind']}")
        out.append({"id": it["id"], "kind": it["kind"], "fresh": parse_fresh(it["fresh"], f"items[{i}].fresh")})
    return out


def read_inventory(path: str, kinds=KINDS_P1, fresh=False):
    """fresh=False: dict đếm theo loại (v1.0/v1.1). fresh=True: list cá thể (v1.2)."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        raise BadInput(f"không đọc được file kho {path}: {e}")
    if not isinstance(data, dict) or set(data.keys()) != {"items"}:
        raise BadInput("file kho chỉ được có khóa gốc 'items'")
    if fresh:
        return validate_item_list(data["items"], kinds)
    return validate_items(data["items"], kinds)


def hold_to_items(hold: list) -> dict:
    """Khoang (mảng id theo thứ tự nhặt) -> object đếm, sắp theo id nguyên liệu."""
    counts = {}
    for k in hold:
        counts[k] = counts.get(k, 0) + 1
    return {k: counts[k] for k in sorted(counts)}


def item_to_json(it) -> dict:
    """Cá thể (fresh có thể là Fraction/số) -> dạng JSON, fresh làm tròn 6 chữ số."""
    return {"id": it["id"], "kind": it["kind"], "fresh": round(float(it["fresh"]), 6)}


def items_to_json(items) -> list:
    """Danh sách cá thể -> mảng JSON sắp theo id (F2 trước F10)."""
    return [item_to_json(it) for it in sorted(items, key=lambda x: id_key(x["id"]))]


def _atomic_write(path: str, obj):
    d = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix=".inv-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, separators=(",", ":"))
            f.write("\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def write_inventory(path: str, items: dict):
    items = {k: items[k] for k in sorted(items) if items[k] > 0}
    _atomic_write(path, {"items": items})


def write_inventory_items(path: str, items):
    """v1.2: ghi kho cá thể (danh sách {id, kind, fresh}); ngất thì truyền [] -> {"items":[]}."""
    _atomic_write(path, {"items": items_to_json(items)})
