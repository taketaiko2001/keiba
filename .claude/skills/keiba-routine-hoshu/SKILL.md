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
- **JRAの発走前ライブ単勝オッズは、tools/*.py・WebFetchのどちらで`race.netkeiba.com`の出走表ページを取得してもプレースホルダ(`---.-`)しか得られない（2026-09-05確認）。JRAのオッズはページ内のJS Ajax API(`/api/api_get_jra_odds.html`)経由で描画されており、このAPIを直接叩いても匿名アクセスでは`{"status":"middle","reason":"result odds empty"}`が返るだけで実オッズは取得不可（発走40分前〜16分前の複数タイミング・複数レースで確認、Cookie/Referer付与でも変化なし）。確定済みの過去レースでは同APIから確定オッズが正常に返るため、API自体は生きているが「発走前のライブオッズ」だけがおそらくnetkeibaプレミアム会員限定になっている構造的制約と考えられる。NAR(`nar.netkeiba.com`)は出走表HTMLに直接オッズが埋め込まれているためこの問題はない。この制約が解消されていない限り、JRAレースは単勝オッズによる妙味判定・トリガミ回避チェックができず、安全対策を通過できないため購入見送りとなる。解消策（netkeibaプレミアム契約／別の無料オッズ公開ドメインの許可リスト追加など）は運用者判断が必要。**
