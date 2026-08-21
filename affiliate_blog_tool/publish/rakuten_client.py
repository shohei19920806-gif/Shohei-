"""楽天ウェブサービス（商品検索API）を使った、楽天アフィリエイトリンクの自動取得。

事前準備（すべて無料）:
  1. 楽天アフィリエイトに登録: https://affiliate.rakuten.co.jp/
     登録完了後、管理画面で「アフィリエイトID」を確認できる
  2. 楽天ウェブサービスでアプリ登録し、アプリID(applicationId)を発行:
     https://webservice.rakuten.co.jp/
  3. .env に RAKUTEN_APP_ID / RAKUTEN_AFFILIATE_ID を設定

仕組み:
  商品検索APIのリクエストに affiliateId を渡すと、レスポンスの各商品に
  affiliateUrl（あなたのアフィリエイトIDが埋め込まれた商品リンク）が
  含まれて返ってくる。そのURLをそのまま記事に貼るだけで成果が計測される。

参考: 楽天市場商品検索API (IchibaItem/Search)
  https://webservice.rakuten.co.jp/documentation/ichiba-item-search
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from affiliate_blog_tool.common.config import RakutenConfig

logger = logging.getLogger(__name__)

SEARCH_ENDPOINT = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"


@dataclass
class RakutenItem:
    name: str
    price: int
    item_url: str
    affiliate_url: str
    image_url: str | None
    shop_name: str


class RakutenClient:
    def __init__(self, config: RakutenConfig):
        if not config.is_configured:
            raise RuntimeError(
                "楽天ウェブサービスが未設定です。RAKUTEN_APP_ID を .env に設定してください。"
            )
        if not config.affiliate_id:
            logger.warning(
                "RAKUTEN_AFFILIATE_ID が未設定です。取得できる商品リンクに成果（報酬）が"
                "付与されません。アフィリエイトIDの設定を推奨します。"
            )
        self.config = config

    def search_items(self, keyword: str, hits: int = 3) -> list[RakutenItem]:
        """キーワードで商品を検索し、アフィリエイトリンク付きで返す。

        sort="-reviewCount" でレビュー数の多い（＝売れている）商品を優先する。
        """
        params = {
            "applicationId": self.config.app_id,
            "keyword": keyword,
            "hits": hits,
            "sort": "-reviewCount",
            "format": "json",
        }
        if self.config.affiliate_id:
            params["affiliateId"] = self.config.affiliate_id

        resp = requests.get(SEARCH_ENDPOINT, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        items = [_parse_item(entry.get("Item", entry)) for entry in data.get("Items", [])]
        logger.info("楽天市場で「%s」の商品を%d件取得しました", keyword, len(items))
        return items


def _parse_item(item: dict) -> RakutenItem:
    image_url = None
    images = item.get("mediumImageUrls") or []
    if images:
        first = images[0]
        image_url = first.get("imageUrl") if isinstance(first, dict) else first

    return RakutenItem(
        name=item.get("itemName", ""),
        price=int(item.get("itemPrice", 0) or 0),
        item_url=item.get("itemUrl", ""),
        # affiliateUrl が無い場合（アフィリエイトID未設定時など）は通常URLにフォールバック
        affiliate_url=item.get("affiliateUrl") or item.get("itemUrl", ""),
        image_url=image_url,
        shop_name=item.get("shopName", ""),
    )
