import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate_blog_tool.content.quality_checks import find_experience_placeholders


def test_find_experience_placeholders_returns_hint():
    body = "導入文\n<!-- EXPERIENCE: 実際に0歳児と堤防釣りに行った時の様子 -->\n本文"
    result = find_experience_placeholders(body)
    assert result == ["実際に0歳児と堤防釣りに行った時の様子"]


def test_find_experience_placeholders_none():
    assert find_experience_placeholders("体験談の目印なし本文") == []


def test_find_experience_placeholders_multiple():
    body = (
        "<!-- EXPERIENCE: ヒント1 -->\n本文\n<!-- EXPERIENCE: ヒント2 -->"
    )
    assert find_experience_placeholders(body) == ["ヒント1", "ヒント2"]
