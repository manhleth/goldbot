"""Điểm vào duy nhất.

    python main.py web                                    # giao diện web local (điều khiển mọi chức năng)
    python main.py live                                   # chạy live trên tài khoản DEMO
    python main.py backtest --from 2023-01-01 --to 2025-12-31 [--refresh]
    python main.py report [--db journal/backtest.db] [--run RUN_ID]
    python main.py download --from 2023-01-01 --to 2025-12-31
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import pandas as pd

from core.config import ConfigError, load_config

ROOT = Path(__file__).resolve().parent
log = logging.getLogger("goldbot")


def _use_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")  # console Windows mặc định cp1252


def _setup_logging(command: str) -> None:
    (ROOT / "logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout),
                  logging.FileHandler(ROOT / "logs" / f"{command}.log", encoding="utf-8")],
    )


def _utc(value: str) -> pd.Timestamp:
    return pd.Timestamp(value, tz="UTC")


def cmd_live(cfg: dict, _args) -> int:
    from core.mt5_client import connect
    from execution.live import LiveTrader
    from execution.mt5_broker import DemoAccountRequired
    from journal.db import Journal

    try:
        LiveTrader(cfg, Journal(cfg["journal"]["live_db"]), connect, ROOT).run_forever()
    except DemoAccountRequired as exc:
        log.critical(str(exc))
        return 2
    except KeyboardInterrupt:
        log.info("Dừng theo yêu cầu.")
    return 0


def cmd_backtest(cfg: dict, args) -> int:
    from backtest.runner import run_backtest

    run_id, journal = run_backtest(cfg, _utc(args.start), _utc(args.end), refresh=args.refresh)
    print(_render(journal, run_id, cfg))
    return 0


def _pairs(text: str | None) -> dict[str, float] | None:
    """Chuỗi "a=1,b=2" thành {"a": 1.0, "b": 2.0}."""
    if not text:
        return None
    return {k.strip(): float(v) for k, v in (item.split("=") for item in text.split(","))}


def cmd_playbook(cfg: dict, args) -> int:
    from playbook.runner import run_playbook

    only = [name.strip() for name in args.only.split(",")] if args.only else None
    risk, capital_by = _pairs(args.risk), _pairs(args.capital_by)
    if args.refresh:  # tải lại lịch sử khung gốc từ MT5 trước khi chạy
        cmd_history(cfg, argparse.Namespace(tf=args.base, start=args.refresh_from))
    rows = run_playbook(cfg, Path(args.playbook), _utc(args.start), _utc(args.end), only, args.base,
                        Path(args.data) if args.data else None, args.variant,
                        {"valid_days": args.bias_days, "mode": args.bias_mode} if args.bias_days else None,
                        args.capital, risk, capital_by, json.loads(args.overrides) if args.overrides else None,
                        args.cent)
    print(f"Xong {len(rows)} phương pháp — xem chi tiết từng run trong tab Thống kê.")
    return 0


def cmd_feeds(cfg: dict, args) -> int:
    """Đồng bộ channel: bài mới; --backfill lùi lấy lịch sử; --media tải ảnh; --watch chạy liên tục."""
    import time

    from feeds.store import FeedStore
    from feeds.sync import backfill, download_media, poll_latest
    from feeds.telegram_public import new_client
    from feeds.topics import TopicMatcher

    fc = cfg["feeds"]
    matcher = TopicMatcher(fc["topics"], fc["exclude"])
    channels = [args.channel] if args.channel else fc["channels"]
    if args.export_calls or args.import_calls:
        return _transfer_calls(fc["db"], channels, args.export_calls, args.import_calls)
    with FeedStore(fc["db"]) as store, new_client(fc["timeout_seconds"]) as client:
        while True:
            for channel in channels:
                new = poll_latest(client, store, channel)
                if args.backfill:
                    new += backfill(client, store, channel, fc["request_delay_seconds"], args.max_pages)
                relevant = {int(r.post_id) for r in store.posts(channel).itertuples() if matcher.topics(r.text)}
                media = download_media(client, store, channel, Path(fc["media_dir"]), fc["request_delay_seconds"],
                                       only_ids=relevant) if args.media else 0
                log.info("%s: %d bài mới, %d ảnh mới, tổng %d bài", channel, new, media,
                         len(store.known_ids(channel)))
            if not args.watch:
                return 0
            time.sleep(fc["poll_minutes"] * 60)


def cmd_bot(cfg: dict, args) -> int:
    from core.mt5_client import connect
    from execution.one_bot import OneBot

    if args.name not in cfg["bots"]:
        print(f"Không có bot '{args.name}'. Có: {', '.join(cfg['bots'])}")
        return 1
    OneBot(cfg, args.name, connect, ROOT, dry_run=args.dry_run).run_forever()
    return 0


def cmd_history(cfg: dict, args) -> int:
    """Tải lịch sử dài một khung từ MT5 vào cache (vd cache/XAUUSD_M15_long.csv cho bot ONE)."""
    import pandas as pd

    from core.mt5_client import connect
    from data.history import save_spec, spec_path
    from data.mt5_source import MT5Source

    source = MT5Source(connect(cfg), cfg["symbol"], cfg["data"]["server_time"])
    df = source.fetch_range(args.tf, _utc(args.start), pd.Timestamp.now(tz="UTC"), cfg["data"]["fetch_chunk_bars"])
    out = Path(cfg["data"]["cache_dir"]) / f"{cfg['symbol']}_{args.tf}_long.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.drop(columns="close_time").to_csv(out, index=False)
    save_spec(spec_path(out.parent, cfg["symbol"]), source.symbol_spec())  # thông số hợp đồng thật cho backtest
    print(f"{args.tf}: {len(df)} nến, {df['time'].iat[0]} → {df['time'].iat[-1]} → {out}")
    return 0


def cmd_start_bots(cfg: dict, args) -> int:
    """Khởi động các bot ONE nền (cùng cơ chế với nút trên web, ghi pid để web thấy trạng thái)."""
    from web.services.processes import ManagedProcess

    names = args.names.split(",") if args.names else list(cfg["bots"])
    for name in names:
        proc = ManagedProcess(f"bot_{name}", ROOT, Path(args.config).resolve())
        if proc.is_running():
            print(f"{name}: đang chạy (pid {proc._pid()})")
            continue
        proc.start(["bot", "--name", name])
        print(f"{name}: đã khởi động (pid {proc._pid()}), log: logs/bot_{name}.log")
    return 0


def _transfer_calls(db: str, channels: list[str], export: str | None, imported: str | None) -> int:
    import json

    from feeds.store import FeedStore

    with FeedStore(db) as store:
        if export:
            payload = {ch: json.loads(store.calls(ch).to_json(orient="records", force_ascii=False)) for ch in channels}
            Path(export).parent.mkdir(parents=True, exist_ok=True)
            Path(export).write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            print(f"Đã xuất {sum(len(v) for v in payload.values())} nhãn → {export}")
        if imported:
            payload = json.loads(Path(imported).read_text(encoding="utf-8"))
            for ch, rows in payload.items():
                for row in rows:
                    for col in ("targets", "tools", "fib_levels"):
                        if isinstance(row.get(col), str):
                            row[col] = json.loads(row[col])
                store.save_calls(ch, rows)
            print(f"Đã nhập {sum(len(v) for v in payload.values())} nhãn từ {imported}")
    return 0


def cmd_report(cfg: dict, args) -> int:
    from journal.db import Journal

    journal = Journal(args.db or cfg["journal"]["backtest_db"])
    run_id = args.run or journal.latest_run()
    if run_id is None:
        print("Chưa có run nào trong journal.")
        return 1
    print(_render(journal, run_id, cfg))
    return 0


def cmd_reviews(cfg: dict, args) -> int:
    from journal.reviews import ReviewStore
    from stats.review_report import build

    with ReviewStore(ROOT / cfg["review"]["db"]) as store:
        text = build(store.reviewed(), cfg["review"])
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Đã ghi {args.out}")
    else:
        print(text)
    return 0


def cmd_download(cfg: dict, args) -> int:
    from core.mt5_client import connect
    from data.history import load_history
    from data.mt5_source import MT5Source

    frames, _ = load_history(cfg, _utc(args.start), _utc(args.end), True,
                             lambda: MT5Source(connect(cfg), cfg["symbol"], cfg["data"]["server_time"]))
    for tf, df in frames.items():
        print(f"{tf}: {len(df)} nến, {df['time'].iat[0]} → {df['close_time'].iat[-1]}")
    return 0


def cmd_web(cfg: dict, args) -> int:
    import webbrowser

    import uvicorn

    from web.app import create_app

    host, port = cfg["web"]["host"], args.port or cfg["web"]["port"]
    url = f"http://{'localhost' if host in ('127.0.0.1', '0.0.0.0') else host}:{port}"
    log.info("Giao diện: %s", url)
    if not args.no_browser:
        webbrowser.open(url)
    uvicorn.run(create_app(ROOT, Path(args.config).resolve()), host=host, port=port, log_level="warning")
    return 0


def _render(journal, run_id: str, cfg: dict) -> str:
    from stats.report import build_report, signal_summary

    trades = journal.frame("SELECT * FROM trades WHERE run_id = ? ORDER BY entry_time", [run_id])
    equity = journal.frame("SELECT * FROM equity WHERE run_id = ? ORDER BY time", [run_id])
    signals = journal.frame("SELECT * FROM signals WHERE run_id = ?", [run_id])
    return f"Run: {run_id}\n{signal_summary(signals)}\n\n{build_report(trades, equity, cfg)}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Bot XAUUSD đa khung — chỉ tài khoản DEMO")
    parser.add_argument("--config", default=str(ROOT / "config.yaml"))
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("live").set_defaults(func=cmd_live)
    for name, func in (("backtest", cmd_backtest), ("download", cmd_download)):
        p = sub.add_parser(name)
        p.add_argument("--from", dest="start", required=True)
        p.add_argument("--to", dest="end", required=True)
        if name == "backtest":
            p.add_argument("--refresh", action="store_true", help="tải lại dữ liệu từ MT5")
        p.set_defaults(func=func)
    pp = sub.add_parser("playbook", help="backtest các phương pháp trong playbook.yaml")
    pp.add_argument("--from", dest="start", required=True)
    pp.add_argument("--to", dest="end", required=True)
    pp.add_argument("--only", help="danh sách mã, vd xau01,xau12")
    pp.add_argument("--playbook", default=str(ROOT / "playbook.yaml"))
    pp.add_argument("--base", default="M5", help="khung gốc khớp lệnh (M5 hoặc M15)")
    pp.add_argument("--data", help="file CSV nến khung gốc (mặc định cache)")
    pp.add_argument("--variant", help="biến thể quản lý lệnh trong playbook.yaml (vd hold_h4)")
    pp.add_argument("--bias-days", type=int, help="lọc theo hướng nhận định channel còn hiệu lực N ngày")
    pp.add_argument("--bias-mode", default="strict", choices=["strict", "block_against"])
    pp.add_argument("--capital", type=float, help="vốn ban đầu toàn tài khoản (mỗi phương pháp × capital_share)")
    pp.add_argument("--risk", help="%% rủi ro mỗi lệnh theo phương pháp, vd one_swing=2,one_day=1")
    pp.add_argument("--capital-by", help="vốn riêng từng phương pháp (bỏ capital_share), vd one_swing=700,one_day=300")
    pp.add_argument("--overrides", help='JSON thêm theo phương pháp, vd {"one_swing": {"max_lot": 5, "risk_caps": [[5000, 5]]}}')
    pp.add_argument("--refresh", action="store_true", help="tải lại lịch sử khung gốc từ MT5 trước khi chạy")
    pp.add_argument("--cent", type=float, help="backtest như tài khoản cent: 1 lot cent = N lot thường (vd 0.01)")
    pp.add_argument("--refresh-from", default="2015-01-01")
    pp.set_defaults(func=cmd_playbook)
    hp = sub.add_parser("history", help="tải lịch sử dài một khung từ MT5 vào cache (cho bot ONE)")
    hp.add_argument("--tf", default="M15")
    hp.add_argument("--from", dest="start", default="2015-01-01")
    hp.set_defaults(func=cmd_history)
    sp = sub.add_parser("start-bots", help="khởi động nền các bot ONE trong config (bỏ qua bot đang chạy)")
    sp.add_argument("--names", help="vd swing,day (mặc định: tất cả)")
    sp.set_defaults(func=cmd_start_bots)
    bp = sub.add_parser("bot", help="bot phương pháp ONE trên MT5 demo (vd --name swing / --name day)")
    bp.add_argument("--name", required=True)
    bp.add_argument("--dry-run", action="store_true", help="chạy đủ quy trình nhưng không gửi lệnh")
    bp.set_defaults(func=cmd_bot)
    fp = sub.add_parser("feeds", help="đồng bộ channel Telegram công khai")
    fp.add_argument("--channel")
    fp.add_argument("--backfill", action="store_true", help="lùi lấy toàn bộ bài cũ")
    fp.add_argument("--max-pages", type=int, help="giới hạn số trang khi lùi (mỗi trang ~20 bài)")
    fp.add_argument("--media", action="store_true", help="tải ảnh các bài thuộc feeds.topics (vàng, bạc, dầu)")
    fp.add_argument("--watch", action="store_true", help="chạy liên tục, kiểm tra bài mới mỗi poll_minutes")
    fp.add_argument("--export-calls", help="xuất nhãn nhận định ra file JSON (để chép sang máy khác)")
    fp.add_argument("--import-calls", help="nhập nhãn nhận định từ file JSON")
    fp.set_defaults(func=cmd_feeds)
    wp = sub.add_parser("web", help="giao diện web local")
    wp.add_argument("--port", type=int)
    wp.add_argument("--no-browser", action="store_true")
    wp.set_defaults(func=cmd_web)
    rp = sub.add_parser("report")
    rp.add_argument("--db")
    rp.add_argument("--run")
    rp.set_defaults(func=cmd_report)
    vp = sub.add_parser("reviews", help="xuất nhận xét + nét vẽ tay của từng lệnh (để tìm lỗi lặp lại)")
    vp.add_argument("--out", help="ghi ra file markdown thay vì in")
    vp.set_defaults(func=cmd_reviews)
    return parser


def main(argv: list[str] | None = None) -> int:
    _use_utf8_console()
    os.chdir(ROOT)  # đường dẫn tương đối trong config luôn tính từ thư mục bot
    args = build_parser().parse_args(argv)
    _setup_logging(f"bot_{args.name}" if args.command == "bot" else args.command)
    try:
        cfg = load_config(args.config)
    except ConfigError as exc:
        log.critical("Config lỗi: %s", exc)
        return 2
    return args.func(cfg, args)


if __name__ == "__main__":
    sys.exit(main())
