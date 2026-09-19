---
name: 競馬ルーティン保守
description: 競馬仮想馬券シミュレーションのRemoteTriggerルーティン設定変更・トラブルシューティング時の手順と既知の落とし穴。ルーティンの設定確認・更新、またはエラー調査を行う際に読むこと。
---

# 競馬ルーティン保守(2026-09-01時点)

## RemoteTriggerルーティン
- ID: `trig_0158hKaa54vBiqB6Wnz371ny`、名前「競馬仮想馬券シミュレーション」
- cron: `7 0,3,6,9,12 * * 0,6`（JST土日9,12,15,18,21時・3時間おき。2026-09-02〜、旧・毎正時07分の1時間おき）
- 環境: keiba-env2（Network accessがCustomでrace.netkeiba.com / nar.netkeiba.com / db.netkeiba.com / www.jra.go.jp / www.oddspark.comへ直接アクセス可。2026-09-14に`sports.yahoo.co.jp`の追加を運用者に依頼済み・許可され次第このリストに追加すること）
- ルーティンの`update`は`job_config.ccr`を毎回フルセット（environment_id・session_context・events全文）で送ること。部分更新すると`prompt`等が消える。

## 既知の落とし穴
- WebFetchが数十時間規模で全ドメイン`EGRESS_BLOCKED`になることがある。1〜2回は静かに見送り、3回以上連続なら記録・運用者へ報告する。
- `tools/netkeiba_fetch.py`の`body_weight_kg`欄が単勝オッズと酷似した値を返す列ずれ不具合が時々発生する。発生した馬はその項目の評価から除外する。
- `~/.claude/skills/`（ユーザースコープ）のスキルはこのクラウドルーティンからは見えない。ルーティンに使わせたいスキルは必ずこのリポジトリの`.claude/skills/`にコミットすること。
- **`tools/netkeiba_fetch.py`・`netkeiba_result.py`は元々`nar.netkeiba.com`固定でNAR専用だった（2026-09-05修正済み、race_idの場コード01-10ならJRA用`race.netkeiba.com`を自動選択）。同じくJRAページでは性齢(`td.Barei`)・斤量(単一classの`td.Txt_C`)のHTML構造がNARと異なるため、両対応のフォールバックを入れてある。ツールを新規作成・改修する際は必ずJRA・NAR両方のrace_idで動作確認すること。**
- **JRAの単勝オッズ取得不具合(2026-09-05発生・09-06に部分修正)**: `race.netkeiba.com`の出馬表ページ(`shutuba.html`)は単勝オッズ欄が常に静的プレースホルダー(`---.-`)のままで、実際の値はブラウザ上でJS Ajax API(`/api/api_get_jra_odds.html?race_id=<id>&type=1&housiki=c99`)を叩いて後から埋め込む仕組みだった。これに気づかず`shutuba.html`のHTMLを直接パースしていた`tools/netkeiba_fetch.py`は、JRAレースで常にオッズnullを返していた。**2026-09-06、`fetch_jra_win_odds()`を追加し、このAPIをRefererヘッダ(`https://race.netkeiba.com/odds/index.html?race_id=<id>&type=b1`)付きで直接叩いて実オッズ・人気順位を取得し上書きするよう修正済み(`fetch_shutuba`内でJRAレースのみ自動適用)。確定済み(レース終了後)の複数レースで実際に正しいオッズが返ることを確認した。**
- **「G3以上の重賞」の解釈ミスに注意(2026-09-13発生・訂正済み)**: 2026-09-13朝1回目実行で、G2レース(セントライト記念・ローズS)を「G3未満だから重賞必須購入ルールの対象外」と誤って判定する事例が発生した。重賞の格付け序列はG1＞G2＞G3（G1が最上位）であり、CLAUDE.md・競馬運用記録.mdの「G3以上（G3・G2・G1）の重賞レース」という定義通り、G1・G2・G3はすべて必須購入ルールの対象。「G3以上」を数値的に「G3、G4…」のように読み違えないこと。
- **JRA発売中ライブオッズは匿名アクセスでは構造的に取得不可(2026-09-12確定)**: 2026-09-06時点で持ち越されていた疑問点（発走前ライブオッズが取得できないのはReferer欠落のせいか、プレミアム会員限定の構造的制約か）を、次のJRA開催日(2026-09-12)の朝1回目サイクルで検証し決着した。窓内の発売中レース(中山1R 202606040301、発走まで約37分)で`tools/netkeiba_fetch.py`を実行してもwin_odds/ninki_rankは全馬null、オッズAPI(`/api/api_get_jra_odds.html`)を単勝〜馬単など券種(type=1,2,3,5,6)を変えて直接叩いても全て`{"status":"middle","data":"","update_count":"0","reason":"result odds empty"}`。決め手は`race.netkeiba.com/odds/index.html?race_id=<id>&type=b1`のHTMLソース内にある`var _isPremium = '0';`で、この値がそのままAPIの`isPremium`パラメータに渡される作りだった。**つまりJRAの発売中ライブ単勝オッズはnetkeibaの有料プレミアム会員(`isPremium=1`)向け専用機能であり、匿名/無料アクセス(`isPremium=0`)では原理的に取得不可能**（確定後レースのオッズだけが無料公開される仕様）。代替も不可：`www.jra.go.jp`は公開オッズページへの導線が見当たらず、`www.oddspark.com`は地方競馬(NAR)専用でJRAレースの情報を含まない。よって現状の許可済みアクセス手段だけでは、発売中JRAレースの単勝オッズを検算する方法が存在しない。運用者判断が必要（netkeibaプレミアム契約／別ドメインの許可リスト追加／JRA限定運用の継続可否の再検討）。この制約はセッションのプレミアム状態に依存し時間経過や券種変更では変わらないため、レースごとに再検証する必要はない（開催日単位で「今日も変化なし」を確認する程度でよい）。
- **代替データ源`tools/yahoo_keiba_odds.py`の発売中ライブオッズ取得を確認済み(2026-09-19検証成功)**: 運用者の指示で調査したYahoo!スポーツ競馬(`sports.yahoo.co.jp/keiba/race/odds/tfw/<yahoo_race_id>`)は、ログイン不要の一般公開ページとして単勝・複勝オッズを静的HTMLに直接埋め込んでいる(netkeibaのようなJS/Ajax後付けではない)。`yahoo_race_id`はnetkeiba形式race_id(12桁)の先頭2桁("20")を除いた10桁。2026-09-14時点では確定済み(レース終了後)レースでの検証のみだったが、**2026-09-19(土)09:14 JST、発売中(発走37分前)の阪神1R(202609040501)に対し`tools/yahoo_keiba_odds.py`を実行し、出走全8頭の単勝・複勝オッズが正しく取得できることを確認した(同時刻の`tools/netkeiba_fetch.py`はいつも通り全馬null)**。ネットワークの許可リストにも`sports.yahoo.co.jp`が追加済み(HTTP 200)であることを確認済み。これにより2026-09-01のJRA限定運用開始以来続いていた新規購入0件の状態から復帰した(阪神3Rで初購入、詳細は競馬運用記録.md参照)。
  - **組み合わせ券種オッズページも静的HTMLで取得可能**: ワイド`/keiba/race/odds/wide/<yahoo_race_id>`・馬連`/keiba/race/odds/ur/<yahoo_race_id>`も同様にログイン不要・静的HTMLで、オッズの下限-上限レンジ(例"3.5-4.1")が全馬番組み合わせ分掲載されている。`tools/yahoo_keiba_odds.py`はまだ単勝・複勝(`tfw`)のみ対応で、ワイド・馬連は2026-09-19時点でその場でrequests+BeautifulSoupの簡易スクリプトを都度書いて取得した(専用ツール化はまだ未実施、必要なら`tools/yahoo_keiba_odds.py`に`--type wide`等のオプションとして追加を検討)。馬単`/ut/`・3連単`/st/`・3連複`/sf/`のURLスラッグも存在を確認したが2026-09-19時点で内容は未検証。
  - トリガミ回避チェックは、単勝オッズからの概算ではなく、この実際のワイド/馬連オッズ(下限値)を使って検算する方が精度が高い。
- **前回セッションのcommitがpushされずHEAD detachedのまま残っていた不具合(2026-09-19 12時台に発見・復旧)**: 2026-09-19 09:08 JSTサイクルの`git commit`は実行されていたが、実行環境がHEAD detached状態(`refs/heads/main`ではなくコミットそのものを指す状態)だったため、ローカルの`main`ブランチが更新されず、結果として`git push`（実行された形跡はあるが反映されていなかった）後もorigin/mainに反映されない「宙に浮いた」コミットになっていた。次サイクル(12:11 JST)開始時に`git status`が`HEAD detached from refs/heads/main`と表示され発覚。復旧手順：`git merge-base --is-ancestor <origin/main> <HEAD>`でfast-forward可能なことを確認した上で`git branch -f main HEAD && git checkout main`でローカルmainを追いつかせてから通常通りcommit・push。**毎サイクルの手順7(git commit/push)の前に`git status`を確認し、"HEAD detached"の表示が出た場合は上記の復旧手順を踏んでからcommitすること。**
