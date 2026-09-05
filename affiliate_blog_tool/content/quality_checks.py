"""公開前の品質チェック（E-E-A-T対策など）。"""
from __future__ import annotations

import re

EXPERIENCE_PLACEHOLDER_RE = re.compile(r"<!--\s*EXPERIENCE:\s*(.+?)\s*-->")


def find_experience_placeholders(body_markdown: str) -> list[str]:
    """本文中に残っている「体験談を書いてください」の目印一覧を返す。

    Googleの評価基準(E-E-A-T)では、AIが書いた一般論だけの記事より、
    筆者本人の一次体験が書かれた記事の方が評価されやすい。
    公開前に、ここで検出されたヒントに沿って自分の体験談を書き足すことを推奨する。
    """
    return [m.group(1) for m in EXPERIENCE_PLACEHOLDER_RE.finditer(body_markdown)]
