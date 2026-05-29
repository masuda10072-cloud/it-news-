"""interest_scorer のユニットテスト"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.interest_scorer import (
    _normalize,
    get_hatena_score,
    get_hn_score,
    score_article,
    score_all_articles,
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestNormalize:
    def test_最大値で正規化すると100になる(self):
        assert _normalize(500, 500) == 100.0

    def test_0は0になる(self):
        assert _normalize(0, 500) == 0.0

    def test_上限を超えた値は100にクランプされる(self):
        assert _normalize(1000, 500) == 100.0

    def test_max_valが0の場合は0を返す(self):
        assert _normalize(100, 0) == 0.0


class TestGetHnScore:
    def test_raw_score_がある場合はAPI呼び出しをしない(self):
        with patch("src.interest_scorer.httpx.Client") as mock_client:
            score = get_hn_score("https://example.com", hn_score_raw=250)
        mock_client.assert_not_called()
        assert score == 50.0  # 250/500 * 100

    def test_raw_score_なしの場合はAlgolia検索を行う(self):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"hits": [{"points": 100}]}

        with patch("src.interest_scorer.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            score = get_hn_score("https://example.com/article")

        assert score == 20.0  # 100/500 * 100

    def test_API失敗時は0を返す(self):
        with patch("src.interest_scorer.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("timeout")
            score = get_hn_score("https://example.com/article")

        assert score == 0.0


class TestGetHatenaScore:
    def test_ブックマーク数から正規化スコアを返す(self):
        mock_resp = MagicMock()
        mock_resp.text = "250"

        with patch("src.interest_scorer.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            score = get_hatena_score("https://example.com/article")

        assert score == 50.0  # 250/500 * 100

    def test_API失敗時は0を返す(self):
        with patch("src.interest_scorer.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception("error")
            score = get_hatena_score("https://example.com/article")

        assert score == 0.0


class TestScoreArticle:
    def test_スコアフィールドが全て付与される(self):
        article = json.loads((FIXTURES / "sample_articles.json").read_text())[0]

        with patch("src.interest_scorer.get_hn_score", return_value=84.0):
            with patch("src.interest_scorer.get_hatena_score", return_value=20.0):
                with patch("src.interest_scorer.get_reddit_score", return_value=40.0):
                    with patch("src.interest_scorer.get_google_trends_score", return_value=60.0):
                        scored = score_article(article)

        assert "score_composite" in scored
        assert "score_hn" in scored
        assert "score_reddit" in scored
        assert "score_hatena" in scored
        assert "score_trends" in scored

        # 複合スコア = 84*0.35 + 40*0.25 + 20*0.20 + 60*0.20
        expected = round(84 * 0.35 + 40 * 0.25 + 20 * 0.20 + 60 * 0.20, 1)
        assert scored["score_composite"] == expected


class TestScoreAllArticles:
    def test_max_articles件数を超えない(self):
        articles = json.loads((FIXTURES / "sample_articles.json").read_text())

        with patch("src.interest_scorer.score_article", side_effect=lambda a: {**a, "score_composite": 50.0, "score_hn": 50.0, "score_reddit": 50.0, "score_hatena": 50.0, "score_trends": 50.0}):
            with patch("src.interest_scorer.time.sleep"):
                result = score_all_articles(articles, max_articles=2)

        assert len(result) <= 2

    def test_スコア降順でソートされる(self):
        articles = json.loads((FIXTURES / "sample_articles.json").read_text())
        scores = [90.0, 30.0, 60.0]

        def mock_score(article):
            idx = articles.index(article) if article in articles else 0
            s = scores[min(idx, len(scores) - 1)]
            return {**article, "score_composite": s, "score_hn": s, "score_reddit": 0.0, "score_hatena": 0.0, "score_trends": 0.0}

        with patch("src.interest_scorer.score_article", side_effect=mock_score):
            with patch("src.interest_scorer.time.sleep"):
                result = score_all_articles(articles, max_articles=3)

        composites = [r["score_composite"] for r in result]
        assert composites == sorted(composites, reverse=True)
