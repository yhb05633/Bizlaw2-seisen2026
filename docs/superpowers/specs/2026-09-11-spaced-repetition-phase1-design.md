# 間隔反復・検索練習 フェーズ1 設計書

## 背景・目的

現状のフラッシュカードアプリは章単位の順番出題のみで、復習タイミングの最適化や自己評価に基づく習熟管理がない。認知科学の知見(間隔反復・検索練習)に基づき学習効率を高める機能を段階的に追加する。本設計はそのうちフェーズ1(最優先の2機能)を対象とする。

- 機能1: Leitner System方式の間隔反復(box_level 1〜5、次回復習日の算出、「今日の復習キュー」)
- 機能2: 検索練習の強制と3段階自己評価(わからなかった/かろうじて正解/簡単だった)による box_level 更新

インターリーブ出題・自信度申告・学習進捗の可視化(元の優先度3〜5)は本設計の対象外。フェーズ1の動作確認後に別途設計する。

## 確認済みの前提(既存実装)

- 単一ファイル静的アプリ。`index.html`(HTML/CSS/JS)、`cards.js`(生成データ、直接編集禁止)、ビルドなし、フレームワークなし。
- 保存はlocalStorageのみ。既存キー: `bizlaw2seisen:stars:<id>`、`bizlaw2seisen:master:<id>`、`bizlaw2seisen:memo:<id>`、`bizlaw2seisen:masterSkipEnabled`。
- カードは全172問に`answerIndex`があり客観的正誤判定が可能。「分野」に相当する情報は`chapter`/`chapterTitle`として既存(16分野、3〜34問/分野)。
- 出題は章フィルタ後の配列順のみ。ランダム化・インターリーブなし。
- 選択肢を選ばないと解答ボタンが押せない実装が既にあり、検索練習(答えを見る前に自分の回答を確定させる)の要件を満たしている。

## 決定事項(ユーザー確認済み)

1. 分野の粒度は既存16章(`chapter`/`chapterTitle`)をそのまま使う。新規分類タグは作らない。
2. 既存の★実施回数・マスタートグルはそのまま維持し、新しいSRSシステムは完全に並行追加する(置き換えない)。
3. 自己評価3段階は、選択式の客観正誤(正解/不正解バッジ)と独立して、常に自由に選べる(矛盾防止の制約は入れない)。
4. 「今日の復習」は章一覧画面に新規ボタンとして追加し、全章横断でキューに入る。

## データモデル

`cards.js`は一切変更しない(生成物であり共有データのため)。新しい学習状態は既存パターンに倣い、カードIDごとに1つのJSONオブジェクトとしてlocalStorageに保存する。

```
key: bizlaw2seisen:srs:<id>
value (JSON):
{
  "box": 1,              // 1〜5
  "lastReviewedAt": null,     // ISO8601文字列 or null(未評価)
  "nextReviewAt": "2026-09-11", // YYYY-MM-DD文字列
  "streak": 0,            // 連続「わからなかった」以外の評価回数
  "totalReviews": 0,
  "totalCorrect": 0        // 自己評価が「わからなかった」以外だった回数
}
```

- `getSrs(id)`: 未保存の場合は `{box:1, lastReviewedAt:null, nextReviewAt: todayStr(), streak:0, totalReviews:0, totalCorrect:0}` を返す。これにより既存カード・新規カードとも自動的に「即復習対象」として扱われ、後方互換のためのマイグレーション処理は不要。
- `saveSrs(id, srs)`: JSON文字列化して保存。
- 「分野」は新フィールドを追加せず、既存の `card.chapter` / `card.chapterTitle` をそのまま利用する。

## 間隔反復ロジック

```
BOX_INTERVAL_DAYS = {1:1, 2:3, 3:7, 4:14, 5:30}
```

- `todayStr()`: ローカルタイムゾーンの `YYYY-MM-DD` を返す。
- `addDays(dateStr, n)`: 日付文字列にn日加算した `YYYY-MM-DD` を返す。
- `isDueToday(id)`: `getSrs(id).nextReviewAt <= todayStr()`
- `getDueCards(cardsArray)`: `cardsArray.filter(c => isDueToday(c.id))`

