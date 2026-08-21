import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate_blog_tool.common.models import Vertical, classify_vertical
from affiliate_blog_tool.seo.gsc_client import GSCRow
from affiliate_blog_tool.seo.scorer import score_grow_opportunities, score_new_opportunities, merge_and_rank
from affiliate_blog_tool.seo.trends_client import TrendSignal


def test_classify_vertical_parenting():
    assert classify_vertical("離乳食 開始時期") == Vertical.PARENTING


def test_classify_vertical_fishing():
    assert classify_vertical("堤防釣り 初心者 仕掛け") == Vertical.FISHING


def test_classify_vertical_unknown():
    assert classify_vertical("今日の天気") == Vertical.UNKNOWN


def test_score_grow_opportunities_filters_by_impressions_and_position():
    rows = [
        GSCRow(query="低表示回数", page="/a", clicks=0, impressions=5, ctr=0.0, position=8.0),
        GSCRow(query="範囲外順位", page="/b", clicks=1, impressions=100, ctr=0.01, position=45.0),
        GSCRow(query="狙い目クエリ", page="/c", clicks=1, impressions=200, ctr=0.005, position=8.0),
    ]
    results = score_grow_opportunities(rows, min_impressions=20, position_range=(4.0, 20.0))
    queries = [r.query for r in results]
    assert "狙い目クエリ" in queries
    assert "低表示回数" not in queries
    assert "範囲外順位" not in queries


def test_score_grow_opportunities_sorted_descending():
    rows = [
        GSCRow(query="A", page="/a", clicks=1, impressions=500, ctr=0.001, position=6.0),
        GSCRow(query="B", page="/b", clicks=1, impressions=30, ctr=0.02, position=6.0),
    ]
    results = score_grow_opportunities(rows)
    assert results[0].query == "A"
    assert results[0].opportunity_score >= results[1].opportunity_score


def test_score_new_opportunities_excludes_existing_queries():
    signals = [
        TrendSignal(keyword="既存クエリ", interest=80, is_rising=True, seed="育児"),
        TrendSignal(keyword="新規クエリ", interest=90, is_rising=True, seed="育児"),
    ]
    results = score_new_opportunities(signals, existing_queries={"既存クエリ"})
    queries = [r.query for r in results]
    assert "新規クエリ" in queries
    assert "既存クエリ" not in queries


def test_score_new_opportunities_rising_weighted_higher():
    signals = [
        TrendSignal(keyword="急上昇ワード", interest=50, is_rising=True, seed="釣り"),
        TrendSignal(keyword="安定ワード", interest=50, is_rising=False, seed="釣り"),
    ]
    results = score_new_opportunities(signals, existing_queries=set())
    scores = {r.query: r.opportunity_score for r in results}
    assert scores["急上昇ワード"] > scores["安定ワード"]


def test_merge_and_rank_respects_top_n():
    grow = [
        __import__("affiliate_blog_tool.common.models", fromlist=["KeywordOpportunity"]).KeywordOpportunity(
            query=f"g{i}", vertical=Vertical.PARENTING, opportunity_score=float(i)
        )
        for i in range(5)
    ]
    new = []
    ranked = merge_and_rank(grow, new, top_n=2)
    assert len(ranked) == 2
    assert ranked[0].opportunity_score >= ranked[1].opportunity_score
