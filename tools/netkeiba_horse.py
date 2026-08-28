"""
netkeiba(db.netkeiba.com)の馬個別ページから、過去の競走成績を
生HTMLから直接パースして取得するツール。近走のフォーム分析に使う。

使い方:
    python3 tools/netkeiba_horse.py <horse_id> [output.json]
    例: python3 tools/netkeiba_horse.py 2021104277

horse_id は出馬表(netkeiba_fetch.py)の各馬データの "horse_id" フィールドで取得できる。
"""
import sys
import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
}

# 完全一致するヘッダーテキスト -> 出力キー
WANTED_HEADERS = {
    "日付": "date",
    "開催": "track",
    "天気": "weather",
    "R": "race_num",
    "レース名": "race_name",
    "頭数": "num_horses",
    "枠番": "waku",
    "馬番": "umaban",
    "オッズ": "odds",
    "人気": "ninki",
    "着順": "rank",
    "騎手": "jockey",
    "斤量": "weight_carried",
    "距離": "distance",
    "馬場": "track_condition",
    "タイム": "time",
    "着差": "chakusa",
    "通過": "passing",
    "ペース": "pace",
    "上り": "agari_3f",
    "馬体重": "body_weight",
    "賞金": "prize",
}


def fetch_horse_results(horse_id: str) -> dict:
    url = f"https://db.netkeiba.com/horse/result/{horse_id}/"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    horse_name = None
    title_el = soup.select_one("h1") or soup.select_one(".horse_title h1")
    if title_el:
        horse_name = title_el.get_text(strip=True)

    table = soup.select_one("table.db_h_race_results")
    races = []
    col_index = {}
    if table:
        ths = table.select("thead th")
        for i, th in enumerate(ths):
            text = th.get_text(strip=True)
            if text in WANTED_HEADERS and WANTED_HEADERS[text] not in col_index.values():
                col_index[i] = WANTED_HEADERS[text]

        for row in table.select("tbody tr"):
            tds = row.find_all("td", recursive=False)
            if not tds:
                continue
            record = {}
            race_id = None
            for i, td in enumerate(tds):
                key = col_index.get(i)
                if not key:
                    continue
                a = td.select_one("a")
                text = td.get_text(strip=True)
                record[key] = text if text else None
                if key == "race_name" and a and a.get("href"):
                    parts = [p for p in a["href"].split("/") if p]
                    if parts and parts[-1].isdigit():
                        race_id = parts[-1]
            if record:
                record["race_id"] = race_id
                races.append(record)

    return {
        "horse_id": horse_id,
        "horse_name": horse_name,
        "num_past_races": len(races),
        "races_most_recent_first": races,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 netkeiba_horse.py <horse_id> [output.json]", file=sys.stderr)
        sys.exit(1)
    result = fetch_horse_results(sys.argv[1])
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