## 検索練習・自己評価ロジック

自己評価は3値: `'unknown'`(わからなかった) / `'barely'`(かろうじて正解) / `'easy'`(簡単だった)。

```
applySelfAssessment(id, grade):
  srs = getSrs(id)
  if grade === 'unknown': newBox = 1
  else if grade === 'barely': newBox = srs.box
  else if grade === 'easy': newBox = min(5, srs.box + 1)

  srs.box = newBox
  srs.lastReviewedAt = now (ISO文字列)
  srs.nextReviewAt = addDays(todayStr(), BOX_INTERVAL_DAYS[newBox])
  srs.totalReviews += 1
  srs.streak = grade === 'unknown' ? 0 : srs.streak + 1
  if grade !== 'unknown': srs.totalCorrect += 1
  saveSrs(id, srs)
```

選択式の客観正誤(`answerIndex`との一致)は既存の `answer-result` バッジとして今まで通り表示するのみで、box更新には一切影響しない(決定事項3)。

## UI変更

### 章一覧画面

- 既存の `.chapter-toolbar` に「今日の復習」ボタン(`#btn-review-queue`)を追加。ラベルは対象件数を含める(例: `今日の復習（12）`)。件数0件でもボタン自体は常時表示。
- クリック時: `CARDS`全体から `getDueCards()` でフィルタ。0件なら既存の「すべての問題がマスター済みです」と同様のアラートパターンで「今日復習すべきカードはありません」を表示して処理を中断。1件以上なら既存の `startChapter` と同じ要領で `currentCards`/`currentIndex`/`sessionResults` をセットし `showCardScreen()` → `renderCard()`(専用の `startReviewQueue()` 関数を新設し、`startChapter` とロジックを共有できる部分は共通化する)。
- 章ごとのマスタースキップ設定(`isMasterSkipEnabled`)は「今日の復習」には適用しない(due=未マスター相当の意味を持つため)。

### カード画面(裏面)

- 既存の `#answer-result`(正誤バッジ)の直後、`#btn-master` の前に自己評価3ボタン行(`.self-assessment`)を追加: 「わからなかった」「かろうじて正解」「簡単だった」。
- ボタン押下で `applySelfAssessment(card.id, grade)` を呼び、直後に次回復習日を短く表示(例: `次回復習: 9/12`)。表示領域は自己評価ボタン行のすぐ下に小さく追加。
- 同一カード表示中に複数回タップした場合は上書き(最後の選択が有効)で問題ない。他の裏面要素(マスターボタン、メモ、★行)の挙動・スタイルは変更しない。

## エラー処理・エッジケース

- localStorageが使えない(プライベートブラウズ等)場合は既存の★/マスター/メモと同じく `try/catch` で握りつぶし、読み込みはデフォルト値、書き込みは無視する(既存コードの流儀に合わせる)。
- 日付境界(日をまたいだままアプリを開きっぱなしにするケース)は考慮しない。`todayStr()` は評価アクション実行時点で都度計算するため、操作のたびに正しい「今日」を参照する。
- 「今日の復習」セッション中の章表示・スワイプ・スライダー・成績確認・メモ機能は既存の `currentCards` ベースの仕組みをそのまま使うため追加対応不要。

## 動作確認方法(手動)

1. Commit 1後: 章一覧で「今日の復習（172）」のように全件が表示されることを確認。押下してカード画面に遷移し、既存の章セッションと同様に閲覧・スワイプ・戻るができることを確認。
2. Commit 2後: カード裏面で3段階評価ボタンをタップし、「次回復習: ...」の表示が更新されることを確認。DevToolsで `localStorage` の `bizlaw2seisen:srs:<id>` の値(box/nextReviewAt等)が期待通り変化することを確認。「わからなかった」を選んだカードが翌日以降まで復習対象から外れないこと(=今日また出る)、「簡単だった」を選んだカードが件数から即座に減ることを、章一覧に戻って件数表示で確認。

## 対象外(フェーズ2以降・別途設計)

- インターリーブ出題(分野シャッフル)
- 自信度申告と誤答の重み付け
- 学習進捗の可視化(分野別正答率、ストリーク、推定記憶保持率)
