.PHONY: help install test lint format clean run

help: ## このヘルプメッセージを表示
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 依存関係をインストール
	uv sync

test: ## テストを実行
	uv run pytest -v

test-cov: ## カバレッジ付きでテストを実行
	uv run pytest --cov=. --cov-report=html --cov-report=term

lint: ## コードをリント
	uv run ruff check .

format: ## コードをフォーマット
	uv run ruff format .

format-check: ## フォーマットチェック（変更なし）
	uv run ruff format --check .

clean: ## 一時ファイルを削除
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -f *.log
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

run: ## FAQスクリプトを実行
	uv run python src/main.py

pre-commit-install: ## pre-commitフックをインストール
	uv run pre-commit install

pre-commit-run: ## pre-commitを全ファイルで実行
	uv run pre-commit run --all-files
