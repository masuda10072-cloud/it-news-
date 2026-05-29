# 📰 IT ニュース新聞 自動生成システム

IT 関連ニュースを毎朝自動収集し、世間の関心度スコアを付与した新聞を生成。
Google Chat へ配信し、Markdown ファイルとして Git で履歴管理する。

## アーキテクチャ

```
GitHub Actions (毎日 07:00 JST)
    └── main.py
         ├── src/news_fetcher.py      # HN API + RSS フィード
         ├── src/interest_scorer.py  # HN / Reddit / はてブ / Google Trends
         ├── src/newspaper_generator.py  # Markdown 生成
         └── src/notifier.py         # Google Chat 送信 + ファイル保存
```

## 関心度スコアの計算式

```
スコア(0-100) = HN(35%) + Reddit(25%) + はてブ(20%) + Google Trends(20%)
```

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、各値を設定する。

```bash
cp .env.example .env
```

| 変数名 | 取得方法 |
|---|---|
| `REDDIT_CLIENT_ID` | https://www.reddit.com/prefs/apps でアプリ作成 |
| `REDDIT_CLIENT_SECRET` | 同上 |
| `REDDIT_USER_AGENT` | `ITNewsBot/1.0 by <あなたのRedditユーザー名>` |
| `GOOGLE_CHAT_WEBHOOK_URL` | 下記「Google Chat Webhook 設定手順」を参照 |

### 3. Google Chat Webhook の設定

1. Google Chat を開く
2. 通知を受け取りたい**スペース**を開く
3. スペース名横の「▾」→「**アプリと統合を管理**」をクリック
4. 「**Webhook を追加**」→ 名前を入力（例: `IT ニュース新聞`）→「保存」
5. 表示された **Webhook URL** をコピーして `.env` に設定

### 4. Reddit API の設定

1. https://www.reddit.com/prefs/apps にアクセス
2. 「**create another app**」をクリック
3. 種類: `script` を選択、名前: `ITNewsBot`、redirect uri: `http://localhost`
4. 作成後に表示される **client id**（アプリ名下の文字列）と **secret** をコピー

### 5. ローカルで実行

```bash
# 通常実行（Google Chat 送信あり）
python main.py

# ドライラン（ファイル保存のみ、送信なし）
python main.py --dry-run

# 記事数を指定
python main.py --max 10
```

### 6. GitHub Actions の設定

1. GitHub にリポジトリを作成してプッシュ
2. リポジトリの **Settings → Secrets and variables → Actions** を開く
3. 以下の Secrets を追加:
   - `REDDIT_CLIENT_ID`
   - `REDDIT_CLIENT_SECRET`
   - `REDDIT_USER_AGENT`
   - `GOOGLE_CHAT_WEBHOOK_URL`
4. `.github/workflows/daily_news.yml` が自動的に毎日 07:00 JST に実行される
5. **手動実行**: Actions タブ → `IT ニュース新聞 自動生成` → `Run workflow`

## テスト実行

```bash
pytest tests/ -v
```

## 出力例

```markdown
# 📰 IT ニュース新聞 — 2026年05月29日

> 🗓️ 生成日時: 2026-05-29 07:00 JST
> 📊 本日の最高関心度スコア: 92/100
> 📰 掲載記事数: 15 件

---

## 📋 本日のトップニュース

### 1. OpenAI releases new model with improved reasoning
**関心度: ★★★★★ (92/100)** | 注目度: 🔥 超高
📊 HN:84 | Reddit:48 | はてブ:32 | Trends:60
📰 ソース: Hacker News
🔗 [記事を読む](https://openai.com/blog/...)
```
