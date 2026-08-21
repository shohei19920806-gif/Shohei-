"""GSC実績 + Google Trends を組み合わせて「狙い目キーワード」をスコアリングする。

考え方（無料データだけで「ヒットしていて競合が低いもの」を近似する）:

  A) 伸びしろ型（grow）
     既に自サイトが順位を持っている（= 検索上コンテンツとして成立しており、
     全くの無風ではない）クエリのうち、
       - 表示回数（impressions）が多い
       - 順位が 4〜20位（1〜3位ほど激戦ではないが、露出は取れている）
       - CTRが順位の割に低い（タイトル/導入文の改善や関連記事追加で伸びる余地）
     ものを「リライト・関連記事追加で伸ばせるテーマ」として抽出する。

  B) 新規開拓型（new）
     Google Trendsで急上昇（rising）しているが、まだ自サイトのGSCデータに
     ないキーワードを、「これから需要が伸びる＝先行者になれる＝
     相対的に競合コンテンツが薄い」候補として抽出する。
"""
from __future__ import annotations

from affiliate_blog_tool.common.models import KeywordOpportunity, classify_vertical
from affiliate_blog_tool.seo.gsc_client import GSCRow
from affiliate_blog_tool.seo.trends_client import TrendSignal

# 順位ごとの一般的な期待CTR（業界データの目安。厳密である必要はなく、
# 「このクエリはこの順位にしては伸びていない」を判定する基準として使う）
EXPECTED_CTR_BY_POSITION = {
    1: 0.28, 2: 0.15, 3: 0.10, 4: 0.07, 5: 0.06,
    6: 0.05, 7: 0.04, 8: 0.03, 9: 0.03, 10: 0.025,
}


def _expected_ctr(position: float) -> float:
    p = max(1, min(20, round(position)))
    if p <= 10:
        return EXPECTED_CTR_BY_POSITION[p]
    # 11-20位はなだらかに逓減
    return max(0.008, 0.02 - (p - 10) * 0.001)


def score_grow_opportunities(
    gsc_rows: list[GSCRow],
    min_impressions: int = 20,
    position_range: tuple[float, float] = (4.0, 20.0),
) -> list[KeywordOpportunity]:
    """既存の実績を伸ばせる「グロー型」テーマを抽出する。"""
    results: list[KeywordOpportunity] = []
    for row in gsc_rows:
        if row.impressions < min_impressions:
            continue
        if not (position_range[0] <= row.position <= position_range[1]):
            continue

        expected = _expected_ctr(row.position)
        ctr_gap = max(0.0, expected - row.ctr)
        # 表示回数が多いほど、CTRの伸びしろが大きいほど、
        # 1位に近いほど(=詰めやすいほど) スコアを高くする
        proximity_bonus = max(0.0, (20 - row.position) / 20)
        score = row.impressions * (0.4 + ctr_gap * 6) * (0.5 + proximity_bonus)

        results.append(
            KeywordOpportunity(
                query=row.query,
                vertical=classify_vertical(row.query + " " + row.page),
                impressions=row.impressions,
                clicks=row.clicks,
                ctr=row.ctr,
                position=row.position,
                source_page=row.page,
                opportunity_score=round(score, 2),
            )
        )
    results.sort(key=lambda o: o.opportunity_score, reverse=True)
    return results


def score_new_opportunities(
    trend_signals: list[TrendSignal],
    existing_queries: set[str],
) -> list[KeywordOpportunity]:
    """まだ自サイトに実績が無い、Trends急上昇ワードを「新規開拓型」として抽出する。"""
    existing_lower = {q.lower() for q in existing_queries}
    results: list[KeywordOpportunity] = []
    seen: set[str] = set()

    for sig in trend_signals:
        key = sig.keyword.lower()
        if key in existing_lower or key in seen:
            continue
        seen.add(key)

        # rising(急上昇)は新規開拓・低競合の代理指標として重み付けを厚くする
        weight = 3.0 if sig.is_rising else 1.0
        score = min(sig.interest, 5000) * weight / 50  # スケールをgrow型に近づける

        results.append(
            KeywordOpportunity(
                query=sig.keyword,
                vertical=classify_vertical(sig.keyword + " " + sig.seed),
                trend_score=sig.interest,
                trend_is_rising=sig.is_rising,
                opportunity_score=round(score, 2),
            )
        )
    results.sort(key=lambda o: o.opportunity_score, reverse=True)
    return results


def merge_and_rank(
    grow: list[KeywordOpportunity],
    new: list[KeywordOpportunity],
    top_n: int = 20,
) -> list[KeywordOpportunity]:
    combined = grow + new
    combined.sort(key=lambda o: o.opportunity_score, reverse=True)
    return combined[:top_n]
