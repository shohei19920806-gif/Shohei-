import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate_blog_tool.content.adsense_checklist import (
    RECOMMENDED_MIN_POSTS,
    all_ready,
    evaluate_readiness,
)


def test_evaluate_readiness_all_ok():
    items = evaluate_readiness(
        published_post_count=RECOMMENDED_MIN_POSTS,
        existing_page_titles=["プライバシーポリシー", "お問い合わせ", "運営者プロフィール"],
    )
    assert all_ready(items)


def test_evaluate_readiness_not_enough_posts():
    items = evaluate_readiness(
        published_post_count=1,
        existing_page_titles=["プライバシーポリシー", "お問い合わせ", "プロフィール"],
    )
    post_item = next(i for i in items if i.name == "公開記事数")
    assert not post_item.ok
    assert not all_ready(items)


def test_evaluate_readiness_missing_pages():
    items = evaluate_readiness(published_post_count=RECOMMENDED_MIN_POSTS, existing_page_titles=[])
    assert not all_ready(items)
    missing_names = [i.name for i in items if not i.ok]
    assert "固定ページ: プライバシーポリシー" in missing_names
    assert "固定ページ: お問い合わせ" in missing_names
    assert "固定ページ: プロフィール" in missing_names


def test_evaluate_readiness_page_detection_is_case_insensitive():
    items = evaluate_readiness(
        published_post_count=RECOMMENDED_MIN_POSTS,
        existing_page_titles=["Privacy Policy", "Contact", "About Me"],
    )
    assert all_ready(items)
