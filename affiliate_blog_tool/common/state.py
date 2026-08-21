"""既出テーマの重複投稿を防ぐための、簡易な実行状態の保存。"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from affiliate_blog_tool.common.config import STATE_DIR

STATE_FILE = STATE_DIR / "published_keywords.json"


def _load() -> dict:
    if not STATE_FILE.exists():
        return {}
    return json.loads(STATE_FILE.read_text(encoding="utf-8"))


def _save(data: dict) -> None:
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def is_already_used(target_keyword: str) -> bool:
    return target_keyword in _load()


def mark_used(target_keyword: str, wp_post_id: int | None = None, wp_url: str | None = None) -> None:
    data = _load()
    data[target_keyword] = {
        "used_at": datetime.now(timezone.utc).isoformat(),
        "wp_post_id": wp_post_id,
        "wp_url": wp_url,
    }
    _save(data)


def filter_unused(target_keywords: list[str]) -> list[str]:
    used = set(_load().keys())
    return [k for k in target_keywords if k not in used]
