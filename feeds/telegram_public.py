"""Đọc trang xem trước công khai của channel Telegram (https://t.me/s/<channel>), không cần đăng nhập.

Mỗi trang ~20 bài; `?before=<id>` lấy các bài cũ hơn id đó. Chỉ dùng cho channel công khai.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

import httpx
import pandas as pd

BASE = "https://t.me/s/{channel}"
USER_AGENT = "Mozilla/5.0 (compatible; gold-bot feed reader)"

_SPLIT = re.compile(r'<div class="tgme_widget_message_wrap')
_POST = re.compile(r'data-post="([^/"]+)/(\d+)"')
_TIME = re.compile(r'<time datetime="([^"]+)"')
_PHOTO = re.compile(r"tgme_widget_message_photo_wrap[^>]*background-image:url\('([^']+)'\)")
_VIEWS = re.compile(r'tgme_widget_message_views">([^<]+)<')
_TEXT = re.compile(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>\s*(?:<div class="tgme_widget_message_(?:'
                   r'reactions|footer|link_preview)|</div>)', re.S)
_TAG = re.compile(r"<[^>]+>")


@dataclass(frozen=True)
class Post:
    channel: str
    post_id: int
    time: pd.Timestamp
    text: str
    photos: tuple[str, ...] = field(default_factory=tuple)
    views: str = ""
    edited: bool = False

    @property
    def url(self) -> str:
        return f"https://t.me/{self.channel}/{self.post_id}"


def _clean(fragment: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", fragment)
    return html.unescape(_TAG.sub("", text)).strip()


def parse_page(page: str) -> list[Post]:
    posts: list[Post] = []
    for block in _SPLIT.split(page)[1:]:
        ident, when = _POST.search(block), _TIME.search(block)
        if ident is None or when is None:
            continue
        text = _TEXT.search(block)
        views = _VIEWS.search(block)
        posts.append(Post(
            channel=ident.group(1), post_id=int(ident.group(2)),
            time=pd.Timestamp(when.group(1)).tz_convert("UTC"),
            text=_clean(text.group(1)) if text else "",
            photos=tuple(_PHOTO.findall(block)),
            views=views.group(1).strip() if views else "",
            edited="tgme_widget_message_meta" in block and ">edited<" in block,
        ))
    return posts


def fetch_page(client: httpx.Client, channel: str, before: int | None = None) -> list[Post]:
    params = {"before": before} if before else None
    response = client.get(BASE.format(channel=channel), params=params)
    response.raise_for_status()
    return parse_page(response.text)


def new_client(timeout: float) -> httpx.Client:
    return httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=timeout, follow_redirects=True)
