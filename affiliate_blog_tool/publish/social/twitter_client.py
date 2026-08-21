"""X (Twitter) API v2 投稿クライアント。

事前準備:
  1. X Developer Portal でアプリを作成（投稿にはBasicプラン以上が事実上必要）
  2. OAuth 1.0a のAPIキー/シークレット、アクセストークン/シークレットを取得
  3. .env に X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_SECRET を設定
"""
from __future__ import annotations

import logging

from affiliate_blog_tool.common.config import TwitterConfig

logger = logging.getLogger(__name__)

MAX_LEN = 140  # 日本語は140文字制限


def build_tweet_text(title: str, excerpt: str, url: str) -> str:
    """タイトル+要約+URLを140文字以内に収める。"""
    reserved = len(url) + 1  # URL + 改行
    budget = MAX_LEN - reserved
    body = f"{title}\n{excerpt}" if excerpt else title
    if len(body) > budget:
        body = body[: max(0, budget - 1)] + "…"
    return f"{body}\n{url}"


class TwitterClient:
    def __init__(self, config: TwitterConfig):
        if not config.is_configured:
            raise RuntimeError(
                "Xが未設定です。X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / "
                "X_ACCESS_SECRET を .env に設定してください。"
            )
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            import tweepy

            self._client = tweepy.Client(
                consumer_key=self.config.api_key,
                consumer_secret=self.config.api_secret,
                access_token=self.config.access_token,
                access_token_secret=self.config.access_secret,
            )
        return self._client

    def post(self, title: str, excerpt: str, url: str) -> dict:
        client = self._get_client()
        text = build_tweet_text(title, excerpt, url)
        resp = client.create_tweet(text=text)
        logger.info("Xに投稿しました: %s", resp.data)
        return resp.data
