---
name: 競馬ルーティン保守
description: 競馬仮想馬券シミュレーションのRemoteTriggerルーティン設定変更・トラブルシューティング時の手順と既知の落とし穴。ルーティンの設定確認・更新、またはエラー調査を行う際に読むこと。
---

# 競馬ルーティン保守(2026-09-01時点)

## RemoteTriggerルーティン
- ID: `trig_0158hKaa54vBiqB6Wnz371ny`、名前「競馬仮想馬券シミュレーション」
- cron: `7 0,3,6,9,12 * * 0,6`（JST土日9,12,15,18,21時・3時間おき。2026-09-02〜、旧・毎正時07分の1時間おき）
- 環境: keiba-env2（Network accessがCustomでrace.netkeiba.com / nar.netkeiba.com / db.netkeiba.com / www.jra.go.jp / www.oddspark.comへ直接アクセス可）
- ルーティンの`update`は`job_config.ccr`を毎回フルセット（environment_id・session_context・events全文）で送ること。部分更新すると`prompt`等が消える。

## 既知の落とし穴
- WebFetchが数十時間規模で全ドメイン`EGRESS_BLOCKED`になることがある。1〜2回は静かに見送り、3回以上連続なら記録・運用者へ報告する。
- `tools/netkeiba_fetch.py`の`body_weight_kg`欄が単勝オッズと酷似した値を返す列ずれ不具合が時々発生する。発生した馬はその項目の評価から除外する。
- `~/.claude/skills/`（ユーザースコープ）のスキルはこのクラウドルーティンからは見えない。ルーティンに使わせたいスキルは必ずこのリポジトリの`.claude/skills/`にコミットすること。
- **`tools/netkeiba_fetch.py`・`netkeiba_result.py`は元々`nar.netkeiba.com`固定でNAR専用だった（2026-09-05修正済み、race_idの場コード01-10ならJRA用`race.netkeiba.com`を自動選択）。同じくJRAページでは性齢(`td.Barei`)・斤量(単一classの`td.Txt_C`)のHTML構造がNARと異なるため、両対応のフォールバックを入れてある。ツールを新規作成・改修する際は必ずJRA・NAR両方のrace_idで動作確認すること。**
- **JRAの単勝オッズ取得不具合(2026-09-05発生・09-06に部分修正)**: `race.netkeiba.com`の出馬表ページ(`shutuba.html`)は単勝オッズ欄が常に静的プレースホルダー(`---.-`)のままで、実際の値はブラウザ上でJS Ajax API(`/api/api_get_jra_odds.html?race_id=<id>&type=1&housiki=c99`)を叩いて後から埋め込む仕組みだった。これに気づかず`shutuba.html`のHTMLを直接パースしていた`tools/netkeiba_fetch.py`は、JRAレースで常にオッズnullを返していた。**2026-09-06、`fetch_jra_win_odds()`を追加し、このAPIをRefererヘッダ(`https://race.netkeiba.com/odds/index.html?race_id=<id>&type=b1`)付きで直接叩いて実オッズ・人気順位を取得し上書きするよう修正済み(`fetch_shutuba`内でJRAレースのみ自動適用)。確定済み(レース終了後)の複数レースで実際に正しいオッズが返ることを確認した。**
- **「G3以上の重賞」の解釈ミスに注意(2026-09-13発生・訂正済み)**: 2026-09-13朝1回目実行で、G2レース(セントライト記念・ローズS)を「G3未満だから重賞必須購入ルールの対象外」と誤って判定する事例が発生した。重賞の格付け序列はG1＞G2＞G3（G1が最上位）であり、CLAUDE.md・競馬運用記録.mdの「G3以上（G3・G2・G1）の重賞レース」という定義通り、G1・G2・G3はすべて必須購入ルールの対象。「G3以上」を数値的に「G3、G4…」のように読み違えないこと。
- **JRA発売中ライブオッズは匿名アクセスでは構造的に取得不可(2026-09-12確定)**: 2026-09-06時点で持ち越されていた疑問点（発走前ライブオッズが取得できないのはReferer欠落のせいか、プレミアム会員限定の構造的制約か）を、次のJRA開催日(2026-09-12)の朝1回目サイクルで検証し決着した。窓内の発売中レース(中山1R 202606040301、発走まで約37分)で`tools/netkeiba_fetch.py`を実行してもwin_odds/ninki_rankは全馬null、オッズAPI(`/api/api_get_jra_odds.html`)を単勝〜馬単など券種(type=1,2,3,5,6)を変えて直接叩いても全て`{"status":"middle","data":"","update_count":"0","reason":"result odds empty"}`。決め手は`race.netkeiba.com/odds/index.html?race_id=<id>&type=b1`のHTMLソース内にある`var _isPremium = '0';`で、この値がそのままAPIの`isPremium`パラメータに渡される作りだった。**つまりJRAの発売中ライブ単勝オッズはnetkeibaの有料プレミアム会員(`isPremium=1`)向け専用機能であり、匿名/無料アクセス(`isPremium=0`)では原理的に取得不可能**（確定後レースのオッズだけが無料公開される仕様）。代替も不可：`www.jra.go.jp`は公開オッズページへの導線が見当たらず、`www.oddspark.com`は地方競馬(NAR)専用でJRAレースの情報を含まない。よって現状の許可済みアクセス手段だけでは、発売中JRAレースの単勝オッズを検算する方法が存在しない。運用者判断が必要（netkeibaプレミアム契約／別ドメインの許可リスト追加／JRA限定運用の継続可否の再検討）。この制約はセッションのプレミアム状態に依存し時間経過や券種変更では変わらないため、レースごとに再検証する必要はない（開催日単位で「今日も変化なし」を確認する程度でよい）。
