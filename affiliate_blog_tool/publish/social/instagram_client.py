"""Instagram Graph API 投稿クライアント（画像フィード投稿）。

事前準備:
  1. Instagramビジネス/クリエイターアカウントをFacebookページに連携
  2. Meta for Developers でアプリを作成し、長期有効アクセストークンを取得
     （instagram_content_publish 権限が必要）
  3. .env に IG_ACCESS_TOKEN / IG_USER_ID を設定

制約:
  Instagram Graph APIは「インターネット上に公開済みの画像URL」しか
  受け付けない（ローカル画像の直接アップロード不可）。
  そのため image_url には、記事のアイキャッチ画像など既に公開済みのURLを渡す。
  投稿本文だけのテキスト投稿はInstagramの仕様上不可。
"""
from __future__ import annotations

import logging
import time

import requests

from affiliate_blog_tool.common.config import InstagramConfig

logger = logging.getLogger(__name__)

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def build_caption(title: str, excerpt: str, url: str) -> str:
    # Instagramの投稿はリンクをタップできないため、プロフィールリンク誘導文を添える
    return f"{title}\n\n{excerpt}\n\n詳しくはブログへ（プロフィール欄のリンクから）\n{url}"


class InstagramClient:
    def __init__(self, config: InstagramConfig):
        if not config.is_configured:
            raise RuntimeError(
                "Instagramが未設定です。IG_ACCESS_TOKEN / IG_USER_ID を .env に設定してください。"
            )
        self.config = config

    def post_image(self, image_url: str, title: str, excerpt: str, article_url: str) -> dict:
        caption = build_caption(title, excerpt, article_url)

        # 1. メディアコンテナ作成
        create_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.config.ig_user_id}/media",
            data={
                "image_url": image_url,
                "caption": caption,
                "access_token": self.config.access_token,
            },
            timeout=60,
        )
        create_resp.raise_for_status()
        container_id = create_resp.json()["id"]

        # 2. コンテナの処理完了を待つ（数秒かかることがある）
        for _ in range(10):
            status_resp = requests.get(
                f"{GRAPH_API_BASE}/{container_id}",
                params={"fields": "status_code", "access_token": self.config.access_token},
                timeout=30,
            )
            status_resp.raise_for_status()
            if status_resp.json().get("status_code") == "FINISHED":
                break
            time.sleep(2)

        # 3. 公開
        publish_resp = requests.post(
            f"{GRAPH_API_BASE}/{self.config.ig_user_id}/media_publish",
            data={"creation_id": container_id, "access_token": self.config.access_token},
            timeout=60,
        )
        publish_resp.raise_for_status()
        result = publish_resp.json()
        logger.info("Instagramに投稿しました: %s", result)
        return result
