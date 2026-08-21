"""コマンドラインエントリーポイント。

使い方例:
  python -m affiliate_blog_tool.cli analyze
  python -m affiliate_blog_tool.cli themes --max 5
  python -m affiliate_blog_tool.cli generate
  python -m affiliate_blog_tool.cli list-drafts
  python -m affiliate_blog_tool.cli publish-wp --draft data/drafts/xxx.json
  python -m affiliate_blog_tool.cli publish-wp --draft data/drafts/xxx.json --publish
  python -m affiliate_blog_tool.cli publish-sns --draft data/drafts/xxx.json \\
      --url https://example.com/xxx --image https://example.com/eyecatch.jpg --x --instagram
  python -m affiliate_blog_tool.cli run-all --max-themes 3
"""
from __future__ import annotations

import argparse
import logging
import sys

from affiliate_blog_tool import pipeline
from affiliate_blog_tool.common import state
from affiliate_blog_tool.common.config import load_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("affiliate_blog_tool.cli")


def cmd_analyze(args):
    settings = load_settings()
    pipeline.run_analyze(settings, top_n=args.top_n)


def cmd_themes(args):
    pipeline.run_select_themes(max_themes=args.max, min_score=args.min_score)


def cmd_generate(args):
    settings = load_settings()
    paths = pipeline.run_generate(settings)
    print(f"{len(paths)}件の下書きを生成しました:")
    for p in paths:
        print(f"  - {p}")


def cmd_list_drafts(args):
    for p in pipeline.list_drafts():
        article = pipeline.load_draft(p)
        print(f"{p.name}\t{article.theme.vertical.value}\t{article.meta_title}")


def cmd_publish_wp(args):
    from affiliate_blog_tool.publish.wordpress_client import WordPressClient
    from pathlib import Path

    settings = load_settings()
    client = WordPressClient(settings.wordpress)

    draft_path = Path(args.draft)
    article = pipeline.load_draft(draft_path)

    if not args.publish:
        print("--publish を指定していないため『下書き保存』のみ行います（記事は公開されません）。")

    post = client.create_post(article, publish=args.publish)
    state.mark_used(article.theme.target_keyword, wp_post_id=post.get("id"), wp_url=post.get("link"))
    print(f"投稿完了: id={post.get('id')} status={post.get('status')} url={post.get('link')}")


def cmd_publish_sns(args):
    from pathlib import Path

    settings = load_settings()
    article = pipeline.load_draft(Path(args.draft))

    if args.x:
        from affiliate_blog_tool.publish.social.twitter_client import TwitterClient

        TwitterClient(settings.twitter).post(article.meta_title, article.excerpt, args.url)

    if args.instagram:
        from affiliate_blog_tool.publish.social.instagram_client import InstagramClient

        if not args.image:
            print("エラー: Instagram投稿には --image (公開済み画像URL) が必要です。", file=sys.stderr)
            sys.exit(1)
        InstagramClient(settings.instagram).post_image(
            args.image, article.meta_title, article.excerpt, args.url
        )


def cmd_run_all(args):
    settings = load_settings()
    pipeline.run_analyze(settings, top_n=args.top_n)
    pipeline.run_select_themes(max_themes=args.max_themes)
    paths = pipeline.run_generate(settings)
    print(f"{len(paths)}件の下書きを生成しました。内容を確認のうえ:")
    print("  publish-wp / publish-sns コマンドで投稿してください（自動公開はしません）。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="affiliate_blog_tool")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("analyze", help="GSC+Trendsからキーワード機会を分析")
    p.add_argument("--top-n", type=int, default=30)
    p.set_defaults(func=cmd_analyze)

    p = sub.add_parser("themes", help="記事テーマを選定")
    p.add_argument("--max", type=int, default=5)
    p.add_argument("--min-score", type=float, default=0.0)
    p.set_defaults(func=cmd_themes)

    p = sub.add_parser("generate", help="Claude APIで記事を生成")
    p.set_defaults(func=cmd_generate)

    p = sub.add_parser("list-drafts", help="生成済み下書きの一覧")
    p.set_defaults(func=cmd_list_drafts)

    p = sub.add_parser("publish-wp", help="WordPressへ投稿（デフォルトは下書き保存）")
    p.add_argument("--draft", required=True)
    p.add_argument("--publish", action="store_true", help="指定時のみ実際に公開する")
    p.set_defaults(func=cmd_publish_wp)

    p = sub.add_parser("publish-sns", help="X/Instagramへ告知投稿")
    p.add_argument("--draft", required=True)
    p.add_argument("--url", required=True, help="公開された記事のURL")
    p.add_argument("--image", help="Instagram投稿用の公開済み画像URL")
    p.add_argument("--x", action="store_true")
    p.add_argument("--instagram", action="store_true")
    p.set_defaults(func=cmd_publish_sns)

    p = sub.add_parser("run-all", help="analyze→themes→generateを一括実行（公開は手動確認）")
    p.add_argument("--top-n", type=int, default=30)
    p.add_argument("--max-themes", type=int, default=3)
    p.set_defaults(func=cmd_run_all)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
