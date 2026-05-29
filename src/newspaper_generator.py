"""HTML新聞生成モジュール: カテゴリ別・コンパクトレイアウトのHTML新聞を生成する"""

import html as _html
from datetime import datetime
from typing import Optional

_CATEGORY_CONFIG = {
    "AI・機械学習":    {"icon": "🤖", "color": "#4f46e5", "light": "#eef2ff", "border": "#818cf8"},
    "セキュリティ":     {"icon": "🔒", "color": "#dc2626", "light": "#fef2f2", "border": "#f87171"},
    "開発・インフラ":   {"icon": "🛠️", "color": "#059669", "light": "#ecfdf5", "border": "#34d399"},
    "ITビジネス・その他": {"icon": "💼", "color": "#d97706", "light": "#fffbeb", "border": "#fbbf24"},
}
_DEFAULT_CONFIG = {"icon": "📌", "color": "#6b7280", "light": "#f9fafb", "border": "#9ca3af"}

_CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'Helvetica Neue','Noto Sans JP',sans-serif;background:#f0f2f5;color:#1a1a2e;line-height:1.5;font-size:15px}
.wrap{max-width:860px;margin:0 auto;padding:14px}
.hd{text-align:center;background:#1a1a2e;color:#fff;padding:18px 16px 14px;border-radius:8px;margin-bottom:12px}
.hd-sub{font-size:.7rem;color:#94a3b8;letter-spacing:3px;text-transform:uppercase}
.hd-ttl{font-size:1.75rem;font-weight:900;letter-spacing:3px;margin-top:4px}
.hd-date{font-size:.95rem;color:#cbd5e1;margin-top:6px}
.stats{display:flex;flex-wrap:wrap;gap:12px;justify-content:center;background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:9px 14px;margin-bottom:18px;font-size:.8rem;color:#64748b}
.sec{margin-bottom:18px}
.sec-hd{display:flex;align-items:center;gap:7px;padding:8px 13px;border-radius:5px 5px 0 0;font-size:.92rem;font-weight:700;color:#fff}
.arts{border-radius:0 0 5px 5px;overflow:hidden}
.art{background:#fff;border-bottom:1px solid #f1f5f9;padding:10px 14px;border-left:4px solid transparent}
.art:last-child{border-bottom:none;border-radius:0 0 5px 5px}
.art:hover{background:#f8fafc}
.art-row1{display:flex;align-items:baseline;gap:6px;flex-wrap:wrap}
.art-num{font-size:.75rem;font-weight:700;color:#94a3b8;min-width:18px;flex-shrink:0}
.art-en{font-size:.88rem;font-weight:600;color:#1d4ed8;text-decoration:none}
.art-en:hover{text-decoration:underline}
.art-ja{font-size:.82rem;color:#475569;white-space:nowrap}
.art-row2{margin-top:4px;font-size:.78rem;color:#64748b;display:flex;flex-wrap:wrap;align-items:center;gap:8px;padding-left:24px}
.art-summary{color:#374151}
.badge{background:#f1f5f9;color:#475569;padding:1px 7px;border-radius:10px;font-size:.72rem;white-space:nowrap}
.score-b{background:#dbeafe;color:#1d4ed8;padding:1px 7px;border-radius:10px;font-size:.72rem;font-weight:700;white-space:nowrap}
.ft{text-align:center;font-size:.72rem;color:#94a3b8;padding:18px 0 10px;border-top:1px solid #e2e8f0;margin-top:6px}
/* Rate limit warning */
.rate-warn{background:#fef3c7;border:1px solid #f59e0b;border-radius:6px;padding:10px 14px;margin-bottom:14px;font-size:.8rem;color:#92400e;display:flex;align-items:flex-start;gap:8px}
.art-ja-na{color:#94a3b8;font-style:italic}
.art-summary-na{color:#f59e0b;font-style:italic}
/* Legend */
.legend{border:1px solid #e2e8f0;border-radius:6px;margin-top:8px;margin-bottom:16px;background:#fff;overflow:hidden}
.legend summary{cursor:pointer;padding:9px 14px;font-size:.8rem;font-weight:600;color:#475569;user-select:none;list-style:none;display:flex;align-items:center;gap:6px}
.legend summary::-webkit-details-marker{display:none}
.legend summary::after{content:"▸";margin-left:auto;font-size:.7rem;color:#94a3b8}
details[open].legend summary::after{content:"▾"}
.legend-body{padding:12px 14px;border-top:1px solid #f1f5f9}
.legend h4{font-size:.78rem;font-weight:700;color:#1a1a2e;margin:10px 0 4px}
.legend h4:first-child{margin-top:0}
.legend p{font-size:.75rem;color:#475569;line-height:1.6}
.legend table{width:100%;border-collapse:collapse;font-size:.73rem;margin-top:6px}
.legend th{background:#f8fafc;color:#374151;font-weight:600;padding:5px 8px;text-align:left;border:1px solid #e2e8f0}
.legend td{padding:5px 8px;border:1px solid #e2e8f0;color:#475569;vertical-align:top}
.legend td:first-child{font-family:monospace;font-weight:700;color:#1d4ed8;white-space:nowrap}
.star-table td:first-child{color:#f59e0b;font-family:inherit}
@media(max-width:600px){
  .hd-ttl{font-size:1.3rem;letter-spacing:1px}
  .art-en{font-size:.84rem}
  .art-ja{font-size:.78rem}
  .stats{font-size:.75rem;gap:8px}
  .legend table{font-size:.68rem}
}
"""


def _e(text: str) -> str:
    """HTMLエスケープ"""
    return _html.escape(str(text))


def _score_stars(score: float) -> str:
    if score >= 80:
        return "★★★★★"
    if score >= 60:
        return "★★★★☆"
    if score >= 40:
        return "★★★☆☆"
    if score >= 20:
        return "★★☆☆☆"
    return "★☆☆☆☆"


def _article_html(article: dict, rank: int, border_color: str) -> str:
    title_en = _e(article["title"])
    title_ja = _e(article.get("title_ja", ""))
    summary_ja = _e(article.get("summary_ja", ""))
    url = _e(article["url"])
    score = article.get("score_composite", 0)
    hn = article.get("score_hn", 0)
    source = _e(article.get("source", ""))

    llm_ok = article.get("llm_ok", True)
    if title_ja:
        title_ja_html = f'<span class="art-ja">({title_ja})</span>'
    elif not llm_ok:
        title_ja_html = '<span class="art-ja art-ja-na">（⚠️ APIレート制限のため和訳取得不可）</span>'
    else:
        title_ja_html = ""

    if summary_ja:
        summary_html = f'<span class="art-summary">📝 {summary_ja}</span>'
    elif not llm_ok:
        summary_html = '<span class="art-summary-na">📝 APIレート制限のため要約を取得できませんでした</span>'
    else:
        summary_html = ""
    hn_html = f'<span class="badge">HN:{hn:.0f}</span>' if hn > 0 else ""

    return f"""
    <div class="art" style="border-left-color:{border_color}">
      <div class="art-row1">
        <span class="art-num">{rank}.</span>
        <a href="{url}" class="art-en" target="_blank" rel="noopener">{title_en}</a>
        {title_ja_html}
      </div>
      <div class="art-row2">
        {summary_html}
        <span class="score-b">関心度 {score:.0f}/100 {_score_stars(score)}</span>
        {hn_html}
        <span class="badge">{source}</span>
      </div>
    </div>"""


def _category_section_html(category: str, articles: list[dict], start_rank: int) -> tuple[str, int]:
    cfg = _CATEGORY_CONFIG.get(category, _DEFAULT_CONFIG)
    arts_html = ""
    rank = start_rank
    for art in articles:
        arts_html += _article_html(art, rank, cfg["border"])
        rank += 1

    section = f"""
  <div class="sec">
    <div class="sec-hd" style="background:{cfg['color']}">{cfg['icon']} {_e(category)}</div>
    <div class="arts">{arts_html}</div>
  </div>"""
    return section, rank


def generate_html_newspaper(
    articles_by_category: dict[str, list[dict]],
    date: Optional[datetime] = None,
    total_fetched: int = 0,
    top_score: float = 0,
) -> str:
    """カテゴリ別コンパクトHTML新聞を生成する"""
    if date is None:
        date = datetime.now()

    date_ja = date.strftime("%Y年%m月%d日")
    generated_at = date.strftime("%Y-%m-%d %H:%M")
    total_it = sum(len(v) for v in articles_by_category.values())

    # レート制限の確認（いずれかの記事で llm_ok=False なら警告）
    all_articles = [a for arts in articles_by_category.values() for a in arts]
    rate_limited = any(not a.get("llm_ok", True) for a in all_articles)
    fail_reason = next(
        (a.get("llm_fail_reason", "") for a in all_articles if not a.get("llm_ok", True)), ""
    )

    rate_warn_html = ""
    if rate_limited:
        rate_warn_html = f"""
  <div class="rate-warn">
    <span>⚠️</span>
    <span>
      <b>Gemini API {fail_reason}のため、和訳・要約を取得できませんでした。</b><br>
      時間をおいて再実行すると翻訳・要約が表示されます。記事リンクは正常です。
    </span>
  </div>"""

    stats_html = f"""
  <div class="stats">
    <span>🗓️ {generated_at} JST</span>
    <span>📰 取得 {total_fetched}件 → IT関連 {total_it}件</span>
    <span>📊 最高関心度 {top_score:.0f}/100</span>
  </div>"""

    categories_html = ""
    rank = 1
    for category, articles in articles_by_category.items():
        if not articles:
            continue
        section, rank = _category_section_html(category, articles, rank)
        categories_html += section

    legend_html = """
  <details class="legend">
    <summary>📊 関心度スコアの算出方法・バッジの見方</summary>
    <div class="legend-body">
      <h4>関心度スコア（0〜100点）の計算式</h4>
      <p>下記4指標を正規化（0〜100）した後、重み付き平均で算出します。</p>
      <p style="margin-top:6px;font-family:monospace;font-size:.75rem;background:#f8fafc;padding:6px 10px;border-radius:4px;color:#374151">
        スコア = HN × 35% ＋ Reddit × 25% ＋ はてブ × 20% ＋ Trends × 20%
      </p>
      <h4>バッジの意味</h4>
      <table>
        <thead><tr><th>バッジ表示</th><th>指標</th><th>重み</th><th>正規化の上限</th><th>何を表すか</th></tr></thead>
        <tbody>
          <tr><td>HN:XX</td><td>Hacker News スコア</td><td>35%</td><td>500pt → 100</td><td>技術者コミュニティ (Hacker News) での投票数。多いほどエンジニアから注目されている記事。</td></tr>
          <tr><td>Reddit:XX</td><td>Reddit アップボート</td><td>25%</td><td>5,000票 → 100</td><td>technology / programming 等のサブレディットでのアップボート数。</td></tr>
          <tr><td>はてブ:XX</td><td>はてなブックマーク</td><td>20%</td><td>500件 → 100</td><td>はてなブックマーク登録数。主に日本語圏の関心度を示す。</td></tr>
          <tr><td>Trends:XX</td><td>Google Trends</td><td>20%</td><td>100 = 最大関心</td><td>過去24時間のGoogle検索トレンドスコア（0〜100）。</td></tr>
        </tbody>
      </table>
      <h4>★の基準</h4>
      <table class="star-table">
        <thead><tr><th>表示</th><th>スコア範囲</th><th>注目度の目安</th></tr></thead>
        <tbody>
          <tr><td>★★★★★</td><td>80〜100</td><td>複数プラットフォームで爆発的に拡散中</td></tr>
          <tr><td>★★★★☆</td><td>60〜79</td><td>IT業界全体で広く話題になっている</td></tr>
          <tr><td>★★★☆☆</td><td>40〜59</td><td>特定コミュニティで注目を集めている</td></tr>
          <tr><td>★★☆☆☆</td><td>20〜39</td><td>一定の関心あり、今後拡散の可能性</td></tr>
          <tr><td>★☆☆☆☆</td><td>0〜19</td><td>ニッチな話題・速報段階（まだスコアが低い）</td></tr>
        </tbody>
      </table>
      <p style="margin-top:10px;font-size:.7rem;color:#94a3b8">
        ※ 分類・翻訳・要約は Gemini AI が自動生成。スコアはリアルタイム取得データに基づきます。<br>
        ※ 新鮮なニュースはまだ投票数が少なく低スコアになる場合があります。
      </p>
    </div>
  </details>"""

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>IT ニュース新聞 — {date_ja}</title>
  <style>{_CSS}</style>
</head>
<body>
<div class="wrap">
  <div class="hd">
    <div class="hd-sub">Daily IT News Digest</div>
    <div class="hd-ttl">📰 IT ニュース新聞</div>
    <div class="hd-date">{date_ja}</div>
  </div>
  {stats_html}
  {rate_warn_html}
  {categories_html}
  {legend_html}
  <div class="ft">
    自動生成 by IT ニュース新聞システム
  </div>
</div>
</body>
</html>"""
