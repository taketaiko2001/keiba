"""
netkeiba(地方競馬 nar.netkeiba.com)の出馬表ページから、
出走馬・単勝オッズなどを生HTMLから直接パースして取得するツール。

WebFetchの要約AIは表の列を読み違えることがある(実測で「人気順位」を
「単勝オッズ」と誤って回答するケースを確認済み)ため、生HTMLをBeautifulSoup
で確実にパースする。

使い方:
    python3 tools/netkeiba_fetch.py <race_id>
    例: python3 tools/netkeiba_fetch.py 202643082811

race_id の構造: [年4桁][場コード2桁][開催回?2桁][日2桁][レース番号2桁]
主な場コード: 43=船橋 47=笠松 50=園田 (他場は要調査)
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


def fetch_shutuba(race_id: str) -> dict:
    url = f"https://nar.netkeiba.com/race/shutuba.html?race_id={race_id}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    race_name_el = soup.select_one(".RaceName")
    race_name = race_name_el.get_text(strip=True) if race_name_el else None

    race_data_el = soup.select_one(".RaceData01")
    race_data = race_data_el.get_text(" ", strip=True) if race_data_el else None

    horses = []
    for row in soup.select("tr.HorseList"):
        umaban_el = row.select_one('[class^="Umaban"]')
        umaban = umaban_el.get_text(strip=True) if umaban_el else None

        name_el = row.select_one("td.HorseInfo span.HorseName a") or row.select_one("td.HorseInfo span.HorseName")
        horse_name = name_el.get_text(strip=True) if name_el else None
        horse_id = None
        if name_el and name_el.get("href"):
            m = re.search(r"/horse/(\w+)", name_el["href"])
            if m:
                horse_id = m.group(1)

        jockey_el = row.select_one("td.Jockey span.Jockey a") or row.select_one("td.Jockey")
        jockey = jockey_el.get_text(strip=True) if jockey_el else None

        weight_el = row.select_one("td.Txt_C:not(.Popular)")
        weight = weight_el.get_text(strip=True) if weight_el else None

        odds_el = row.select_one("td.Popular.Txt_R")
        odds_raw = odds_el.get_text(strip=True) if odds_el else None
        odds = None
        if odds_raw:
            try:
                odds = float(odds_raw)
            except ValueError:
                odds = None  # 発売前(オッズ未確定)や取消などの場合は非数値

        rank_el = row.select_one("td.Popular.Txt_C span")
        ninki = rank_el.get_text(strip=True) if rank_el else None

        horses.append({
            "umaban": umaban,
            "horse_id": horse_id,
            "horse_name": horse_name,
            "jockey": jockey,
            "weight_kg": weight,
            "win_odds": odds,
            "ninki_rank": ninki,
        })

    # オッズ昇順(人気順)に並べ替え。None(未確定)は末尾に。
    horses_sorted = sorted(horses, key=lambda h: (h["win_odds"] is None, h["win_odds"]))

    return {
        "race_id": race_id,
        "race_name": race_name,
        "race_data": race_data,
        "num_horses": len(horses),
        "horses_by_popularity": horses_sorted,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 netkeiba_fetch.py <race_id> [output.json]", file=sys.stderr)
        sys.exit(1)
    result = fetch_shutuba(sys.argv[1])
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
