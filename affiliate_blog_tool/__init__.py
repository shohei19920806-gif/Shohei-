"""育児 × 釣り アフィリエイトブログ自動化ツール。

パイプライン:
  1. analyze   : Google Search Console + Google Trends からSEOデータを収集・分析
  2. themes    : 「伸びているが競合が薄い」テーマを選定
  3. generate  : Claude API で記事を自動生成（下書き）
  4. publish   : WordPressへ投稿（デフォルトは下書き保存。--publish で公開）
  5. social    : X / Instagram へ告知投稿
"""
