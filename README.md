# Kaggle Competition Scraper 🏆

Kaggleコンペティションの情報を包括的にスクレイピングし、構造化された形式（JSON・Markdown）で出力するPythonアプリケーションです。

## 🌟 主な機能

- **コンペティション概要の取得**: タイトル、説明、評価指標、賞金情報など
- **ディスカッションフォーラムの取得**: 全スレッドと投稿内容の抽出
- **ノートブック情報の取得**: Kaggle API経由でコード情報を取得
- **複数出力形式**: JSON、Markdown、CSVでのデータ出力
- **Webインターフェース**: Streamlitによる使いやすいUI

## 📋 必要要件

- Python 3.7+
- Kaggle API認証（ノートブック取得用）

## 🚀 セットアップ

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd kaggle-competition-scraper2
```

### 2. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 3. Kaggle API認証の設定

#### オプション1: kaggle.jsonファイルを使用

1. [Kaggle](https://www.kaggle.com)にログイン
2. Account → API → "Create New API Token"をクリック
3. ダウンロードされた`kaggle.json`を以下の場所に配置:
   - **Linux/Mac**: `~/.kaggle/kaggle.json`
   - **Windows**: `C:\\Users\\<username>\\.kaggle\\kaggle.json`

#### オプション2: 環境変数を使用

```bash
export KAGGLE_USERNAME="your-username"
export KAGGLE_KEY="your-api-key"
```

## 💻 使用方法

### Streamlitアプリでの使用

```bash
streamlit run streamlit_app.py
```

ブラウザで `http://localhost:8501` にアクセスし、以下の手順で使用：

1. 左サイドバーでスクレイピングオプションを設定
2. コンペティションURLを入力（例: `https://www.kaggle.com/competitions/titanic`）
3. "Start Scraping"ボタンをクリック
4. 結果の確認とダウンロード

### Pythonスクリプトでの使用

```python
from kaggle_scraper import KaggleCompetitionScraper

# スクレイパーの初期化
scraper = KaggleCompetitionScraper()

# コンペティションデータの取得
data = scraper.scrape_all_competition_data("https://www.kaggle.com/competitions/titanic")

# JSONファイルとして保存
scraper.save_to_json(data, "titanic_data.json")

# Markdownレポートの生成
markdown_report = scraper.generate_markdown_report(data)
with open("titanic_report.md", "w", encoding="utf-8") as f:
    f.write(markdown_report)
```

## 📊 出力形式

### JSON形式

```json
{
  "competition": {
    "id": "titanic",
    "title": "Titanic - Machine Learning from Disaster",
    "description": "...",
    "timeline": {...},
    "reward": "$10,000",
    "evaluation": "..."
  },
  "discussionThreads": [
    {
      "id": "12345",
      "title": "Having issues with the dataset",
      "author": "KaggleUser123",
      "replyCount": 5,
      "voteCount": 10,
      "posts": [...]
    }
  ],
  "notebooks": [
    {
      "id": "67890",
      "title": "Titanic Survival Prediction",
      "author": "DataScientistX",
      "votes": 120,
      "url": "https://www.kaggle.com/..."
    }
  ]
}
```

### Markdown形式

構造化されたMarkdownレポートを生成し、以下の情報を含みます：

- コンペティション概要
- ディスカッションスレッド一覧（投稿内容含む）
- ノートブック一覧（投票数、作者情報含む）

## ⚙️ カスタマイズオプション

### スクレイピング設定

- `max_threads`: 取得するディスカッション数の上限（デフォルト: 20）
- `max_notebooks`: 取得するノートブック数の上限（デフォルト: 30）
- `max_posts_per_thread`: スレッドあたりの投稿数上限（デフォルト: 10）

### レート制限対策

```python
import time

# リクエスト間隔の調整
scraper.session.headers.update({
    'User-Agent': 'Your Custom User Agent'
})

# 各リクエスト後の待機時間
time.sleep(1)  # 1秒待機
```

## 🔧 トラブルシューティング

### よくある問題

#### 1. Kaggle API認証エラー

```
Error: Could not authenticate with Kaggle API
```

**解決方法:**
- `kaggle.json`ファイルが正しい場所にあることを確認
- ファイルの権限を確認: `chmod 600 ~/.kaggle/kaggle.json`

#### 2. スクレイピングエラー

```
Error scraping competition overview
```

**解決方法:**
- コンペティションURLが正しいことを確認
- インターネット接続を確認
- レート制限に引っかかっている可能性があるため、時間をおいて再試行

#### 3. セレクターが見つからない

Kaggleのページ構造が変更された場合、以下のファイルのセレクターを更新してください：

- `kaggle_scraper.py`の各`_extract_*`メソッド

## 📝 データ利用時の注意事項

- Kaggleの利用規約に従ってデータを使用してください
- 過度なリクエストを避け、適切な間隔でスクレイピングを行ってください
- 取得したデータの再配布時は著作権に注意してください

## 🤝 貢献

バグ報告や機能追加の提案は、Issueやプルリクエストでお知らせください。

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🔗 関連リンク

- [Kaggle API Documentation](https://github.com/Kaggle/kaggle-api)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [BeautifulSoup Documentation](https://www.crummy.com/software/BeautifulSoup/bs4/doc/)