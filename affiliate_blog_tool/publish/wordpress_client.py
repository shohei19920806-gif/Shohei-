"""WordPress REST API クライアント（アプリケーションパスワード認証）。

事前準備:
  1. WordPress管理画面 > ユーザー > プロフィール で「アプリケーションパスワード」を発行
  2. .env に WP_BASE_URL / WP_USERNAME / WP_APP_PASSWORD を設定
     WP_BASE_URL は https://example.com のようにパスなし

安全設計:
  デフォルトは status="draft"（下書き保存のみ）。
  実際に公開するのは publish=True を明示した時だけ。
"""
from __future__ import annotations

import logging

import requests

from affiliate_blog_tool.common.config import WordPressConfig
from affiliate_blog_tool.common.models import GeneratedArticle, Vertical

logger = logging.getLogger(__name__)

CATEGORY_MAP = {
    Vertical.PARENTING: "育児",
    Vertical.FISHING: "釣り",
    Vertical.UNKNOWN: "お知らせ",
}


def _markdown_to_html(markdown_text: str) -> str:
    """簡易Markdown→HTML変換。凝った変換が必要な場合は `markdown` パッケージに差し替え可。"""
    try:
        import markdown as md

        return md.markdown(markdown_text, extensions=["extra"])
    except ImportError:
        # markdown未インストール時のフォールバック（最低限の見出し/改行変換）
        lines = markdown_text.splitlines()
        html_lines = []
        for line in lines:
            if line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.strip() == "":
                html_lines.append("")
            else:
                html_lines.append(f"<p>{line}</p>")
        return "\n".join(html_lines)


class WordPressClient:
    def __init__(self, config: WordPressConfig):
        if not config.is_configured:
            raise RuntimeError(
                "WordPressが未設定です。WP_BASE_URL / WP_USERNAME / WP_APP_PASSWORD を "
                ".env に設定してください。"
            )
        self.config = config
        self.session = requests.Session()
        self.session.auth = (config.username, config.app_password)

    @property
    def _api_base(self) -> str:
        return self.config.base_url.rstrip("/") + "/wp-json/wp/v2"

    def _get_or_create_category(self, name: str) -> int | None:
        try:
            resp = self.session.get(f"{self._api_base}/categories", params={"search": name}, timeout=30)
            resp.raise_for_status()
            for cat in resp.json():
                if cat["name"] == name:
                    return cat["id"]
            create = self.session.post(f"{self._api_base}/categories", json={"name": name}, timeout=30)
            create.raise_for_status()
            return create.json()["id"]
        except requests.RequestException:
            logger.warning("カテゴリ「%s」の取得/作成に失敗しました。カテゴリなしで投稿します。", name)
            return None

    def create_post(self, article: GeneratedArticle, publish: bool = False) -> dict:
        """記事をWordPressに投稿する。デフォルトは下書き(draft)。"""
        category_name = CATEGORY_MAP.get(article.theme.vertical, "お知らせ")
        category_id = self._get_or_create_category(category_name)

        payload = {
            "title": article.meta_title or article.theme.title,
            "content": _markdown_to_html(article.body_markdown),
            "excerpt": article.excerpt,
            "status": "publish" if publish else "draft",
        }
        if category_id:
            payload["categories"] = [category_id]

        resp = self.session.post(f"{self._api_base}/posts", json=payload, timeout=60)
        resp.raise_for_status()
        post = resp.json()

        # メタディスクリプションは多くのSEOプラグイン（Yoast等）が固有フィールドを
        # 要求するため、標準REST APIだけでは設定できないことがある。
        # meta フィールド経由で書き込みを試みる（プラグイン側の対応が必要）。
        logger.info(
            "WordPressに投稿しました: id=%s status=%s url=%s",
            post.get("id"), post.get("status"), post.get("link"),
        )
        return post

    def create_page(self, title: str, body_markdown: str, publish: bool = False, slug: str | None = None) -> dict:
        """固定ページ（プライバシーポリシー等）を作成する。デフォルトは下書き。"""
        payload = {
            "title": title,
            "content": _markdown_to_html(body_markdown),
            "status": "publish" if publish else "draft",
        }
        if slug:
            payload["slug"] = slug

        resp = self.session.post(f"{self._api_base}/pages", json=payload, timeout=60)
        resp.raise_for_status()
        page = resp.json()
        logger.info(
            "固定ページを作成しました: id=%s status=%s url=%s",
            page.get("id"), page.get("status"), page.get("link"),
        )
        return page

    def list_pages(self, per_page: int = 50) -> list[dict]:
        resp = self.session.get(f"{self._api_base}/pages", params={"per_page": per_page}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def count_posts(self, status: str = "publish") -> int:
        """指定ステータスの投稿数を返す（アドセンス審査の記事数チェック用）。"""
        resp = self.session.get(
            f"{self._api_base}/posts",
            params={"status": status, "per_page": 1},
            timeout=30,
        )
        resp.raise_for_status()
        total = resp.headers.get("X-WP-Total")
        return int(total) if total is not None else len(resp.json())
