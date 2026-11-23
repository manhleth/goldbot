"""Nạp và kiểm tra config.yaml."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

from core.timeframes import TF_MINUTES

REQUIRED_SECTIONS = (
    "symbol", "account", "mt5", "timeframes", "data", "structure", "bias", "fvg", "order_block",
    "sweep", "trendline", "sr_flip", "confluence", "trigger", "filters", "risk", "management",
    "backtest", "live", "journal", "stats", "news", "web", "sessions", "ict", "range_breakout", "feeds", "enabled_setups",
)
FORECAST_RULES = ("off", "block_against", "require_aligned")
SIZING_MODES = ("fixed_money", "percent")
TP1_MODES = ("fixed_rr", "nearest", "first_valid")
SL_ANCHORS = ("invalidation", "zone")
BIAS_METHODS = ("indicators", "smc")
NON_SESSION_POOLS = ("pdh_pdl", "swing", "equal")  # loại thanh khoản không phải range của một phiên


class ConfigError(ValueError):
    pass


def load_config(path: str | Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    validate(cfg)
    return cfg


def validate(cfg: dict) -> None:
    missing = [key for key in REQUIRED_SECTIONS if key not in cfg]
    if missing:
        raise ConfigError(f"config thiếu mục: {', '.join(missing)}")
    if cfg["account"].get("require_demo") is not True:
        raise ConfigError("account.require_demo phải là true — bot chỉ chạy trên tài khoản demo")
    unknown = [tf for tf in timeframes(cfg) if tf not in TF_MINUTES]
    if unknown:
        raise ConfigError(f"khung thời gian không hỗ trợ: {unknown}")
    for tf in timeframes(cfg):
        for section in ("history_bars", "window_bars"):
            if tf not in cfg["data"][section]:
                raise ConfigError(f"data.{section} thiếu khung {tf}")
        if tf not in cfg["structure"]["fractal_n"]:
            raise ConfigError(f"structure.fractal_n thiếu khung {tf}")
    if cfg["bias"]["slope_ema"] not in cfg["structure"]["ema"]:
        raise ConfigError("bias.slope_ema phải nằm trong structure.ema")
    if cfg["bias"]["method"] not in BIAS_METHODS:
        raise ConfigError(f"bias.method phải là một trong {BIAS_METHODS}")
    windows = cfg["sessions"]["windows"]
    referenced = [*cfg["risk"]["entry_sessions"], *cfg["ict"]["killzones"], cfg["ict"]["asian_session"],
                  *(k for k in [*cfg["ict"]["sweep_pools"], *cfg["ict"]["target_pools"]] if k not in NON_SESSION_POOLS)]
    missing_sessions = sorted({name for name in referenced if name not in windows})
    if missing_sessions:
        raise ConfigError(f"phiên chưa khai báo trong sessions.windows: {missing_sessions}")
    if cfg["risk"]["sizing"] not in SIZING_MODES:
        raise ConfigError(f"risk.sizing phải là một trong {SIZING_MODES}")
    if cfg["risk"]["tp1_mode"] not in TP1_MODES:
        raise ConfigError(f"risk.tp1_mode phải là một trong {TP1_MODES}")
    if cfg["risk"]["sl_anchor"] not in SL_ANCHORS:
        raise ConfigError(f"risk.sl_anchor phải là một trong {SL_ANCHORS}")
    if cfg["news"]["forecast_rule"] not in FORECAST_RULES:
        raise ConfigError(f"news.forecast_rule phải là một trong {FORECAST_RULES}")


def confirm_timeframes(cfg: dict) -> list[str]:
    """Các khung tìm nến xác nhận, ưu tiên theo thứ tự khai báo; mặc định = khung vào lệnh."""
    tfs = cfg["timeframes"]
    return list(tfs.get("confirm") or [tfs["trigger"]])


def timeframes(cfg: dict) -> list[str]:
    """Các khung dùng tới, theo thứ tự từ lớn tới nhỏ, không trùng."""
    tfs = cfg["timeframes"]
    ordered = [*tfs["bias"], tfs["setup"], *confirm_timeframes(cfg), tfs["trigger"]]
    return list(dict.fromkeys(ordered))


def config_hash(cfg: dict) -> str:
    payload = json.dumps(cfg, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:12]
