"""
JRAレースの単勝・複勝オッズを、Yahoo!スポーツ競馬(sports.yahoo.co.jp)の
オッズページから取得するツール。

背景(2026-09-12確認): netkeiba(race.netkeiba.com)のJRA発売中ライブ単勝
オッズは、ページ内JSが`_isPremium`フラグを見てAjax APIへの応答を制御して
おり、匿名/無料アクセスでは常に空データしか返らない(プレミアム会員限定
機能)。Yahoo!スポーツ競馬のオッズページは静的HTMLに単勝・複勝オッズが
直接埋め込まれており、ログイン不要で誰でも閲覧できる一般公開ページのため、
この制約を受けない代替データ源として追加した。

race_id は本リポジトリの他ツールと同じnetkeiba形式(12桁、例
202609040411)で受け取り、内部でYahoo形式(先頭の世紀"20"を除いた10桁、
例2609040411)に変換する。

使い方:
    python3 tools/yahoo_keiba_odds.py <netkeiba形式race_id>
    例: python3 tools/yahoo_keiba_odds.py 202609040411

注意: 2026-09-14時点でこのツールが実際に「発売中(発走前)」のライブオッズ
まで取得できるかは未検証(確認できたのは確定済みレースのみ)。次回JRA開催日
の巡回サイクルで最優先の検証が必要(詳細は.claude/skills/keiba-routine-hoshu/SKILL.md参照)。
また、クラウドルーティンの実行環境(keiba-env2)のNetwork accessに
sports.yahoo.co.jpが許可されていないと接続できない(要・運用者による許可
リストへの追加)。
"""
import sys
import re
import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
}


def _to_yahoo_race_id(netkeiba_race_id: str) -> str:
    # netkeibaのrace_idは[世紀2桁+西暦下2桁][場コード2桁][開催回2桁][日2桁][R番号2桁]の12桁。
    # Yahooはそのうち先頭の世紀2桁("20")を除いた10桁を使う。
    if len(netkeiba_race_id) == 12 and netkeiba_race_id.startswith("20"):
        return netkeiba_race_id[2:]
    return netkeiba_race_id


def fetch_odds(netkeiba_race_id: str) -> dict:
    yahoo_id = _to_yahoo_race_id(netkeiba_race_id)
    url = f"https://sports.yahoo.co.jp/keiba/race/odds/tfw/{yahoo_id}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    title_el = soup.select_one("title")
    race_name = None
    if title_el:
        m = re.search(r"競馬 - (.+?) オッズ", title_el.get_text(strip=True))
        race_name = m.group(1) if m else title_el.get_text(strip=True)

    post_time_el = soup.select_one(".hr-predictRaceInfo__text")
    post_time = post_time_el.get_text(strip=True) if post_time_el else None

    horses = []
    table = soup.select_one("#raceodds_table") or soup.select_one("table.hr-tableValue tbody")
    rows = table.select("tr.hr-tableValue__row") if table else []
    for row in rows:
        cells = row.select("td.hr-tableValue__data")
        if len(cells) < 5:
            continue
        umaban = cells[1].get_text(strip=True)
        horse_a = cells[2].select_one("a")
        horse_name = horse_a.get_text(strip=True) if horse_a else cells[2].get_text(strip=True)
        horse_id = None
        if horse_a and horse_a.get("href"):
            m = re.search(r"/horse/(\w+)", horse_a["href"])
            if m:
                horse_id = m.group(1)

        win_raw = cells[3].get_text(strip=True)
        win_odds = None
        try:
            win_odds = float(win_raw)
        except ValueError:
            win_odds = None  # 取消・発売前など非数値

        fukusho_raw = cells[4].get_text(" ", strip=True)
        fukusho_low = None
        fukusho_high = None
        fm = re.match(r"([\d.]+)\s*-\s*([\d.]+)", fukusho_raw)
        if fm:
            try:
                fukusho_low = float(fm.group(1))
                fukusho_high = float(fm.group(2))
            except ValueError:
                pass

        horses.append({
            "umaban": umaban,
            "horse_id": horse_id,
            "horse_name": horse_name,
            "win_odds": win_odds,
            "fukusho_odds_low": fukusho_low,
            "fukusho_odds_high": fukusho_high,
        })

    # 単勝オッズ昇順(人気順)に並べ替えて人気順位を付与。Noneは末尾。
    horses_sorted = sorted(horses, key=lambda h: (h["win_odds"] is None, h["win_odds"]))
    for i, h in enumerate(horses_sorted, start=1):
        h["ninki_rank"] = i if h["win_odds"] is not None else None

    return {
        "netkeiba_race_id": netkeiba_race_id,
        "yahoo_race_id": yahoo_id,
        "race_name": race_name,
        "post_time": post_time,
        "num_horses": len(horses_sorted),
        "horses_by_popularity": horses_sorted,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 yahoo_keiba_odds.py <netkeiba形式race_id>", file=sys.stderr)
        sys.exit(1)
    result = fetch_odds(sys.argv[1])
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
