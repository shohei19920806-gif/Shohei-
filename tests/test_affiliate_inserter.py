import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate_blog_tool.content.affiliate_inserter import (
    find_affiliate_placeholders,
    insert_affiliate_links,
    render_product_block,
)
from affiliate_blog_tool.publish.rakuten_client import RakutenItem


def test_find_affiliate_placeholders_dedupes_and_preserves_order():
    body = (
        "本文\n<!-- AFFILIATE: ライフジャケット -->\n続き\n"
        "<!-- AFFILIATE: 抱っこ紐 -->\nさらに続き\n"
        "<!-- AFFILIATE: ライフジャケット -->\n"
    )
    result = find_affiliate_placeholders(body)
    assert result == ["ライフジャケット", "抱っこ紐"]


def test_find_affiliate_placeholders_none():
    assert find_affiliate_placeholders("プレースホルダーなしの本文") == []


def test_render_product_block_includes_name_price_link():
    items = [
        RakutenItem(
            name="子ども用ライフジャケット",
            price=3980,
            item_url="https://item.rakuten.co.jp/shop/abc/",
            affiliate_url="https://hb.afl.rakuten.co.jp/xxx",
            image_url="https://image.rakuten.co.jp/shop/abc.jpg",
            shop_name="アウトドアショップ",
        )
    ]
    block = render_product_block(items)
    assert "子ども用ライフジャケット" in block
    assert "3,980円" in block
    assert "https://hb.afl.rakuten.co.jp/xxx" in block
    assert "アウトドアショップ" in block


def test_render_product_block_empty_list():
    assert "見つかりません" in render_product_block([])


class _FakeRakutenClient:
    """ネットワークを叩かない、テスト用のダミークライアント。"""

    def __init__(self, items_by_keyword: dict[str, list[RakutenItem]]):
        self.items_by_keyword = items_by_keyword
        self.call_count = 0

    def search_items(self, keyword: str, hits: int = 3):
        self.call_count += 1
        return self.items_by_keyword.get(keyword, [])


def test_insert_affiliate_links_replaces_placeholder():
    body = "導入文\n<!-- AFFILIATE: ライフジャケット -->\nまとめ"
    item = RakutenItem(
        name="キッズライフジャケット",
        price=2980,
        item_url="https://item.rakuten.co.jp/shop/x/",
        affiliate_url="https://hb.afl.rakuten.co.jp/yyy",
        image_url=None,
        shop_name="ショップA",
    )
    client = _FakeRakutenClient({"ライフジャケット": [item]})

    result = insert_affiliate_links(body, client)

    assert "<!-- AFFILIATE:" not in result
    assert "キッズライフジャケット" in result
    assert "https://hb.afl.rakuten.co.jp/yyy" in result


def test_insert_affiliate_links_caches_repeated_categories():
    body = (
        "<!-- AFFILIATE: 抱っこ紐 -->\n本文\n<!-- AFFILIATE: 抱っこ紐 -->"
    )
    client = _FakeRakutenClient({"抱っこ紐": []})

    insert_affiliate_links(body, client)

    assert client.call_count == 1  # 同じカテゴリは1回だけAPIを呼ぶ


def test_insert_affiliate_links_keeps_placeholder_on_failure():
    class _FailingClient:
        def search_items(self, keyword, hits=3):
            raise RuntimeError("API error")

    body = "<!-- AFFILIATE: ルアー -->"
    result = insert_affiliate_links(body, _FailingClient())

    assert result == body  # 失敗時は元のまま
