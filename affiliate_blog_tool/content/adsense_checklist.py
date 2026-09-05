"""Googleアドセンス申請前の準備状況をチェックする。

審査基準はGoogle側で随時変わるため、ここでの判定はあくまで目安。
最終的な可否はGoogleの審査結果に従うこと。
"""
from __future__ import annotations

from dataclasses import dataclass

# 目安の最低記事数（5〜10記事以上が推奨とされることが多いため、中間を採用）
RECOMMENDED_MIN_POSTS = 8

REQUIRED_PAGES = {
    "プライバシーポリシー": ["プライバシーポリシー", "privacy"],
    "お問い合わせ": ["お問い合わせ", "contact"],
    "プロフィール": ["プロフィール", "運営者", "about"],
}


@dataclass
class CheckItem:
    name: str
    ok: bool
    detail: str


def evaluate_readiness(published_post_count: int, existing_page_titles: list[str]) -> list[CheckItem]:
    """公開済み記事数と固定ページのタイトル一覧から、審査準備状況を判定する。"""
    titles_lower = [t.lower() for t in existing_page_titles]
    items: list[CheckItem] = []

    items.append(
        CheckItem(
            name="公開記事数",
            ok=published_post_count >= RECOMMENDED_MIN_POSTS,
            detail=f"{published_post_count}記事 / 推奨{RECOMMENDED_MIN_POSTS}記事以上",
        )
    )

    for page_name, keywords in REQUIRED_PAGES.items():
        found = any(any(kw.lower() in title for kw in keywords) for title in titles_lower)
        items.append(
            CheckItem(
                name=f"固定ページ: {page_name}",
                ok=found,
                detail="設置済み" if found else "未設置（setup-pages コマンドで作成できます）",
            )
        )

    return items


def all_ready(items: list[CheckItem]) -> bool:
    return all(item.ok for item in items)
