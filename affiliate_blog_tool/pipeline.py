"""パイプライン全体のオーケストレーション。

  analyze  : GSC + Trends からキーワード機会を収集し、レポートをdata/reports/に保存
  themes   : レポートから記事テーマを選定し、data/reports/themes.json に保存
  generate : テーマからClaude APIで記事を生成し、data/drafts/ に下書き保存
  publish  : 下書きをWordPressに投稿（デフォルトは下書き保存。--publish で公開）
  social   : 投稿済み記事をX/Instagramで告知

安全設計:
  各ステージはファイルベースで疎結合（前段の出力ファイルを次段が読む）。
  途中で止めて内容を人間がレビューしてから次に進められる。
  publish/social は明示的に --yes を付けない限り実行前に確認を挟む設計を推奨。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from affiliate_blog_tool.common import state
from affiliate_blog_tool.common.config import REPORTS_DIR, DRAFTS_DIR, Settings
from affiliate_blog_tool.common.models import ArticleTheme, GeneratedArticle, KeywordOpportunity, Vertical
from affiliate_blog_tool.content.article_generator import ArticleGenerator
from affiliate_blog_tool.content.theme_selector import select_themes
from affiliate_blog_tool.seo.gsc_client import GSCClient
from affiliate_blog_tool.seo.scorer import score_grow_opportunities, score_new_opportunities, merge_and_rank
from affiliate_blog_tool.seo.trends_client import TrendsClient

logger = logging.getLogger(__name__)

OPPORTUNITIES_FILE = REPORTS_DIR / "opportunities.json"
THEMES_FILE = REPORTS_DIR / "themes.json"

# Trendsで関連クエリを調べるための種キーワード（ブログの2大ジャンル）
DEFAULT_SEED_KEYWORDS = [
    "育児", "赤ちゃん 育児グッズ", "離乳食",
    "釣り", "堤防釣り", "ルアー釣り",
]


def run_analyze(settings: Settings, seed_keywords: list[str] | None = None, top_n: int = 30) -> list[KeywordOpportunity]:
    """GSC実績 + Google Trends から狙い目キーワードを抽出し、レポート保存する。"""
    seeds = seed_keywords or DEFAULT_SEED_KEYWORDS

    grow: list[KeywordOpportunity] = []
    if settings.gsc.is_configured:
        gsc_rows = GSCClient(settings.gsc).fetch_query_page_performance()
        grow = score_grow_opportunities(gsc_rows)
        existing_queries = {r.query for r in gsc_rows}
    else:
        logger.warning("GSC未設定のためスキップします（grow型の分析なし）")
        existing_queries = set()

    trends = TrendsClient()
    signals = trends.related_queries(seeds)
    new = score_new_opportunities(signals, existing_queries)

    ranked = merge_and_rank(grow, new, top_n=top_n)

    OPPORTUNITIES_FILE.write_text(
        json.dumps([o.to_dict() for o in ranked], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("分析結果を保存しました: %s (%d件)", OPPORTUNITIES_FILE, len(ranked))
    return ranked


def _load_opportunities() -> list[KeywordOpportunity]:
    raw = json.loads(OPPORTUNITIES_FILE.read_text(encoding="utf-8"))
    out = []
    for d in raw:
        d = dict(d)
        d["vertical"] = Vertical(d["vertical"])
        out.append(KeywordOpportunity(**d))
    return out


def run_select_themes(max_themes: int = 5, min_score: float = 0.0, skip_used: bool = True) -> list[ArticleTheme]:
    opportunities = _load_opportunities()
    if skip_used:
        unused_keywords = set(state.filter_unused([o.query for o in opportunities]))
        opportunities = [o for o in opportunities if o.query in unused_keywords]

    themes = select_themes(opportunities, max_themes=max_themes, min_score=min_score)
    THEMES_FILE.write_text(
        json.dumps([t.to_dict() for t in themes], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("テーマを選定しました: %s (%d件)", THEMES_FILE, len(themes))
    return themes


def _load_themes() -> list[ArticleTheme]:
    raw = json.loads(THEMES_FILE.read_text(encoding="utf-8"))
    out = []
    for d in raw:
        d = dict(d)
        d["vertical"] = Vertical(d["vertical"])
        out.append(ArticleTheme(**d))
    return out


def run_generate(settings: Settings) -> list[Path]:
    themes = _load_themes()
    generator = ArticleGenerator(settings.claude)
    articles = generator.generate_many(themes)

    saved_paths = []
    for article in articles:
        safe_name = "".join(c for c in article.theme.target_keyword if c.isalnum())[:40] or "article"
        path = DRAFTS_DIR / f"{safe_name}.json"
        path.write_text(json.dumps(article.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        saved_paths.append(path)
        logger.info("下書きを保存しました: %s", path)
    return saved_paths


def load_draft(path: Path) -> GeneratedArticle:
    data = json.loads(path.read_text(encoding="utf-8"))
    theme_data = dict(data["theme"])
    theme_data["vertical"] = Vertical(theme_data["vertical"])
    theme = ArticleTheme(**theme_data)
    return GeneratedArticle(
        theme=theme,
        meta_title=data["meta_title"],
        meta_description=data["meta_description"],
        body_markdown=data["body_markdown"],
        excerpt=data["excerpt"],
        tags=data.get("tags", []),
        created_at=data.get("created_at", ""),
    )


def list_drafts() -> list[Path]:
    return sorted(DRAFTS_DIR.glob("*.json"))
