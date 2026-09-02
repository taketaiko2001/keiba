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
