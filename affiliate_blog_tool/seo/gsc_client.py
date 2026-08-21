"""Google Search Console (Search Analytics API) クライアント。

事前準備:
  1. Google Cloud Console でプロジェクトを作成し、Search Console API を有効化
  2. サービスアカウントを作成し、JSONキーをダウンロード
  3. Search Console の「設定 > ユーザーとアクセス権」で
     サービスアカウントのメールアドレスを「閲覧者」として追加
  4. .env に GSC_SITE_URL / GSC_CREDENTIALS_JSON を設定
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from affiliate_blog_tool.common.config import GSCConfig

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]


@dataclass
class GSCRow:
    query: str
    page: str
    clicks: int
    impressions: int
    ctr: float
    position: float


class GSCClient:
    def __init__(self, config: GSCConfig):
        if not config.is_configured:
            raise RuntimeError(
                "Google Search Console が未設定です。GSC_SITE_URL と "
                "GSC_CREDENTIALS_JSON を .env に設定してください。"
            )
        self.config = config
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service
        # 遅延importにして、GSCを使わない場合はgoogle-api依存が無くても動くようにする
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(
            self.config.credentials_json, scopes=SCOPES
        )
        self._service = build("searchconsole", "v1", credentials=creds)
        return self._service

    def fetch_query_page_performance(
        self, days: int = 90, row_limit: int = 5000
    ) -> list[GSCRow]:
        """直近days日間の「検索クエリ×ページ」実績を取得する。"""
        from datetime import date, timedelta

        service = self._get_service()
        end = date.today() - timedelta(days=2)  # GSCは直近2日分は未確定のことが多い
        start = end - timedelta(days=days)

        rows: list[GSCRow] = []
        start_row = 0
        while True:
            body = {
                "startDate": start.isoformat(),
                "endDate": end.isoformat(),
                "dimensions": ["query", "page"],
                "rowLimit": min(25000, row_limit - len(rows)) if row_limit else 25000,
                "startRow": start_row,
            }
            resp = (
                service.searchanalytics()
                .query(siteUrl=self.config.site_url, body=body)
                .execute()
            )
            batch = resp.get("rows", [])
            for r in batch:
                query, page = r["keys"]
                rows.append(
                    GSCRow(
                        query=query,
                        page=page,
                        clicks=int(r.get("clicks", 0)),
                        impressions=int(r.get("impressions", 0)),
                        ctr=float(r.get("ctr", 0.0)),
                        position=float(r.get("position", 0.0)),
                    )
                )
            if len(batch) < 25000 or (row_limit and len(rows) >= row_limit):
                break
            start_row += len(batch)

        logger.info("GSCから%d件のクエリ×ページ実績を取得しました", len(rows))
        return rows
