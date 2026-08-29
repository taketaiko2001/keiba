"""
netkeiba(db.netkeiba.com)の騎手・調教師 個別ページから、
通算・当年の成績（勝率・連対率・複勝率）を生HTMLから直接パースして取得するツール。

騎手・調教師どちらも中央(JRA)・地方(NAR)それぞれの成績表が別テーブルで存在する場合があるため、
騎乗(出走)回数が多い方＝主戦場のテーブルを自動選択する。

使い方:
    python3 tools/netkeiba_people.py jockey <jockey_id> [output.json]
    python3 tools/netkeiba_people.py trainer <trainer_id> [output.json]
    例: python3 tools/netkeiba_people.py jockey 05524

jockey_id / trainer_id は netkeiba_fetch.py の出馬表データの
"jockey_id" / "trainer_id" フィールドで取得できる。
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

COL_KEYS = [
    "year", "rank", "win1", "win2", "win3", "win_other",
    "mounts", "stakes_starts", "stakes_wins",
    "win_rate", "place2_rate", "place3_rate", "top_horse",
]


def _parse_int(text):
    text = text.replace(",", "").strip()
    if not text or text in ("-",):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_results_table(table):
    rows = table.select("tbody tr")
    parsed = []
    for row in rows:
        cells = [td.get_text(strip=True) for td in row.find_all(["td", "th"])]
        if len(cells) < len(COL_KEYS):
            cells += [""] * (len(COL_KEYS) - len(cells))
        record = dict(zip(COL_KEYS, cells))
        record["mounts_num"] = _parse_int(record["mounts"])
        parsed.append(record)
    return parsed


def _fetch(kind: str, person_id: str) -> dict:
    assert kind in ("jockey", "trainer")
    url = f"https://db.netkeiba.com/{kind}/{person_id}/"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    name = None
    if soup.title and soup.title.string:
        m = re.match(r"(.+?)のプロフィール", soup.title.string.strip())
        name = m.group(1) if m else soup.title.string.strip()

    tables = soup.select("table.ResultsByYears")
    best_table = None
    best_mounts = -1
    for t in tables:
        rows = _parse_results_table(t)
        if not rows:
            continue
        career_row = rows[0]  # 累計(career total)は常に先頭行
        mounts = career_row.get("mounts_num") or 0
        if mounts > best_mounts:
            best_mounts = mounts
            best_table = rows

    career = best_table[0] if best_table else None
    recent_years = best_table[1:] if best_table else []

    return {
        f"{kind}_id": person_id,
        "name": name,
        "career_totals": career,
        "recent_years": recent_years,  # 新しい年度が先頭
    }


def fetch_jockey_stats(jockey_id: str) -> dict:
    return _fetch("jockey", jockey_id)


def fetch_trainer_stats(trainer_id: str) -> dict:
    return _fetch("trainer", trainer_id)


if __name__ == "__main__":
    if len(sys.argv) < 3 or sys.argv[1] not in ("jockey", "trainer"):
        print("usage: python3 netkeiba_people.py <jockey|trainer> <id> [output.json]", file=sys.stderr)
        sys.exit(1)
    result = _fetch(sys.argv[1], sys.argv[2])
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if len(sys.argv) >= 4:
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
