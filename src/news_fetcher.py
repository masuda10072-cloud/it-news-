"""ニュース取得モジュール: RSS フィードおよび Hacker News API からIT記事を収集する"""

import logging
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Optional

import feedparser
import httpx

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss"},
    {"name": "MIT Technology Review", "url": "https://www.technologyreview.com/feed/"},
]

GOOGLE_NEWS_RSS = (
    "https://news.google.com/rss/search"
    "?q=IT+technology+AI+software&hl=en-US&gl=US&ceid=US:en"
)

# 直近 N 時間以内の記事のみ取得する（HN は過去の人気記事も上位に来るため日時フィルタが必須）
HN_HOURS_WINDOW = 48


def _hn_api_url() -> str:
    """過去 HN_HOURS_WINDOW 時間以内の記事を日付降順で返す HN Algolia URL を生成する"""
    cutoff = int(time.time()) - HN_HOURS_WINDOW * 3600
    return (
        "https://hn.algolia.com/api/v1/search_by_date"
        f"?tags=story&hitsPerPage=30"
        f"&numericFilters=points>10,created_at_i>{cutoff}"
    )


def _parse_date(date_str: Optional[str]) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return parsedate_to_datetime(date_str)
    except Exception:
        return datetime.now(timezone.utc)


def fetch_rss_feed(feed_info: dict, max_per_feed: int = 10) -> list[dict]:
    """単一 RSS フィードから記事を取得する"""
    try:
        d = feedparser.parse(feed_info["url"])
        articles = []
        for entry in d.entries[:max_per_feed]:
            title = entry.get("title", "").strip()
            url = entry.get("link", "").strip()
            if not title or not url:
                continue
            articles.append(
                {
                    "title": title,
                    "url": url,
                    "source": feed_info["name"],
                    "published_at": _parse_date(entry.get("published")),
                    "hn_id": None,
                    "hn_score_raw": None,
                }
            )
        return articles
    except Exception as e:
        logger.warning("RSS取得エラー [%s]: %s", feed_info["name"], e)
        return []


def fetch_hn_top_stories() -> list[dict]:
    """Hacker News Algolia API から直近 48 時間のストーリーをスコア降順で取得する"""
    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(_hn_api_url())
            resp.raise_for_status()
            data = resp.json()

        articles = []
        for hit in data.get("hits", []):
            title = hit.get("title", "").strip()
            hn_id = hit.get("objectID")
            url = hit.get("url") or f"https://news.ycombinator.com/item?id={hn_id}"
            if not title:
                continue

            pub_str = hit.get("created_at", "")
            try:
                published_at = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            except Exception:
                published_at = datetime.now(timezone.utc)

            articles.append(
                {
                    "title": title,
                    "url": url,
                    "source": "Hacker News",
                    "published_at": published_at,
                    "hn_id": hn_id,
                    "hn_score_raw": hit.get("points", 0),
                }
            )
        return articles
    except Exception as e:
        logger.warning("HN取得エラー: %s", e)
        return []


def fetch_all_news(max_per_feed: int = 10) -> list[dict]:
    """全ニュースソースから記事を取得し URL で重複除去して返す"""
    articles: list[dict] = []

    articles.extend(fetch_hn_top_stories())

    for feed in RSS_FEEDS:
        articles.extend(fetch_rss_feed(feed, max_per_feed))

    articles.extend(fetch_rss_feed({"name": "Google News", "url": GOOGLE_NEWS_RSS}, max_per_feed))

    seen_urls: set[str] = set()
    unique: list[dict] = []
    for article in articles:
        url = article["url"]
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique.append(article)

    logger.info("取得記事数（重複除去後）: %d 件", len(unique))
    return unique
