"""パイプライン全体で共有するデータ構造。"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum


class Vertical(str, Enum):
    PARENTING = "育児"
    FISHING = "釣り"
    UNKNOWN = "不明"


# ブログの2大ジャンルを判定するための簡易キーワード辞書。
# 実運用では記事カテゴリやWordPressのタクソノミーと突き合わせて精度を上げる。
VERTICAL_KEYWORDS = {
    Vertical.PARENTING: [
        "育児", "子育て", "赤ちゃん", "新生児", "離乳食", "保育園", "幼稚園",
        "抱っこ紐", "ベビーカー", "おむつ", "授乳", "寝かしつけ", "ワンオペ",
        "子供服", "知育", "チャイルドシート",
    ],
    Vertical.FISHING: [
        "釣り", "釣果", "ルアー", "リール", "ロッド", "仕掛け", "堤防釣り",
        "船釣り", "エギング", "アジング", "バス釣り", "渓流釣り", "餌",
        "タックル", "偏光グラス", "クーラーボックス",
    ],
}


def classify_vertical(text: str) -> Vertical:
    for vertical, keywords in VERTICAL_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return vertical
    return Vertical.UNKNOWN


@dataclass
class KeywordOpportunity:
    """GSC実績 + Trendsの伸び を組み合わせた「狙い目キーワード」1件分。"""

    query: str
    vertical: Vertical
    impressions: int = 0
    clicks: int = 0
    ctr: float = 0.0
    position: float = 0.0
    trend_score: float = 0.0  # Google Trendsの relative interest (0-100) or rising指標
    trend_is_rising: bool = False
    source_page: str | None = None
    opportunity_score: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["vertical"] = self.vertical.value
        return d


@dataclass
class ArticleTheme:
    """記事化する1テーマ。"""

    title: str
    target_keyword: str
    vertical: Vertical
    search_intent: str
    related_keywords: list[str] = field(default_factory=list)
    opportunity_score: float = 0.0
    notes: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["vertical"] = self.vertical.value
        return d


@dataclass
class GeneratedArticle:
    theme: ArticleTheme
    meta_title: str
    meta_description: str
    body_markdown: str
    excerpt: str
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "theme": self.theme.to_dict(),
            "meta_title": self.meta_title,
            "meta_description": self.meta_description,
            "body_markdown": self.body_markdown,
            "excerpt": self.excerpt,
            "tags": self.tags,
            "created_at": self.created_at,
        }
