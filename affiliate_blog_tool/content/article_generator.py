"""Claude API を使って、記事テーマから下書き記事を自動生成する。"""
from __future__ import annotations

import json
import logging

from affiliate_blog_tool.common.config import ClaudeConfig
from affiliate_blog_tool.common.models import ArticleTheme, GeneratedArticle

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたは「育児」と「釣り」の2ジャンルを扱う日本語アフィリエイトブログの
専属ライターです。SEOに強く、読者の検索意図に的確に応える記事を書きます。

執筆ルール:
- 一次情報のように断定できない事実（医学的な断定、安全性に関わる内容など）は
  一般論として書き、「かかりつけ医に相談」「メーカーの安全基準を確認」等の
  注意喚起を添える。
- 誇大な効果効能を謳わない。薬機法・景品表示法に抵触しうる表現
  （「必ず治る」「絶対に釣れる」等）は使わない。
- アフィリエイト商品を紹介する箇所には Markdown コメント
  `<!-- AFFILIATE: 商品カテゴリ名 -->` を本文中に挿入する
  （実際の商品名・リンクは後工程で人間が差し込むため、ここでは挿入しない）。
- E-E-A-T（経験・専門性・権威性・信頼性）対策として、導入文の直後に
  Markdownコメント `<!-- EXPERIENCE: 何についての体験談を書くべきかの一言ヒント -->`
  を必ず1箇所挿入する（例: `<!-- EXPERIENCE: 実際に0歳児と堤防釣りに行った時の様子 -->`）。
  これは筆者本人が自分の実体験・写真を追記するための目印であり、
  AIが体験談の内容そのものを創作してはならない。
- 見出し(H2/H3)を使い、各見出しの中でも結論から書く（PREP法：結論→理由→具体例→再結論）。
  遠回しな前置きをせず、まず答えを述べてから理由・具体例を続ける。

文章の質に関するルール（読みやすさ対策）:
- 同じ接続詞（「しかし」「そして」等）や同じ文末（「です」「ます」等）を
  3回以上連続させない。
- 「〜ということ」「〜こと」「これ・それ・あの」等の指示語・冗長表現は
  意味が通る範囲で削る。
- 「の」「と」「や」を1文中で連続使用しない。
- 主語と述語、修飾語と被修飾語の距離はできるだけ近づける。
- 漢字とひらがなのバランスは漢字3〜4割・ひらがな6〜7割程度を目安にし、
  漢字ばかりで堅苦しくならないようにする。
- 抽象的な説明より、具体的な数字（月齢、時間、金額、個数など）を優先して使う。
- 出力は必ず指定のJSON形式のみ。前後に説明文を付けない。
"""

OUTPUT_SCHEMA_HINT = """\
以下のJSON形式で出力してください（キーを変えない・追加しない）:
{
  "meta_title": "32文字前後のSEOタイトル（対策キーワードを含む）",
  "meta_description": "110-120文字程度のメタディスクリプション",
  "body_markdown": "本文全体（Markdown、H2/H3見出し、2000-3000文字目安）",
  "excerpt": "記事の要約（SNS告知にも使える80文字程度）",
  "tags": ["タグ1", "タグ2", "タグ3"]
}
"""


def _build_user_prompt(theme: ArticleTheme) -> str:
    related = "、".join(theme.related_keywords) if theme.related_keywords else "なし"
    return f"""\
次のテーマで記事を1本執筆してください。

- ジャンル: {theme.vertical.value}
- 対策キーワード: {theme.target_keyword}
- 記事タイトル案: {theme.title}
- 想定検索意図: {theme.search_intent}
- 関連キーワード: {related}
- 補足メモ: {theme.notes}

{OUTPUT_SCHEMA_HINT}
"""


class ArticleGenerator:
    def __init__(self, config: ClaudeConfig):
        if not config.is_configured:
            raise RuntimeError(
                "Claude APIが未設定です。ANTHROPIC_API_KEY を .env に設定してください。"
            )
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.config.api_key)
        return self._client

    def generate(self, theme: ArticleTheme) -> GeneratedArticle:
        client = self._get_client()

        response = client.messages.create(
            model=self.config.model,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            output_config={"effort": "high"},
            messages=[{"role": "user", "content": _build_user_prompt(theme)}],
        )

        text = next((b.text for b in response.content if b.type == "text"), "")
        data = _parse_json_response(text)

        return GeneratedArticle(
            theme=theme,
            meta_title=data.get("meta_title", theme.title)[:60],
            meta_description=data.get("meta_description", ""),
            body_markdown=data.get("body_markdown", ""),
            excerpt=data.get("excerpt", ""),
            tags=data.get("tags", []),
        )

    def generate_many(self, themes: list[ArticleTheme]) -> list[GeneratedArticle]:
        articles = []
        for theme in themes:
            try:
                articles.append(self.generate(theme))
            except Exception:
                logger.exception("記事生成に失敗しました: %s", theme.target_keyword)
        return articles


def _parse_json_response(text: str) -> dict:
    """モデル出力からJSON部分を頑健に取り出す（```json フェンス対策込み）。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start != -1 and end != -1:
            return json.loads(cleaned[start : end + 1])
        raise
