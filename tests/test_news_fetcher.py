"""news_fetcher のユニットテスト"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.news_fetcher import fetch_all_news, fetch_hn_top_stories, fetch_rss_feed

FIXTURES = Path(__file__).parent / "fixtures"


class TestFetchHnTopStories:
    def test_正常系_記事リストを返す(self):
        sample = json.loads((FIXTURES / "sample_hn_response.json").read_text())
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample

        with patch("src.news_fetcher.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            articles = fetch_hn_top_stories()

        assert len(articles) == 3
        assert articles[0]["title"] == "OpenAI releases new model with improved reasoning"
        assert articles[0]["source"] == "Hacker News"
        assert articles[0]["hn_score_raw"] == 420

    def test_異常系_ネットワークエラー時は空リストを返す(self):
        with patch("src.news_fetcher.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.side_effect = Exception(
                "Connection error"
            )
            articles = fetch_hn_top_stories()

        assert articles == []

    def test_url未設定のHN記事はフォールバックURLを使用する(self):
        sample = {
            "hits": [
                {
                    "title": "Ask HN: Best practices for AI safety",
                    "url": None,  # URL なし
                    "objectID": "99999",
                    "points": 50,
                    "created_at": "2026-05-29T00:00:00Z",
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = sample

        with patch("src.news_fetcher.httpx.Client") as mock_client:
            mock_client.return_value.__enter__.return_value.get.return_value = mock_resp
            articles = fetch_hn_top_stories()

        assert articles[0]["url"] == "https://news.ycombinator.com/item?id=99999"


class TestFetchRssFeed:
    def test_正常系_エントリーをdictに変換する(self):
        # feedparser エントリーは辞書ライクなオブジェクトなので dict で代替する
        mock_feed = MagicMock()
        mock_feed.entries = [
            {"title": "Test Article", "link": "https://example.com/article", "published": "Thu, 29 May 2026 00:00:00 +0000"},
        ]

        with patch("src.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetch_rss_feed({"name": "Test Feed", "url": "https://example.com/feed"})

        assert len(articles) == 1
        assert articles[0]["title"] == "Test Article"
        assert articles[0]["source"] == "Test Feed"

    def test_異常系_パースエラー時は空リストを返す(self):
        with patch("src.news_fetcher.feedparser.parse", side_effect=Exception("Parse error")):
            articles = fetch_rss_feed({"name": "Test", "url": "https://example.com/feed"})

        assert articles == []

    def test_タイトルまたはURLが空のエントリーはスキップする(self):
        mock_feed = MagicMock()
        mock_feed.entries = [
            {"title": "", "link": "https://example.com/1", "published": None},
            {"title": "Valid Title", "link": "", "published": None},
            {"title": "Good Article", "link": "https://example.com/2", "published": None},
        ]

        with patch("src.news_fetcher.feedparser.parse", return_value=mock_feed):
            articles = fetch_rss_feed({"name": "Test", "url": "https://example.com/feed"})

        assert len(articles) == 1
        assert articles[0]["title"] == "Good Article"


class TestFetchAllNews:
    def test_URL重複が除去される(self):
        duplicate_article = {
            "title": "Duplicate Article",
            "url": "https://example.com/dup",
            "source": "HN",
            "published_at": None,
            "hn_id": None,
            "hn_score_raw": 100,
        }

        with patch("src.news_fetcher.fetch_hn_top_stories", return_value=[duplicate_article]):
            with patch("src.news_fetcher.fetch_rss_feed", return_value=[duplicate_article]):
                articles = fetch_all_news()

        urls = [a["url"] for a in articles]
        assert len(urls) == len(set(urls)), "重複 URL が残っています"
