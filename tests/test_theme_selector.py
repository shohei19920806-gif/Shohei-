import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate_blog_tool.common.models import KeywordOpportunity, Vertical
from affiliate_blog_tool.content.theme_selector import build_theme, infer_search_intent, select_themes


def test_infer_search_intent_comparison():
    assert "比較検討" in infer_search_intent("抱っこ紐 比較")


def test_infer_search_intent_howto():
    assert "ハウツー" in infer_search_intent("離乳食 やり方")


def test_infer_search_intent_default():
    assert "情報収集" in infer_search_intent("釣り 基本")


def test_build_theme_grow_type_notes_mentions_existing_page():
    opp = KeywordOpportunity(
        query="エギング コツ",
        vertical=Vertical.FISHING,
        impressions=300,
        position=7.5,
        ctr=0.01,
        source_page="/blog/egging",
    )
    theme = build_theme(opp)
    assert theme.target_keyword == "エギング コツ"
    assert theme.vertical == Vertical.FISHING
    assert "/blog/egging" in theme.notes


def test_build_theme_new_type_notes_mentions_trend():
    opp = KeywordOpportunity(
        query="新生児 抱っこ紐 冬",
        vertical=Vertical.PARENTING,
        trend_score=88,
        trend_is_rising=True,
    )
    theme = build_theme(opp)
    assert "トレンド" in theme.notes or "急上昇" in theme.notes


def test_select_themes_respects_max_and_min_score():
    opps = [
        KeywordOpportunity(query=f"q{i}", vertical=Vertical.PARENTING, opportunity_score=float(10 - i))
        for i in range(10)
    ]
    themes = select_themes(opps, max_themes=3, min_score=5.0)
    assert len(themes) == 3
    assert all(t.opportunity_score >= 5.0 for t in themes)
