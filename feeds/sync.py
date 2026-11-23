"""Đồng bộ channel: lấy bài mới (thời gian thực), lùi dần lấy bài cũ (lịch sử), tải ảnh."""
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path

import httpx

from feeds.store import FeedStore
from feeds.telegram_public import fetch_page

log = logging.getLogger(__name__)


def poll_latest(client: httpx.Client, store: FeedStore, channel: str) -> int:
    """Trang mới nhất → số bài mới."""
    return store.upsert(fetch_page(client, channel))


def backfill(client: httpx.Client, store: FeedStore, channel: str, delay: float, max_pages: int | None = None,
             sleep: Callable[[float], None] = time.sleep) -> int:
    """Lùi từ bài cũ nhất đã có về đầu channel (hoặc tối đa `max_pages` trang). Tiếp tục được nếu bị ngắt."""
    added, pages = 0, 0
    before = store.oldest_id(channel)
    if before is None:
        added += poll_latest(client, store, channel)
        before = store.oldest_id(channel)
    while before and before > 1 and (max_pages is None or pages < max_pages):
        posts = fetch_page(client, channel, before)
        if not posts:
            break
        added += store.upsert(posts)
        oldest = min(p.post_id for p in posts)
        if oldest >= before:
            break
        before, pages = oldest, pages + 1
        if pages % 20 == 0:
            log.info("%s: đã lùi tới bài %d (%d bài mới)", channel, before, added)
        sleep(delay)
    return added


def download_media(client: httpx.Client, store: FeedStore, channel: str, media_dir: Path, delay: float,
                   sleep: Callable[[float], None] = time.sleep, only_ids: set[int] | None = None) -> int:
    """Tải ảnh còn thiếu (chỉ các bài trong `only_ids` nếu có)."""
    folder = media_dir / channel
    folder.mkdir(parents=True, exist_ok=True)
    count = 0
    for post_id, idx, url in store.missing_media(channel, only_ids):
        response = client.get(url)
        if response.status_code != 200:  # link ảnh hết hạn → tải lại trang chứa bài để lấy link mới
            url = _fresh_photo_url(client, store, channel, post_id, idx)
            response = client.get(url) if url else None
        if response is None or response.status_code != 200:
            log.warning("Không tải được ảnh %d_%d", post_id, idx)
            continue
        path = folder / f"{post_id}_{idx}.jpg"
        path.write_bytes(response.content)
        store.add_media(channel, post_id, idx, url, str(path))
        count += 1
        sleep(delay)
    return count


def _fresh_photo_url(client: httpx.Client, store: FeedStore, channel: str, post_id: int, idx: int) -> str | None:
    posts = fetch_page(client, channel, before=post_id + 1)
    store.upsert(posts)
    match = next((p for p in posts if p.post_id == post_id), None)
    return match.photos[idx] if match is not None and idx < len(match.photos) else None
