# ビジ法2級 精選フラッシュカード

ビジネス実務法務検定2級の精選問題集(全16章・172問)を使った、Mac/iPhone向けフラッシュカードWebアプリ。

## 使い方

- Mac上でSafari/Chromeから `index.html` を直接開いて動作確認できる
- GitHub Pages で公開: https://yhb05633.github.io/Bizlaw2-seisen2026/
- iPhoneでは、上記URLをSafariで開き、共有メニューから「ホーム画面に追加」するとアプリのように使える(Service Workerによりオフライン動作)
- 学習の進捗(「できた」「苦手」マーク)は端末のlocalStorageに保存される(端末をまたいでは同期されない)

## データの更新

問題データは `/Volumes/Macmini M2PRO/専門スキル/法務書籍/Legalstudy2026/ビジ法検定_/ビジ法２精選/` の `01.txt`〜`16.txt` を元にしている。元データを修正した場合は以下を再実行して `cards.js` を作り直す:

```bash
python3 scripts/parse_cards.py
```
