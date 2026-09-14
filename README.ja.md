# ytdlpGUI

**English ([README.md](README.md)) · [中文](README.zh.md) · [日本語](README.ja.md) · [한국어](README.ko.md)**

yt-dlp のクロスプラットフォーム GUI フロントエンド（Web / Linux / Windows）。yt-dlp の**全コマンドラインオプション**をサポートし、UI とロジックを厳密に分離した設計で、将来の macOS / iOS / Android クライアントにも同じバックエンド API を再利用できます。

## 主な機能

- **2 モード UI**：既定のシンプルモード（タイトルバー＋URL 入力＋ダウンロードキュー、純粋な `yt-dlp <url>`）、「⚙ 詳細」で全設定を展開
- **全オプション**：yt-dlp の全オプション（隠しオプションの手動補完込み）を公式カテゴリ別に表示。日本語説明・使用例・ツールチップ付き、検索可能
- **排他制御**：51 组の三状態グループ（デフォルト/オン/オフ）＋30 組の自動クリア排他。メタデータをフロントエンドとバックエンドで共有し、サーバー側でも強制検証
- **ダウンロード管理**：複数 URL のキューン、リアルタイムの進捗・速度・ETA・ログ（SSE）、キャンセル、保存先パスの即時表示
- **情報照会**：フローティングウィンドウにタイトル/長さ/フォーマット表を表示。行をクリックで `-f` を選択。複数リンクは個別照会＋↑↓ ナビゲーション
- **ダウンロード履歴**：URL/タイトル/パス/時刻/成否を全記録、クリア可能、ログパス設定可能
- **ディレクトリ選択**：サーバー側フォルダブラウザ。LAN 共有・ネットワークマウント対応（Windows ドライブ/UNC）
- **4 言語 UI**：中文 / English / 日本語 / 한국어、完全ソフトコード化（`frontend/js/i18n/*.json`）
- **プリセット**：オプション組み合わせの保存/読込/削除、保存時に検証
- **セキュリティ**：オプションのホワイトリスト＋値検証で引数インジェクションを防止。既定は 127.0.0.1 のみリッスン

## アーキテクチャ

```
frontend/   静的 HTML/CSS/JS（ビルド不要、任意の WebView に埋め込み可能）
backend/    FastAPI サービス（純粋ロジック、単体 import 可能）
  api/          薄い HTTP ルーティング層
  services/     downloader / options / metadata / history / store
  data/         options_registry.json（yt_dlp.options から内省生成）
docs/       SDD ドキュメント＋2 ラウンドの QA レポート（123 件の UI ケース＋27 件の修正）
scripts/    generate_registry.py / run_checks.sh / regress_examples.py
```

オプションレジストリは `scripts/generate_registry.py` が yt-dlp ソース（`yt_dlp/options.py`）を内省して生成——フラグ/引数個数/繰り返し可否/排他関係はすべてデータ駆動です。yt-dlp 更新後はスクリプトを再実行するだけで追従し、`--check` モードでドリフトを検出できます。

## クイックスタート

```bash
# Linux / macOS
./run.sh                    # venv 作成・依存インストール・ブラウザ起動
./run.sh --lan              # LAN モード（0.0.0.0、スマホや他 PC からアクセス可）
```

```bat
:: Windows（ソースから実行）
run.bat
```

手動：`python -m uvicorn backend.app.main:app --port 8765` → http://127.0.0.1:8765 を開く
API ドキュメント（OpenAPI）：http://127.0.0.1:8765/docs

## Windows .exe のビルド

**方法 1（推奨）**：Python 3.10+ をインストール後、

```bat
build_windows.bat
```

単一ファイル `dist\ytdlpgui.exe` が生成——コンソールウィンドウなし、ダブルクリックで起動しブラウザ UI を自動で開きます。設定/プリセット/履歴は exe と同じ場所の `data\` フォルダに保存され、exe をコピーするだけで配布できます。

**方法 2（手動）**：

```bat
python -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt pyinstaller
.venv\Scripts\pyinstaller --clean ytdlpgui.spec
```

注：`ytdlpgui.spec` は `console=False`（黒い窓なし）。デバッグ時は `True` にして再ビルドするとログが見えます。exe には現行のレジストリ/フロントエンド素材が同梱されるため、yt-dlp の更新時は再ビルドまたはソース実行が必要です。

## 開発品質スイート

コード変更や yt-dlp 更新後は `scripts/run_checks.sh` を実行（3 ステップすべて合格が条件）：

1. レジストリ・ドリフト検出——yt-dlp の実際のオプションと registry の不一致を警告；
2. 排他メタデータとコマンド構築の構造アサーション（両側非空/対称/multi/nargs/排他拒否）；
3. 全日本語例の回帰テスト（build_args ＋ yt-dlp --simulate で実証、96 件）。

リリース前 3 分のスモークチェック：ページが正常起動 →「すべてのオプション」で三状態グループ ≥40 → 英語 UI に中文の残りがないこと。

## 既知のトレードオフ

- URL 入力は http(s)・`ytsearch` プレフィックス・コロンなしの裸ドメインを受け付け、その他のスキーム/検索プレフィックスは拒否（攻撃面の考慮）
- `--alias` / `--replace-in-metadata` / `--print-to-file` は複数引数オプションで、1 つの入力ボックスにスペース区切りで入力（各セグメントの制限は UI のヒント参照）
- 純粋な CLI 照会系オプション（`--help`/`--dump-json` など）は UI で非表示だが、旧プリセット互換のためホワイトリストでは受理

## 将来の拡張（macOS / iOS / Android）

バックエンドの `services/` 層は Web フレームワーク型に依存せずそのまま移植可能。フロントエンドはビルド不要の静的素材で、WKWebView / WebView / Android WebView で直接読み込み可能、Tauri / Capacitor でのラップもできます。

## ドキュメント

- 設計とタスク：`docs/design.md`、`docs/tasks.md`
- QA：`docs/qa-report-1.md`（データ/ロジック層）、`docs/qa-ui-plan.md` + `docs/qa-ui-report.md`（UI 層 123 ケース）

## 旧版

旧版（tkinter、Windows 専用・最小機能）は `ytdlpGUI@7c93372` を参照。
