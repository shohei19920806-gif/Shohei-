# 育児×釣り アフィリエイトブログ自動化ツール

育児・釣りの2ジャンルを扱うアフィリエイトブログ向けに、

1. **analyze** — Google Search Console（自サイトの実績）+ Google Trends（急上昇キーワード）でSEOデータを収集
2. **themes** — 「表示回数は多いが順位・CTRに伸びしろがある」「Trendsで急上昇中でまだ自サイトに実績がない」テーマを抽出
3. **generate** — Claude API で記事本文（タイトル・メタディスクリプション・本文・タグ）を自動生成（下書き）
4. **publish-wp** — WordPress REST API へ投稿（**デフォルトは下書き保存**。`--publish` を付けた時だけ公開）
5. **publish-sns** — X（Twitter）/ Instagram に告知投稿

をコマンドで一気通貫に行うツールです。

## 設計方針（安全のため）

- **記事の公開・SNS投稿は自動実行しません。** `generate` までは自動で下書きを作りますが、
  WordPressへの公開もSNS投稿も、内容を確認してから明示的にコマンドを実行する運用を想定しています。
  （`publish-wp` はデフォルトで下書き保存のみ。`--publish` を付けない限り公開されません）
- APIキー等の認証情報はすべて `.env`（Git管理対象外）から読み込みます。コード中に直書きしません。
- 一度使ったキーワードは `data/state/published_keywords.json` に記録し、重複投稿を防ぎます。

## セットアップ

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env を編集して各種認証情報を設定
```

### 1. Google Search Console（無料）

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクトを作成し、Search Console API を有効化
2. サービスアカウントを作成し、JSONキーをダウンロードして `credentials/gsc_service_account.json` に配置
3. Search Console の「設定 > ユーザーとアクセス権」で、サービスアカウントのメールアドレスを閲覧者として追加
4. `.env` の `GSC_SITE_URL`（例: `https://example.com/` または `sc-domain:example.com`）を設定

### 2. Claude API（Anthropic）

[console.anthropic.com](https://console.anthropic.com/) でAPIキーを発行し、`.env` の `ANTHROPIC_API_KEY` に設定。

### 3. WordPress

1. WordPress管理画面 > ユーザー > プロフィール で「アプリケーションパスワード」を発行
2. `.env` の `WP_BASE_URL` / `WP_USERNAME` / `WP_APP_PASSWORD` を設定

### 4. X (Twitter)

[X Developer Portal](https://developer.x.com/) でアプリを作成（投稿にはBasicプラン以上が事実上必要）し、
OAuth 1.0aの4つのキーを `.env` に設定。

### 5. Instagram

Instagramビジネス/クリエイターアカウントをFacebookページに連携し、
[Meta for Developers](https://developers.facebook.com/) で `instagram_content_publish` 権限を持つ
長期アクセストークンを発行。`.env` の `IG_ACCESS_TOKEN` / `IG_USER_ID` を設定。
※ Instagram Graph APIは「インターネット上に公開済みの画像URL」しか受け付けません。

## 使い方

```bash
# 1. SEO分析（GSC + Trends）→ data/reports/opportunities.json
python -m affiliate_blog_tool.cli analyze

# 2. 記事テーマ選定（上位5件）→ data/reports/themes.json
python -m affiliate_blog_tool.cli themes --max 5

# 3. Claude APIで記事を自動生成 → data/drafts/*.json
python -m affiliate_blog_tool.cli generate

# 生成された下書き一覧を確認
python -m affiliate_blog_tool.cli list-drafts

# 4. WordPressへ投稿（デフォルトは下書き保存。内容を管理画面で確認してから公開推奨）
python -m affiliate_blog_tool.cli publish-wp --draft data/drafts/xxx.json
# 確認後、実際に公開する場合
python -m affiliate_blog_tool.cli publish-wp --draft data/drafts/xxx.json --publish

# 5. SNSへ告知投稿
python -m affiliate_blog_tool.cli publish-sns \
  --draft data/drafts/xxx.json \
  --url https://example.com/xxx \
  --image https://example.com/wp-content/uploads/eyecatch.jpg \
  --x --instagram

# 1〜3をまとめて実行（公開・SNS投稿は含まない）
python -m affiliate_blog_tool.cli run-all --max-themes 3
```

## 「ヒットしていて競合が低いテーマ」の見つけ方（無料データのみで近似）

有料の競合調査ツール（Ahrefs等）を使わない前提のため、次の2種類のシグナルを組み合わせています。

- **伸びしろ型（grow）**: 自サイトのGSCで表示回数は多いが4〜20位あたりに留まっている
  ＝ある程度需要はあるが上位を取り切れていないクエリを、リライト・関連記事追加の対象として抽出
- **新規開拓型（new）**: Google Trendsで急上昇（rising）しているが、まだ自サイトのGSC実績にない
  キーワード ＝ 需要が伸び始めていて、先行して記事化すれば競合コンテンツが薄いうちに上位を狙える候補として抽出

より正確な競合難易度が必要な場合は、有料SEOツールのAPIキーを取得して
`affiliate_blog_tool/seo/` にクライアントを追加する形で拡張できます。

## ディレクトリ構成

```
affiliate_blog_tool/
  common/     設定・共通データモデル・状態管理
  seo/        GSC/Trendsクライアント、スコアリングロジック
  content/    テーマ選定、Claude APIによる記事生成
  publish/    WordPress投稿、SNS投稿（X/Instagram）
  cli.py      コマンドラインエントリーポイント
  pipeline.py 各ステージのオーケストレーション
data/
  reports/    分析結果・選定テーマ（JSON）
  drafts/     生成された記事下書き（JSON）
  state/      投稿済みキーワードの記録（重複防止）
tests/        pytestによるユニットテスト（スコアリング/テーマ選定/JSON解析等）
```

## テスト

```bash
pip install pytest
pytest tests/ -v
```

外部API（GSC/Trends/Claude/WordPress/X/Instagram）を呼ぶ部分は、
純粋なロジック（スコアリング・テーマ選定・文字数調整・JSON解析）だけを
モックなしでテストしています。

## 法的な注意事項

- アフィリエイトリンクを含む記事には、景品表示法に基づき広告であることの明示が必要です
  （WordPressテンプレート側で「本記事はアフィリエイト広告を含みます」等の表記を入れてください）。
- 生成記事は必ず公開前に人間が事実確認・薬機法/景品表示法観点でのチェックを行ってください
  （このツールはAIが誇大表現を避けるようプロンプト設計していますが、完全ではありません）。
- 各SNS/APIの利用規約・レートリミットを遵守してください。
