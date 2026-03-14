## 特徴

- 🔄 週次自動更新（毎週金曜日16:00 JST）
- 📊 差分検出とレポート生成
- 🔍 変更履歴の追跡
- 🤖 自動PR作成・マージ
- 📝 詳細なログ記録
- ♻️ エラーリトライ機能

## クイックスタート

### 必要な環境
- Python 3.14以上
- uv（最新推奨）

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/norikmb/pokemon-card-rules-faq.git
cd pokemon-card-rules-faq

# 依存関係をインストール
uv sync

# スクリプトを実行
uv run python src/main.py
```

## セットアップ（uv）

```bash
# 依存関係を同期
uv sync

# FAQ 取得を実行
uv run python src/main.py

# テスト / リント
uv run pytest -v
uv run ruff check .
uv run ruff format .
```

## プロジェクト構成

```
pokemon-card-rules-faq/
├── src/
│   ├── main.py          # メインスクリプト
│   ├── config.py        # 設定ファイル
│   └── doc.md           # 詳細ドキュメント
├── tests/               # テストコード
│   ├── test_main.py
│   └── fixtures/
├── .github/
│   └── workflows/
│       ├── update-faq.yml    # FAQ自動更新ワークフロー
│       ├── test.yml          # テストワークフロー
│       └── ruff-action.yml   # コード品質チェック
├── faq_data.json        # FAQ データ（自動生成）
├── diff_report.json     # 差分レポート（自動生成）
├── faq_update.log       # ログファイル（自動生成）
├── pyproject.toml       # プロジェクト設定
├── Makefile             # ビルドタスク
├── .gitignore           # Git除外設定
└── README.md
```

## 使い方

### 手動実行

```bash
# FAQ データを取得
uv run python src/main.py

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

## note への自動投稿

差分が発生した場合に、`diff_report.json` の内容をMarkdown化して note の下書きへ自動投稿できます（noteの非公式APIを利用）。

### 環境変数

- `NOTE_AUTO_POST=true` : 自動投稿を有効化
- `NOTE_COOKIE=...` : noteログイン済みCookie文字列
- `NOTE_USERNAME=...` : 任意。投稿後URLログ表示に利用
- `NOTE_API_BASE_URL=https://note.com` : 通常は変更不要
- `NOTE_USER_AGENT=...` : 任意。通常は変更不要

### 出力ファイル

- 差分JSON: `diff_report.json`
- 投稿用Markdown: `diff_report.md`

### 注意

- note APIは非公式のため、将来的に仕様変更される可能性があります。
- `NOTE_COOKIE` は機密情報のため、CI Secretや環境変数で安全に管理してください。

### GitHub Actionsでの設定

`.github/workflows/update-faq.yml` では以下の Repository Secrets を読むようにしています。

- `NOTE_AUTO_POST` (`true` / `false`)
- `NOTE_COOKIE`
- `NOTE_USERNAME`（任意）

`NOTE_AUTO_POST=true` かつ `NOTE_COOKIE` が設定されている場合のみ、差分発生時に note 下書き投稿を実行します。

`Update FAQ` ワークフロー内では処理を分離しており、`update_faq` ジョブで差分生成、`post_note` ジョブで note 投稿を実行します（`diff_report.json` を artifact で受け渡し）。

手動確認する場合は、GitHub の Actions タブで `Update FAQ` を `Run workflow` から起動してください。

ローカルで `post_note` 相当だけ確認したい場合:

- `make run-note-post`
- 投稿を無効化して動作だけ確認: `NOTE_AUTO_POST=false make run-note-post`

### NOTE_COOKIE の作り方（ブラウザ手動）

1. ブラウザで note にログインする
2. 開発者ツールを開く（Network タブ）
3. note 上で記事作成や下書き保存などの操作を1回行う
4. `https://note.com/api/v1/text_notes` へのリクエストを選択する
5. Request Headers の `cookie` を丸ごとコピーする
6. GitHub Repository Secrets の `NOTE_COOKIE` に貼り付ける

補足:

- `NOTE_COOKIE` は `name=value; name2=value2; ...` 形式の1行文字列です
- Cookie期限切れで投稿失敗する場合は、同じ手順で再取得して更新してください
- 機密情報なのでログ出力・コミット・Issue貼り付けは避けてください

### Secrets 登録例

- `NOTE_AUTO_POST` : `true`
- `NOTE_COOKIE` : `sessid=...; logged_in=...; ...`
- `NOTE_USERNAME` : `あなたのnoteユーザー名`（任意）

### 投稿内容について

直近 7 日以内に発売された拡張パック・構築デッキがある場合、その商品名と発売日を冒頭に記載します。
該当商品がない場合は「今週更新されたQ&Aをまとめています。」という文言になります。
