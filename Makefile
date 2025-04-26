.PHONY: run setup clean test help

# デフォルトのターゲット: ヘルプ表示
default: help

# 任意のPythonファイルを実行
# 使用例: make run app/test.py
# 使用例: make run app/another_script.py
run:
	@if [ -z "$(filter-out $@,$(MAKECMDGOALS))" ]; then \
		echo "❌ エラー: ファイルが指定されていません。例: make run app/test.py"; \
		exit 1; \
	fi
	@echo "🚀 $(filter-out $@,$(MAKECMDGOALS))を実行中..."
	@source venv/bin/activate && python $(filter-out $@,$(MAKECMDGOALS))

# コマンド引数をターゲットとして認識させないための特殊ルール
%:
	@:

# test.pyを実行（省略形）
test:
	@make run app/test.py

# 環境セットアップ
setup:
	@echo "🔧 仮想環境をセットアップ中..."
	@python3 -m venv venv
	@source venv/bin/activate && pip install -U pip
	@echo "📦 依存パッケージをインストール中..."
	@source venv/bin/activate && pip install openai numpy scikit-learn python-dotenv
	@echo "✅ セットアップ完了"

# 環境クリーン
clean:
	@echo "🧹 仮想環境を削除中..."
	@rm -rf venv
	@echo "✅ クリーン完了"

# ヘルプ表示
help:
	@echo "使用可能なコマンド:"
	@echo "  make run ファイル名       - 指定したPythonファイルを実行（例: make run app/test.py）"
	@echo "  make test                - app/test.pyを実行（省略形）"
	@echo "  make setup               - 仮想環境をセットアップして依存パッケージをインストール"
	@echo "  make clean               - 仮想環境を削除"
