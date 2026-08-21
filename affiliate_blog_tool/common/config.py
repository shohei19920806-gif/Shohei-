"""環境変数からの設定読み込み。

すべての認証情報は .env（gitignore対象）または実行環境の環境変数から読む。
コード中にAPIキーやパスワードを直書きしないこと。
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# .env があれば読み込む（python-dotenv がインストールされている場合のみ）
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover - dotenv は任意依存
    pass

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
REPORTS_DIR = DATA_DIR / "reports"
DRAFTS_DIR = DATA_DIR / "drafts"
STATE_DIR = DATA_DIR / "state"

for _d in (REPORTS_DIR, DRAFTS_DIR, STATE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def _env(name: str, default: str | None = None) -> str | None:
    return os.environ.get(name, default)


@dataclass
class GSCConfig:
    site_url: str | None = field(default_factory=lambda: _env("GSC_SITE_URL"))
    credentials_json: str | None = field(
        default_factory=lambda: _env("GSC_CREDENTIALS_JSON", "credentials/gsc_service_account.json")
    )

    @property
    def is_configured(self) -> bool:
        return bool(self.site_url and self.credentials_json and Path(self.credentials_json).exists())


@dataclass
class ClaudeConfig:
    api_key: str | None = field(default_factory=lambda: _env("ANTHROPIC_API_KEY"))
    # デフォルトはClaude Opus 5。コスト重視なら .env の ANTHROPIC_MODEL で
    # claude-sonnet-5 等に切り替え可能。
    model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-opus-5") or "claude-opus-5")

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass
class WordPressConfig:
    base_url: str | None = field(default_factory=lambda: _env("WP_BASE_URL"))  # 例: https://example.com
    username: str | None = field(default_factory=lambda: _env("WP_USERNAME"))
    app_password: str | None = field(default_factory=lambda: _env("WP_APP_PASSWORD"))

    @property
    def is_configured(self) -> bool:
        return bool(self.base_url and self.username and self.app_password)


@dataclass
class TwitterConfig:
    api_key: str | None = field(default_factory=lambda: _env("X_API_KEY"))
    api_secret: str | None = field(default_factory=lambda: _env("X_API_SECRET"))
    access_token: str | None = field(default_factory=lambda: _env("X_ACCESS_TOKEN"))
    access_secret: str | None = field(default_factory=lambda: _env("X_ACCESS_SECRET"))

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_secret and self.access_token and self.access_secret)


@dataclass
class InstagramConfig:
    access_token: str | None = field(default_factory=lambda: _env("IG_ACCESS_TOKEN"))
    ig_user_id: str | None = field(default_factory=lambda: _env("IG_USER_ID"))

    @property
    def is_configured(self) -> bool:
        return bool(self.access_token and self.ig_user_id)


@dataclass
class RakutenConfig:
    app_id: str | None = field(default_factory=lambda: _env("RAKUTEN_APP_ID"))
    # アフィリエイトIDは省略可能だが、未設定だと商品リンクに成果が付与されないため必須級
    affiliate_id: str | None = field(default_factory=lambda: _env("RAKUTEN_AFFILIATE_ID"))

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id)


@dataclass
class Settings:
    gsc: GSCConfig = field(default_factory=GSCConfig)
    claude: ClaudeConfig = field(default_factory=ClaudeConfig)
    wordpress: WordPressConfig = field(default_factory=WordPressConfig)
    twitter: TwitterConfig = field(default_factory=TwitterConfig)
    instagram: InstagramConfig = field(default_factory=InstagramConfig)
    rakuten: RakutenConfig = field(default_factory=RakutenConfig)


def load_settings() -> Settings:
    return Settings()
