## 特徴

- 🔄 週次自動更新（毎週金曜日16:00 JST）
- 📊 差分検出とレポート生成
- 🔍 変更履歴の追跡
- 🤖 自動PR作成・マージ
- 📝 詳細なログ記録
- ♻️ エラーリトライ機能

## クイックスタート

### 必要な環境
- Python 3.10以上
- uv（最新推奨）

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/norikmb/pokemon-card-rules-faq.git
cd pokemon-card-rules-faq

# 依存関係をインストール
uv sync

# スクリプトを実行
uv run python main.py
```

## セットアップ（uv）

```bash
# 依存関係を同期
uv sync

# FAQ 取得を実行
uv run python main.py

# テスト / リント
uv run pytest -v
uv run ruff check .
uv run ruff format .
```

## プロジェクト構成

```
pokemon-card-rules-faq/
├── main.py              # メインスクリプト
├── config.py            # 設定ファイル
├── faq_data.json        # FAQ データ（自動生成）
├── diff_report.json     # 差分レポート（自動生成）
├── faq_update.log       # ログファイル（自動生成）
├── tests/               # テストコード
│   ├── test_main.py
│   └── fixtures/
├── .github/
│   └── workflows/
│       ├── update-faq.yml    # FAQ自動更新ワークフロー
│       └── ruff-action.yml   # コード品質チェック
├── pyproject.toml       # プロジェクト設定
└── README.md
```

## 使い方

### 手動実行

```bash
# FAQ データを取得
uv run python main.py

# テストを実行
uv run pytest

# コードフォーマット
uv run ruff format

# リント
uv run ruff check
```

### GitHub Actions

このプロジェクトは GitHub Actions で自動化されています：

- **FAQ 自動更新**: 毎週金曜日 16:00（JST）に実行
- **コード品質チェック**: プッシュ時に Ruff でリント

## 出力データ

### faq_data.json
全 FAQ データを JSON 形式で保存：

```json
[
  {
    "question_hash": "ハッシュ値",
    "question": "質問内容",
    "answer": "回答内容"
  }
]
```

### diff_report.json
前回との差分レポート：

```json
{
  "summary": {
    "total_old": 100,
    "total_new": 105,
    "added": 5,
    "removed": 0,
    "modified": 2
  },
  "added": [...],
  "removed": [...],
  "modified": [...]
}
```

## 設定のカスタマイズ

`config.py` で以下の設定を変更できます：

- `MAX_RETRIES`: リトライ回数（デフォルト: 3）
- `RETRY_DELAY`: リトライ待機時間（デフォルト: 5秒）
- `SLEEP_MIN` / `SLEEP_MAX`: リクエスト間隔（デフォルト: 0.5-2.0秒）

### Pre-commitフックのセットアップ

```bash
make pre-commit-install
```
