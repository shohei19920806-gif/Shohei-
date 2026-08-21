"""記事本文中の <!-- AFFILIATE: カテゴリ名 --> を、楽天の実商品リンクに差し替える。"""
from __future__ import annotations

import logging
import re

from affiliate_blog_tool.publish.rakuten_client import RakutenClient, RakutenItem

logger = logging.getLogger(__name__)

AFFILIATE_PLACEHOLDER_RE = re.compile(r"<!--\s*AFFILIATE:\s*(.+?)\s*-->")


def find_affiliate_placeholders(body_markdown: str) -> list[str]:
    """本文中のAFFILIATEプレースホルダーのカテゴリ名一覧を、重複を除いて出現順で返す。"""
    seen: list[str] = []
    for m in AFFILIATE_PLACEHOLDER_RE.finditer(body_markdown):
        name = m.group(1)
        if name not in seen:
            seen.append(name)
    return seen


def render_product_block(items: list[RakutenItem]) -> str:
    """楽天の商品リストをMarkdownの商品紹介ブロックに変換する。"""
    if not items:
        return "<!-- 該当する商品が見つかりませんでした -->"

    lines = ["<!-- 楽天アフィリエイト商品 -->"]
    for item in items:
        price_str = f"{item.price:,}円" if item.price else "価格はリンク先を確認"
        if item.image_url:
            lines.append(f"![{item.name}]({item.image_url})")
        lines.append(f"**[{item.name}]({item.affiliate_url})**（{item.shop_name} / {price_str}）")
        lines.append("")
    return "\n".join(lines).rstrip()


def insert_affiliate_links(
    body_markdown: str, client: RakutenClient, hits_per_category: int = 3
) -> str:
    """本文中の全AFFILIATEプレースホルダーを、楽天の実商品リンクに差し替える。

    同じカテゴリ名が複数回出てくる場合はAPI呼び出しを1回にまとめる（キャッシュ）。
    検索に失敗したカテゴリは元のプレースホルダーを残し、処理を止めない。
    """
    cache: dict[str, str] = {}

    def _replace(match: re.Match) -> str:
        category = match.group(1)
        if category not in cache:
            try:
                items = client.search_items(category, hits=hits_per_category)
                cache[category] = render_product_block(items)
            except Exception:
                logger.exception(
                    "「%s」の楽天商品検索に失敗しました。プレースホルダーを残します。", category
                )
                cache[category] = match.group(0)
        return cache[category]

    return AFFILIATE_PLACEHOLDER_RE.sub(_replace, body_markdown)
