"""IT ニュース新聞 自動生成スクリプト

使い方:
    python main.py               # 通常実行（HTML生成 + Google Chat 送信）
    python main.py --dry-run     # ファイル保存のみ（Google Chat 送信スキップ）
    python main.py --max 10      # 最大記事数を指定（デフォルト 15）
"""

import argparse
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.interest_scorer import score_all_articles
from src.llm_processor import group_by_category, process_articles_with_llm
from src.news_fetcher import fetch_all_news
from src.newspaper_generator import generate_html_newspaper
from src.notifier import save_html_file, send_chat_notification

load_dotenv()

Path("outputs").mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("outputs/run.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IT ニュース新聞を生成して配信する")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="HTMLファイル保存のみ。Google Chat への送信を行わない",
    )
    parser.add_argument(
        "--max",
        type=int,
        default=15,
        dest="max_articles",
        help="掲載する最大記事数（デフォルト: 15）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logger.info("=== IT ニュース新聞 生成開始 ===")

    # 1. ニュース取得
    logger.info("ニュース取得中...")
    all_articles = fetch_all_news()
    if not all_articles:
        logger.error("ニュースを取得できませんでした。処理を終了します。")
        sys.exit(1)
    logger.info("取得完了: %d 件", len(all_articles))

    # 2. LLM でIT判定・カテゴリ分類・和訳・要約（HNスコア上位40件を対象）
    logger.info("Gemini で IT判定・分類・翻訳・要約を処理中...")
    candidates = sorted(
        all_articles, key=lambda x: x.get("hn_score_raw") or 0, reverse=True
    )[:40]
    it_articles = process_articles_with_llm(candidates)
    logger.info("IT関連記事: %d 件", len(it_articles))

    if not it_articles:
        logger.warning("IT関連記事が 0 件でした。終了します。")
        sys.exit(0)

    # 3. 関心度スコア算出（IT記事のみ対象）
    logger.info("関心度スコア算出中（API 呼び出しのため数分かかります）...")
    scored_articles = score_all_articles(it_articles, max_articles=args.max_articles)
    logger.info("スコア算出完了: %d 件", len(scored_articles))

    # 4. カテゴリ別グループ化
    articles_by_category = group_by_category(scored_articles)

    # 5. HTML 新聞生成
    logger.info("HTML 新聞を生成中...")
    top_score = scored_articles[0]["score_composite"] if scored_articles else 0
    html_content = generate_html_newspaper(
        articles_by_category,
        total_fetched=len(all_articles),
        top_score=top_score,
    )

    # 6. HTML ファイル保存
    html_path = save_html_file(html_content)
    logger.info("保存完了: %s", html_path)

    # 7. Google Chat 通知送信
    if args.dry_run:
        logger.info("--dry-run モード: Google Chat 送信をスキップしました")
    else:
        success = send_chat_notification(articles_by_category, html_path)
        if success:
            logger.info("Google Chat 送信完了")
        else:
            logger.warning("Google Chat 送信がスキップ or 失敗しました")

    logger.info("=== 完了 ===")


if __name__ == "__main__":
    main()
