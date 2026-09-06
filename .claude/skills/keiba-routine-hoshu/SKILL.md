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
- **未解決の疑問点(要・次回JRA開催日での検証)**: 上記の修正が「発走前でまだ投票受付中(発売中)のライブオッズ」にも通用するかは2026-09-06時点で未検証。検証を試みた時点(16時台)で本日のJRA全レースが終了済みだったため、テストは全て確定後のレースに対してのみ行えた。実際、Refererの有無に関わらず確定後レースでは常に実オッズが返ったため、過去に運用者が報告した「発走前は`reason: result odds empty`」という現象がRefererの欠落によるものか、それとも「発売中のライブオッズは匿名アクセスでは提供されない(プレミアム会員限定等)」という構造的制約によるものかは、今回の調査だけでは切り分けられていない。**次回のJRA開催日(2026-09-12/13)の巡回サイクルで、発走前(発売中)のレースに対して`tools/netkeiba_fetch.py`を実行し、実際にオッズが返るかを最優先で確認し、記録.mdに結果を明記すること。** もし発走前も正しく取得できれば本不具合は解消。もし依然として発走前だけ空のままなら、「発売中のライブオッズは匿名アクセスでは構造的に取得不可」という結論が確定するため、netkeibaプレミアム契約／別の無料オッズ公開ドメインの許可リスト追加／JRA公式サイト(www.jra.go.jp)のオッズページの調査など、運用者判断が必要な解決策の検討に進むこと。
