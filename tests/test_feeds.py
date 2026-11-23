"""Đọc trang t.me/s/<channel> (HTML tự dựng) và lưu idempotent."""
import pytest
from feeds.store import FeedStore
from feeds.sync import backfill
from feeds.telegram_public import parse_page

PAGE = """
<a href="/s/Chan?before=10">older</a>
<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message" data-post="Chan/10">
<a class="tgme_widget_message_photo_wrap 1 2" href="https://t.me/Chan/10" style="width:800px;background-image:url('https://cdn/x.jpg')">
</a><div class="tgme_widget_message_text js-message_text" dir="auto">Vàng điều chỉnh về <b>3370</b><br/>Fib 50%</div>
<div class="tgme_widget_message_footer"><span class="tgme_widget_message_views">2.6K</span>
<time datetime="2026-11-20T08:13:00+00:00" class="time">08:13</time></div></div></div>
<div class="tgme_widget_message_wrap js-widget_message_wrap"><div class="tgme_widget_message" data-post="Chan/11">
<div class="tgme_widget_message_footer"><time datetime="2026-11-20T09:00:00+07:00" class="time">09:00</time></div></div></div>
"""


def test_parse_page_extracts_text_photo_time():
    posts = parse_page(PAGE)
    assert [p.post_id for p in posts] == [10, 11]
    first = posts[0]
    assert first.text == "Vàng điều chỉnh về 3370\nFib 50%" and first.photos == ("https://cdn/x.jpg",)
    assert first.views == "2.6K" and str(first.time) == "2026-11-20 08:13:00+00:00"
    assert str(posts[1].time) == "2026-11-20 02:00:00+00:00" and posts[1].text == ""


class _FakeClient:
    """Trả trang theo before: None → bài 10-11, 10 → bài 8-9, 8 → rỗng."""
    def __init__(self):
        self.calls = []

    def get(self, url, params=None):
        before = (params or {}).get("before")
        self.calls.append(before)
        ids = {None: (10, 11), 10: (8, 9)}.get(before, ())
        body = "".join(f'<div class="tgme_widget_message_wrap"><div data-post="Chan/{i}">'
                       f'<time datetime="2026-11-0{i % 9 + 1}T00:00:00+00:00"></time></div></div>' for i in ids)
        return type("R", (), {"text": body, "raise_for_status": lambda self: None})()


def test_backfill_walks_back_and_is_idempotent(tmp_path):
    with FeedStore(tmp_path / "f.db") as store:
        client = _FakeClient()
        assert backfill(client, store, "Chan", delay=0, sleep=lambda s: None) == 4
        assert store.known_ids("Chan") == {8, 9, 10, 11}
        assert backfill(client, store, "Chan", delay=0, sleep=lambda s: None) == 0  # đã có hết


def test_topic_matcher_keywords_and_exclusions():
    from feeds.topics import TopicMatcher
    m = TopicMatcher({"gold": ["vàng", "xau"], "silver": ["bạc"], "oil": ["dầu", "wti"]}, ["cờ bạc", "cậu vàng"])
    assert m.topics("Vàng có thể điều chỉnh về 3370") == ["gold"]
    assert m.topics("XAU và bạc cùng giảm, WTI tăng") == ["gold", "silver", "oil"]
    assert m.topics("Cậu vàng hôm nay") == [] and m.topics("đừng cờ bạc") == []
    assert m.topics("saudi") == []  # không khớp giữa từ


def test_verify_call_direction_target_and_r():
    import pandas as pd
    from feeds.verify import Call, evaluate
    times = pd.date_range("2026-01-01", periods=10, freq="1D", tz="UTC")
    closes = [100, 101, 103, 106, 104, 108, 111, 109, 112, 115]
    prices = pd.DataFrame({"time": times, "open": closes, "high": [c + 1 for c in closes],
                           "low": [c - 1 for c in closes], "close": closes})
    call = Call(1, times[0] - pd.Timedelta(hours=1), "XAUUSD", "up", (110.0, 120.0), 95.0, True)
    out = evaluate(call, prices, {"3d": pd.Timedelta(days=3)}, max_days=30)
    assert out["ref_price"] == 100 and out["ret_3d"] == pytest.approx(3.0)  # mốc 3 ngày sau giờ đăng → nến đóng 103
    assert out["outcome"] == "target" and out["target"] == 110.0 and out["r"] == pytest.approx(2.0)
    wrong = evaluate(Call(2, call.time, "XAUUSD", "down", (90.0,), 103.0, True), prices, {}, max_days=30)
    assert wrong["outcome"] == "invalidated" and wrong["r"] == -1.0
