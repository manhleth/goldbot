"""Điểm vào duy nhất.

    python main.py web                                    # giao diện web local (điều khiển mọi chức năng)
    python main.py live                                   # chạy live trên tài khoản DEMO
    python main.py backtest --from 2023-01-01 --to 2025-12-31 [--refresh]
    python main.py report [--db journal/backtest.db] [--run RUN_ID]
    python main.py download --from 2023-01-01 --to 2025-12-31
"""
from __future__ import annotations

import argparse
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


def cmd_playbook(cfg: dict, args) -> int:
    from playbook.runner import run_playbook

    only = [name.strip() for name in args.only.split(",")] if args.only else None
    rows = run_playbook(cfg, Path(args.playbook), _utc(args.start), _utc(args.end), only, args.base,
                        Path(args.data) if args.data else None, args.variant,
                        {"valid_days": args.bias_days, "mode": args.bias_mode} if args.bias_days else None)
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


def cmd_report(cfg: dict, args) -> int:
    from journal.db import Journal

    journal = Journal(args.db or cfg["journal"]["backtest_db"])
    run_id = args.run or journal.latest_run()
    if run_id is None:
        print("Chưa có run nào trong journal.")
        return 1
    print(_render(journal, run_id, cfg))
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
    pp.set_defaults(func=cmd_playbook)
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
    fp.set_defaults(func=cmd_feeds)
    wp = sub.add_parser("web", help="giao diện web local")
    wp.add_argument("--port", type=int)
    wp.add_argument("--no-browser", action="store_true")
    wp.set_defaults(func=cmd_web)
    rp = sub.add_parser("report")
    rp.add_argument("--db")
    rp.add_argument("--run")
    rp.set_defaults(func=cmd_report)
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
