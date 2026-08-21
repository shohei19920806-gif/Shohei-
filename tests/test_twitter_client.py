import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate_blog_tool.publish.social.twitter_client import build_tweet_text, MAX_LEN


def test_build_tweet_text_within_limit_short_input():
    text = build_tweet_text("短いタイトル", "短い要約", "https://example.com/abc")
    assert len(text) <= MAX_LEN
    assert text.endswith("https://example.com/abc")


def test_build_tweet_text_truncates_long_input():
    long_title = "あ" * 200
    text = build_tweet_text(long_title, "要約", "https://example.com/abc")
    assert len(text) <= MAX_LEN
    assert "https://example.com/abc" in text
