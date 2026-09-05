# CLAUDE.md

## プロジェクトの目的

ビジネス実務法務検定2級の精選問題集(全16章・172問)を使った、iPhone/Mac向けフラッシュカードWebアプリ。

## 構成

- `index.html` — 単一ファイルの静的Webアプリ(HTML/CSS/JS、外部依存なし)。`cards.js` を読み込んで表示する。
- `cards.js` — `scripts/parse_cards.py` が生成する問題データ(`CHAPTERS`, `CARDS`)。直接手編集しない。
- `scripts/parse_cards.py` — 元データ(`.txt`)から `cards.js` を生成するスクリプト。章番号・章タイトル・問題数はスクリプト内にハードコードされた表が正であり、元データの見出しには依存しない。
- ビルド不要。`index.html` をブラウザで開くだけで動作する。

## データを更新する場合

元の `.txt` を修正した後、`python3 scripts/parse_cards.py` を再実行して `cards.js` を作り直す。章ごとの問題数が想定と食い違う場合はエラーで停止するので、その章のファイルを確認する。

## 使い方

- Macでは `index.html` を直接開いて動作確認
- GitHub Pages で公開: https://yhb05633.github.io/Bizlaw2-seisen2026/
- iPhoneでは、上記URLをSafariで開き「ホーム画面に追加」でアプリのように使える
- 学習進捗はlocalStorageのみ、端末間の同期はしない
