import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from affiliate_blog_tool.content.article_generator import _parse_json_response


def test_parse_json_response_plain():
    text = '{"meta_title": "タイトル", "tags": ["a", "b"]}'
    data = _parse_json_response(text)
    assert data["meta_title"] == "タイトル"
    assert data["tags"] == ["a", "b"]


def test_parse_json_response_with_code_fence():
    text = '```json\n{"meta_title": "タイトル"}\n```'
    data = _parse_json_response(text)
    assert data["meta_title"] == "タイトル"


def test_parse_json_response_with_surrounding_prose():
    text = 'はい、以下がJSONです。\n{"meta_title": "タイトル"}\nご確認ください。'
    data = _parse_json_response(text)
    assert data["meta_title"] == "タイトル"
