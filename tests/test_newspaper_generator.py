"""newspaper_generator のユニットテスト"""

from datetime import datetime

import pytest

from src.newspaper_generator import generate_newspaper, _get_stars, _get_heat


class TestGetStars:
    def test_スコア80以上は星5(self):
        assert _get_stars(80) == "★★★★★"
        assert _get_stars(100) == "★★★★★"

    def test_スコア60以上80未満は星4(self):
        assert _get_stars(60) == "★★★★☆"
        assert _get_stars(79) == "★★★★☆"

    def test_スコア0は星1(self):
        assert _get_stars(0) == "★☆☆☆☆"


class TestGetHeat:
    def test_スコア80以上は超高(self):
        assert "超高" in _get_heat(80)

    def test_スコア0は微(self):
        assert "微" in _get_heat(0)


class TestGenerateNewspaper:
    def _make_article(self, title: str, score: float) -> dict:
        return {
            "title": title,
            "url": f"https://example.com/{title.replace(' ', '-')}",
            "source": "Test Source",
            "published_at": None,
            "hn_id": None,
            "hn_score_raw": None,
            "score_composite": score,
            "score_hn": score,
            "score_reddit": 0.0,
            "score_hatena": 0.0,
            "score_trends": 0.0,
        }

    def test_ヘッダーに日付が含まれる(self):
        articles = [self._make_article("Test Article", 50.0)]
        date = datetime(2026, 5, 29, 7, 0, 0)
        result = generate_newspaper(articles, date=date)

        assert "2026年05月29日" in result

    def test_各記事のタイトルが含まれる(self):
        articles = [
            self._make_article("Article One", 80.0),
            self._make_article("Article Two", 50.0),
        ]
        result = generate_newspaper(articles)

        assert "Article One" in result
        assert "Article Two" in result

    def test_記事数が0でも例外が出ない(self):
        result = generate_newspaper([])
        assert "掲載記事数: 0 件" in result

    def test_ランク番号が付与される(self):
        articles = [self._make_article(f"Article {i}", float(100 - i)) for i in range(3)]
        result = generate_newspaper(articles)

        assert "### 1." in result
        assert "### 2." in result
        assert "### 3." in result
