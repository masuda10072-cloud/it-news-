"""通知モジュール: HTML新聞ファイルの保存と Google Chat cardsV2 通知送信

Google Chat への送信はカード形式（cardsV2）を使用する。
GITHUB_PAGES_URL が設定されている場合、カードにブラウザで開くボタンを追加する。
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_CATEGORY_ICONS = {
    "AI・機械学習":    "🤖",
    "セキュリティ":     "🔒",
    "開発・インフラ":   "🛠️",
    "ITビジネス・その他": "💼",
}


def save_html_file(html_content: str, output_dir: str = "outputs") -> Path:
    """HTML新聞を outputs/{YYYY-MM-DD}.html に保存する"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now().strftime("%Y-%m-%d")
    file_path = output_path / f"{date_str}.html"
    file_path.write_text(html_content, encoding="utf-8")

    logger.info("HTMLファイル保存完了: %s", file_path)
    return file_path


def _build_chat_card(
    articles_by_category: dict,
    html_path: Path,
    date: datetime,
    pages_url: Optional[str],
) -> dict:
    """Google Chat cardsV2 形式のカードを構築する。

    カードの構成:
    - ヘッダー: 日付・記事数
    - セクション: カテゴリ別トップ記事（日本語タイトル＋関心度）
    - ボタン: GITHUB_PAGES_URL が設定されていればHTMLを開くリンク
    """
    date_str = date.strftime("%Y年%m月%d日")
    total = sum(len(v) for v in articles_by_category.values())

    sections = []

    for category, articles in articles_by_category.items():
        if not articles:
            continue
        icon = _CATEGORY_ICONS.get(category, "📌")

        lines = []
        for art in articles[:5]:  # カテゴリごと最大5件
            title_ja = art.get("title_ja") or art["title"][:35]
            score = art.get("score_composite", 0)
            lines.append(f"・{title_ja}　<b>関心度 {score:.0f}/100</b>")

        sections.append({
            "header": f"{icon} {category}（{len(articles)}件）",
            "collapsible": False,
            "widgets": [
                {"textParagraph": {"text": "\n".join(lines)}}
            ],
        })

    # ボタン / ファイル情報セクション
    date_file = date.strftime("%Y-%m-%d")
    if pages_url:
        html_url = f"{pages_url.rstrip('/')}/outputs/{date_file}.html"
        button_widgets = [
            {
                "buttonList": {
                    "buttons": [
                        {
                            "text": "🌐 HTML新聞をブラウザで開く",
                            "onClick": {"openLink": {"url": html_url}},
                        }
                    ]
                }
            }
        ]
    else:
        button_widgets = [
            {
                "textParagraph": {
                    "text": (
                        f"💾 ファイル: <b>{html_path.name}</b><br>"
                        "ブラウザで開くには GitHub Pages を設定してください"
                    )
                }
            }
        ]

    sections.append({"widgets": button_widgets})

    return {
        "cardsV2": [
            {
                "cardId": f"it-news-{date.strftime('%Y%m%d')}",
                "card": {
                    "header": {
                        "title": "📰 IT ニュース新聞",
                        "subtitle": f"{date_str}　|　IT関連: {total}件",
                    },
                    "sections": sections,
                },
            }
        ]
    }


def send_chat_notification(
    articles_by_category: dict,
    html_path: Path,
    webhook_url: Optional[str] = None,
    date: Optional[datetime] = None,
) -> bool:
    """Google Chat Webhook に cardsV2 形式のカードを送信する"""
    if webhook_url is None:
        webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK_URL", "")

    if not webhook_url:
        logger.warning("GOOGLE_CHAT_WEBHOOK_URL が未設定のため送信をスキップします")
        return False

    if date is None:
        date = datetime.now()

    pages_url = os.environ.get("GITHUB_PAGES_URL", "").strip() or None
    payload = _build_chat_card(articles_by_category, html_path, date, pages_url)

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(webhook_url, json=payload)
            resp.raise_for_status()
        logger.info("Google Chat カード送信成功")
        return True
    except httpx.HTTPStatusError as e:
        logger.error(
            "Google Chat 送信失敗: HTTP %d %s",
            e.response.status_code, e.response.text,
        )
        return False
    except Exception as e:
        logger.error("Google Chat 送信エラー: %s", e)
        return False
