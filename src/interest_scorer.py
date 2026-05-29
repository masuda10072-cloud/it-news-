"""関心度スコア算出モジュール

HN / Reddit / はてなブックマーク / Google Trends の 4 指標を
重み付き平均して 0-100 のスコアを算出する。
各 API の失敗はスコア 0 として扱い、処理を継続する。
"""

import logging
import os
import time
from typing import Optional
from urllib.parse import quote

import httpx
import praw
from pytrends.request import TrendReq

logger = logging.getLogger(__name__)

# 各指標の重み（合計 1.0）
WEIGHTS = {
    "hn": 0.35,
    "reddit": 0.25,
    "hatena": 0.20,
    "trends": 0.20,
}

# 正規化の上限値（経験値）
HN_MAX_POINTS = 500
REDDIT_MAX_UPVOTES = 5000
HATENA_MAX_BOOKMARKS = 500

# Reddit で検索するサブレディット
REDDIT_SUBREDDITS = ["technology", "programming", "MachineLearning", "artificial"]


def _normalize(value: float, max_val: float) -> float:
    """値を 0-100 に正規化する"""
    if max_val <= 0:
        return 0.0
    return min(100.0, (value / max_val) * 100.0)


def get_hn_score(url: str, hn_score_raw: Optional[int] = None) -> float:
    """HN スコアを取得・正規化する。raw スコアがある場合はそれを優先する"""
    if hn_score_raw is not None:
        return _normalize(hn_score_raw, HN_MAX_POINTS)

    # URL で HN Algolia を検索してスコアを取得
    try:
        search_url = (
            "https://hn.algolia.com/api/v1/search"
            f"?query={quote(url, safe='')}&tags=story"
            "&restrictSearchableAttributes=url"
        )
        with httpx.Client(timeout=5) as client:
            resp = client.get(search_url)
            data = resp.json()
        hits = data.get("hits", [])
        if hits:
            max_points = max(h.get("points", 0) for h in hits)
            return _normalize(max_points, HN_MAX_POINTS)
    except Exception as e:
        logger.debug("HNスコア取得エラー: %s", e)
    return 0.0


def get_hatena_score(url: str) -> float:
    """はてなブックマーク数を取得・正規化する"""
    try:
        api_url = f"https://bookmark.hatenaapis.com/count/entry?url={quote(url, safe='')}"
        with httpx.Client(timeout=5) as client:
            resp = client.get(api_url)
            count = int(resp.text.strip())
        return _normalize(count, HATENA_MAX_BOOKMARKS)
    except Exception as e:
        logger.debug("はてなスコア取得エラー: %s", e)
    return 0.0


def get_reddit_score(title: str) -> float:
    """Reddit で記事タイトルを検索し、最大 upvote 数を正規化して返す"""
    client_id = os.environ.get("REDDIT_CLIENT_ID", "")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        logger.debug("Reddit APIキー未設定のためスキップ")
        return 0.0

    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=os.environ.get("REDDIT_USER_AGENT", "ITNewsBot/1.0"),
        )
        max_upvotes = 0
        query = title[:100]
        for sub in REDDIT_SUBREDDITS:
            results = reddit.subreddit(sub).search(query, limit=3, time_filter="day")
            for post in results:
                max_upvotes = max(max_upvotes, post.score)
        return _normalize(max_upvotes, REDDIT_MAX_UPVOTES)
    except Exception as e:
        logger.debug("Redditスコア取得エラー: %s", e)
    return 0.0


def get_google_trends_score(title: str) -> float:
    """Google Trends で過去 24 時間の関心度を取得する"""
    # タイトルの先頭 3 単語をキーワードとして使用
    keywords = " ".join(title.split()[:3])
    try:
        pytrends = TrendReq(hl="en-US", tz=540)  # tz=540 は JST
        pytrends.build_payload([keywords], timeframe="now 1-d", geo="")
        data = pytrends.interest_over_time()
        if not data.empty and keywords in data.columns:
            return float(data[keywords].mean())
    except Exception as e:
        logger.debug("Google Trendsスコア取得エラー: %s", e)
    return 0.0


def score_article(article: dict) -> dict:
    """1 記事に関心度スコアを算出して付与する"""
    hn = get_hn_score(article["url"], article.get("hn_score_raw"))
    hatena = get_hatena_score(article["url"])
    reddit = get_reddit_score(article["title"])
    trends = get_google_trends_score(article["title"])

    composite = (
        hn * WEIGHTS["hn"]
        + reddit * WEIGHTS["reddit"]
        + hatena * WEIGHTS["hatena"]
        + trends * WEIGHTS["trends"]
    )

    return {
        **article,
        "score_composite": round(composite, 1),
        "score_hn": round(hn, 1),
        "score_reddit": round(reddit, 1),
        "score_hatena": round(hatena, 1),
        "score_trends": round(trends, 1),
    }


def score_all_articles(
    articles: list[dict],
    max_articles: int = 15,
    api_sleep: float = 0.5,
) -> list[dict]:
    """全記事にスコアを算出し、上位 max_articles 件をスコア降順で返す"""
    # HN スコアで事前に絞り込んでから API を呼ぶことで呼び出し回数を削減
    sorted_initial = sorted(
        articles, key=lambda x: x.get("hn_score_raw") or 0, reverse=True
    )
    candidates = sorted_initial[: max_articles * 2]

    scored = []
    for i, article in enumerate(candidates, 1):
        logger.info(
            "スコア算出中 (%d/%d): %s", i, len(candidates), article["title"][:60]
        )
        scored.append(score_article(article))
        time.sleep(api_sleep)

    return sorted(scored, key=lambda x: x["score_composite"], reverse=True)[
        :max_articles
    ]
