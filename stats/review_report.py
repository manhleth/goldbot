"""Báo cáo nhận xét của người dùng (vẽ tay + lỗi sai) để tìm lỗi lặp lại, rồi sửa quy tắc và backtest lại."""
from __future__ import annotations

from collections import Counter

import pandas as pd


def _labels(options: list[dict]) -> dict[str, str]:
    return {o["key"]: o["label"] for o in options}


def _when(seconds: int) -> str:
    return f"{pd.Timestamp(seconds, unit='s', tz='UTC'):%Y-%m-%d %H:%M}"


def _shape_line(shape: dict, roles: dict[str, str]) -> str:
    pts = " → ".join(f"{_when(p['t'])} @ {p['p']:.2f}" for p in shape["points"])
    return f"{roles.get(shape['role'], shape['role'])} · {shape['kind']}: {pts}"


def _counts(title: str, counter: Counter, labels: dict[str, str]) -> list[str]:
    if not counter:
        return []
    return [f"## {title}", "", *[f"- {labels.get(k, k)}: {n}" for k, n in counter.most_common()], ""]


def build(rows: list[dict], cfg: dict) -> str:
    """Markdown: tổng hợp kết luận/lỗi (kèm R trung bình theo lỗi) + chi tiết từng lệnh (nét vẽ theo giờ UTC)."""
    verdicts, errors, roles = (_labels(cfg[k]) for k in ("verdicts", "error_tags", "roles"))
    if not rows:
        return "Chưa có lệnh nào được nhận xét."
    by_verdict = Counter(r["verdict"] or "none" for r in rows)
    by_error = Counter(e for r in rows for e in r["errors"] or [])
    r_by_error: dict[str, list[float]] = {}
    for r in rows:
        for e in r["errors"] or []:
            if (r["snapshot"] or {}).get("r") is not None:
                r_by_error.setdefault(e, []).append(r["snapshot"]["r"])
    out = [f"# Nhận xét lệnh ({len(rows)})", ""]
    out += _counts("Kết luận", by_verdict, {**verdicts, "none": "Chưa xét"})
    out += _counts("Lỗi sai", by_error, errors)
    if r_by_error:
        out += ["## R trung bình theo lỗi (lệnh đã đóng)", ""]
        out += [f"- {errors.get(k, k)}: {sum(v) / len(v):+.2f}R trên {len(v)} lệnh" for k, v in r_by_error.items()]
        out.append("")
    out += ["## Chi tiết", ""]
    for r in rows:
        snap = r["snapshot"] or {}
        head = " · ".join(str(x) for x in (snap.get("setup_key") or r["scope"], snap.get("direction"),
                                           snap.get("entry_time"), f"{snap['r']:+.2f}R" if snap.get("r") is not None
                                           else None) if x)
        out.append(f"### {head}")
        out.append(f"- Kết luận: {verdicts.get(r['verdict'], 'Chưa xét')}")
        if r["errors"]:
            out.append(f"- Lỗi: {', '.join(errors.get(e, e) for e in r['errors'])}")
        if r["note"]:
            out.append(f"- Ghi chú: {r['note']}")
        if snap.get("entry") is not None:
            out.append(f"- Vào {snap['entry']} · SL {snap.get('sl')} · TP {snap.get('tp')} · thoát: {snap.get('exit_reason')}")
        out += [f"- Nét vẽ: {_shape_line(s, roles)}" for s in r["shapes"] or []]
        out.append("")
    return "\n".join(out)
