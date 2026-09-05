import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate_blog_tool.content.required_pages import (
    SiteProfile,
    contact_page_markdown,
    privacy_policy_markdown,
    profile_page_markdown,
)

PROFILE = SiteProfile(
    site_name="育児と釣りブログ", operator_name="しょうへい", contact_email="you@example.com"
)


def test_privacy_policy_includes_site_name_and_disclosures():
    text = privacy_policy_markdown(PROFILE)
    assert "育児と釣りブログ" in text
    assert "Googleアドセンス" in text
    assert "アフィリエイト" in text
    assert "Cookie" in text


def test_contact_page_includes_email():
    text = contact_page_markdown(PROFILE)
    assert "you@example.com" in text


def test_profile_page_includes_operator_name():
    text = profile_page_markdown(PROFILE)
    assert "しょうへい" in text
