"""Google Trends クライアント（pytrends を利用、無料）。

「競合が薄いが伸びている」キーワードの代理指標として、
関連クエリの中でも "rising"（急上昇）に分類されるものを重視する。
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TrendSignal:
    keyword: str
    interest: float  # 0-100 の相対指標（top/rising双方あり得る）
    is_rising: bool
    seed: str


class TrendsClient:
    """pytrends のラッパー。未インストールでも import 時点では落ちないようにする。"""

    def __init__(self, geo: str = "JP", sleep_sec: float = 1.5):
        self.geo = geo
        self.sleep_sec = sleep_sec
        self._pytrends = None

    def _get_client(self):
        if self._pytrends is None:
            from pytrends.request import TrendReq

            self._pytrends = TrendReq(hl="ja-JP", tz=540)
        return self._pytrends

    def related_queries(self, seed_keywords: list[str]) -> list[TrendSignal]:
        """種キーワードごとに関連クエリ（top / rising）を取得する。"""
        pytrends = self._get_client()
        signals: list[TrendSignal] = []

        for seed in seed_keywords:
            try:
                pytrends.build_payload([seed], timeframe="today 3-m", geo=self.geo)
                related = pytrends.related_queries()
                data = related.get(seed, {})

                rising_df = data.get("rising")
                if rising_df is not None:
                    for _, row in rising_df.iterrows():
                        signals.append(
                            TrendSignal(
                                keyword=str(row["query"]),
                                interest=_parse_value(row.get("value", 0)),
                                is_rising=True,
                                seed=seed,
                            )
                        )

                top_df = data.get("top")
                if top_df is not None:
                    for _, row in top_df.iterrows():
                        signals.append(
                            TrendSignal(
                                keyword=str(row["query"]),
                                interest=float(row.get("value", 0) or 0),
                                is_rising=False,
                                seed=seed,
                            )
                        )
            except Exception as exc:  # pragma: no cover - 外部APIのため
                logger.warning("Google Trends取得に失敗しました (seed=%s): %s", seed, exc)
            time.sleep(self.sleep_sec)  # レート制限回避

        logger.info("Google Trendsから%d件のシグナルを取得しました", len(signals))
        return signals


def _parse_value(value) -> float:
    """rising の value は 'Breakout' 等の文字列のことがあるため数値化する。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        # "Breakout" = 急上昇の最大値として扱う
        return 5000.0
