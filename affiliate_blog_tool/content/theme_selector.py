"""スコアリング済みキーワードから、記事テーマ案を作る。"""
from __future__ import annotations

from affiliate_blog_tool.common.models import ArticleTheme, KeywordOpportunity, Vertical

# 検索意図の簡易判定（記事の切り口をAI生成プロンプトに渡すため）
INTENT_HINTS = [
    ("比較", "比較検討（複数商品/方法の比較記事が刺さる）"),
    ("おすすめ", "商品選定（ランキング・レビュー記事が刺さる）"),
    ("方法", "ハウツー（手順解説記事が刺さる）"),
    ("やり方", "ハウツー（手順解説記事が刺さる）"),
    ("原因", "悩み解決（原因と対策の解説記事が刺さる）"),
    ("時期", "時期・タイミング解説記事が刺さる"),
    ("選び方", "商品選定（選び方ガイドが刺さる）"),
]


def infer_search_intent(query: str) -> str:
    for kw, hint in INTENT_HINTS:
        if kw in query:
            return hint
    return "情報収集（基礎解説＋関連商品の紹介記事が刺さる）"


def build_theme(opportunity: KeywordOpportunity, related: list[str] | None = None) -> ArticleTheme:
    vertical = opportunity.vertical if opportunity.vertical != Vertical.UNKNOWN else Vertical.PARENTING
    intent = infer_search_intent(opportunity.query)

    if opportunity.source_page:
        note = (
            f"既存ページ({opportunity.source_page})が表示回数{opportunity.impressions}件・"
            f"平均順位{opportunity.position:.1f}位・CTR{opportunity.ctr:.1%}。"
            "リライトまたは関連の深掘り記事で上位化を狙う。"
        )
    else:
        note = (
            f"Googleトレンドで急上昇中（interest={opportunity.trend_score:.0f}）。"
            "先行して記事化し、競合が増える前に上位を確保する。"
        )

    title = f"{opportunity.query}｜{intent.split('（')[0]}まとめ"

    return ArticleTheme(
        title=title,
        target_keyword=opportunity.query,
        vertical=vertical,
        search_intent=intent,
        related_keywords=related or [],
        opportunity_score=opportunity.opportunity_score,
        notes=note,
    )


def select_themes(
    opportunities: list[KeywordOpportunity],
    max_themes: int = 5,
    min_score: float = 0.0,
) -> list[ArticleTheme]:
    """スコア順に、閾値以上のものを最大max_themes件テーマ化する。"""
    picked = [o for o in opportunities if o.opportunity_score >= min_score][:max_themes]
    return [build_theme(o) for o in picked]
