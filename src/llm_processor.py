"""LLM処理モジュール: Gemini API で IT判定・カテゴリ分類・和訳・要約をバッチ処理する

30〜40件の記事タイトルを1回のAPIコールでまとめて処理することでコストと速度を最適化する。
API未設定またはエラー時はキーワードベースのフォールバック処理を行う。
"""

import json
import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)

CATEGORY_ORDER = ["AI・機械学習", "セキュリティ", "開発・インフラ", "ITビジネス・その他"]

_IT_KEYWORDS = {
    "ai", "artificial intelligence", "machine learning", "llm", "gpt", "gemini",
    "claude", "neural", "deep learning", "transformer", "diffusion",
    "software", "code", "coding", "programming", "developer", "api", "sdk",
    "cloud", "aws", "azure", "gcp", "kubernetes", "docker", "devops", "ci/cd",
    "security", "vulnerability", "hack", "breach", "cyber", "exploit", "cve",
    "zero-day", "ransomware", "phishing", "malware", "privacy", "encryption",
    "open source", "github", "linux", "python", "javascript", "typescript",
    "rust", "golang", "java", "database", "sql", "nosql", "redis", "postgres",
    "startup", "saas", "tech", "ipo", "funding", "silicon valley",
    "internet", "web", "browser", "mobile app", "algorithm", "quantum computing",
    "semiconductor", "chip", "processor", "data center", "automation",
    "microsoft", "google", "apple", "meta", "amazon", "openai", "anthropic",
    "replit", "github", "gitlab", "npm", "pypi",
}

_NON_IT_KEYWORDS = {
    "rocket launch", "orbit", "spacex", "blue origin", "nasa",
    "homebuilding", "construction", "real estate",
    "vitamin", "hormone", "medicine", "disease", "hospital", "surgery",
    "food", "restaurant", "cooking", "preservatives", "nutrition",
    "gestural", "anthropology", "archaeology",
    "climate change", "weather", "earthquake",
    "football", "basketball", "soccer", "sports",
}

_CATEGORY_KEYWORDS = {
    "AI・機械学習": [
        "ai", "llm", "gpt", "gemini", "claude", "machine learning", "neural",
        "deep learning", "openai", "anthropic", "model", "transformer", "diffusion",
        "chatbot", "copilot", "midjourney", "stable diffusion",
    ],
    "セキュリティ": [
        "security", "vulnerability", "hack", "breach", "cyber", "exploit",
        "zero-day", "ransomware", "phishing", "malware", "privacy", "cve",
        "encryption", "ban", "takedown", "dmca",
    ],
    "開発・インフラ": [
        "github", "linux", "python", "javascript", "typescript", "rust", "golang",
        "cloud", "kubernetes", "docker", "devops", "ci/cd", "open source",
        "database", "framework", "library", "programming", "developer",
        "npm", "pypi", "gitlab", "git",
    ],
}


def _extract_json(text: str) -> Optional[list]:
    """LLMレスポンスから JSON 配列を抽出する"""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]+?)```", text)
    if match:
        text = match.group(1).strip()
    start = text.find("[")
    if start == -1:
        return None
    end = text.rfind("]")
    if end == -1:
        return None
    return json.loads(text[start : end + 1])


def _keyword_category(title: str) -> str:
    """タイトルキーワードでカテゴリを推定する"""
    title_lower = title.lower()
    for cat, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in title_lower for kw in keywords):
            return cat
    return "ITビジネス・その他"


def _fallback_process(articles: list[dict]) -> list[dict]:
    """Gemini API 失敗時: キーワードベースでIT判定のみ行う（翻訳・要約なし）"""
    processed = []
    for article in articles:
        title_lower = article["title"].lower()
        if any(kw in title_lower for kw in _NON_IT_KEYWORDS):
            continue
        if not any(kw in title_lower for kw in _IT_KEYWORDS):
            continue
        processed.append(
            {
                **article,
                "category": _keyword_category(article["title"]),
                "title_ja": "",
                "summary_ja": "",
            }
        )
    logger.info("フォールバック処理: %d件 → IT関連 %d件", len(articles), len(processed))
    return processed


def process_articles_with_llm(articles: list[dict]) -> list[dict]:
    """Gemini API で全記事を1コールでバッチ処理して IT 関連記事のみ返す"""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        logger.warning("GEMINI_API_KEY 未設定。キーワードフォールバックを使用します。")
        return _fallback_process(articles)

    try:
        from google import genai
        client = genai.Client(api_key=api_key)
    except ImportError:
        logger.error("google-genai 未インストール。pip install google-genai を実行してください。")
        return _fallback_process(articles)

    articles_input = json.dumps(
        [{"id": i, "title": a["title"]} for i, a in enumerate(articles)],
        ensure_ascii=False,
    )

    prompt = f"""You are an IT news classifier for a Japanese technology newsletter. Be strict.

For each article, return a JSON array with these exact fields:
- "id": integer (the article's id)
- "is_it": boolean. true ONLY if the article is clearly about IT/software/AI/cybersecurity/cloud/developer tools/SaaS/tech companies/web technology. false for: space rockets, construction, food/nutrition, general biology/medicine, non-tech politics, weather, sports, humanities.
- "category": string or null. Set ONLY when is_it=true. Choose exactly one:
  "AI・機械学習" — AI, LLM, machine learning, ChatGPT, Gemini, Claude, neural networks, generative AI
  "セキュリティ" — cybersecurity, vulnerabilities, hacking, data breaches, CVE, privacy violations, bans for security reasons
  "開発・インフラ" — programming languages, open source projects, cloud infrastructure, DevOps, databases, dev frameworks/tools
  "ITビジネス・その他" — tech company news, funding/IPO, tech policy/regulation, internet trends, hardware, general tech
- "title_ja": string. Concise natural Japanese translation of the English title. 20-35 chars. null if is_it=false.
- "summary_ja": string. One Japanese sentence (30-50 chars) describing the key fact of what happened. Specific and factual. null if is_it=false.

Return ONLY the raw JSON array. No markdown fences, no explanation.

Articles:
{articles_input}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
        )
        results = _extract_json(response.text)
        if results is None:
            raise ValueError("JSON配列の抽出に失敗しました")

        result_map = {r["id"]: r for r in results if isinstance(r, dict)}
        processed = []
        for i, article in enumerate(articles):
            llm = result_map.get(i, {})
            if not llm.get("is_it"):
                continue
            processed.append(
                {
                    **article,
                    "category": llm.get("category") or _keyword_category(article["title"]),
                    "title_ja": llm.get("title_ja") or "",
                    "summary_ja": llm.get("summary_ja") or "",
                }
            )

        logger.info("Gemini処理完了: %d件 → IT関連 %d件", len(articles), len(processed))
        return processed

    except Exception as e:
        logger.error("Gemini処理エラー: %s。フォールバックを使用します。", e)
        return _fallback_process(articles)


def group_by_category(articles: list[dict]) -> dict[str, list[dict]]:
    """記事をカテゴリ別に分類し、カテゴリ順を固定して返す"""
    groups: dict[str, list[dict]] = {cat: [] for cat in CATEGORY_ORDER}
    for article in articles:
        cat = article.get("category", "ITビジネス・その他")
        if cat not in groups:
            cat = "ITビジネス・その他"
        groups[cat].append(article)
    return {cat: arts for cat, arts in groups.items() if arts}
