"""
netkeiba(JRA race.netkeiba.com / 地方競馬 nar.netkeiba.com、race_idの場コードで自動判別)
のレース結果・払戻ページから、着順と各券種の払戻金を生HTMLから直接パースして取得するツール。

使い方:
    python3 tools/netkeiba_result.py <race_id> [output.json]
    例: python3 tools/netkeiba_result.py 202647042808

出力の payouts には、複勝・ワイドのように1レースで複数組の払戻が
出る券種も、馬番の組み合わせ・払戻金・的中時人気をペアで格納する。
"""
import sys
import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "ja,en;q=0.8",
}

BET_TYPE_CLASS_TO_NAME = {
    "Tansho": "単勝",
    "Fukusho": "複勝",
    "Umaren": "馬連",
    "Wide": "ワイド",
    "Umatan": "馬単",
    "Fuku3": "3連複",
    "Tan3": "3連単",
}


def _text(el):
    return el.get_text(strip=True) if el else None


def _domain_for(race_id: str) -> str:
    # race_id の場コード(5-6桁目)が01-10ならJRA(race.netkeiba.com)、
    # それ以外は地方競馬(nar.netkeiba.com)。
    track_code = int(race_id[4:6])
    return "race.netkeiba.com" if 1 <= track_code <= 10 else "nar.netkeiba.com"


def fetch_result(race_id: str) -> dict:
    url = f"https://{_domain_for(race_id)}/race/result.html?race_id={race_id}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    r.encoding = r.apparent_encoding or "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    race_name_el = soup.select_one(".RaceName")
    race_name = _text(race_name_el)
    race_data_el = soup.select_one(".RaceData01")
    race_data = race_data_el.get_text(" ", strip=True) if race_data_el else None

    # 未確定(レース前・結果未反映)の場合、着順テーブルが存在しない
    result_table = soup.select_one("table#All_Result_Table") or soup.select_one("table.ResultRefund")
    finishers = []
    if result_table:
        for row in result_table.select("tbody > tr"):
            nums = row.select("td.Num")
            times = row.select("td.Time")
            waku = _text(nums[0]) if len(nums) > 0 else None
            umaban = _text(nums[1]) if len(nums) > 1 else None
            rank = _text(row.select_one("td.Result_Num div.Rank"))
            horse_name = _text(row.select_one("td.Horse_Info span.Horse_Name a"))
            jockey = _text(row.select_one("td.Jockey a"))
            finish_time = _text(times[0]) if len(times) > 0 else None
            chakusa = _text(times[1]) if len(times) > 1 else None
            agari_3f = _text(times[2]) if len(times) > 2 else None
            pre_race_ninki = _text(row.select_one("span.OddsPeople"))
            win_odds_raw = _text(row.select_one("span.Odds_Ninki"))
            win_odds = None
            if win_odds_raw:
                try:
                    win_odds = float(win_odds_raw)
                except ValueError:
                    win_odds = None
            body_weight = _text(row.select_one("td.Weight"))

            if not umaban and not horse_name:
                continue  # 空行スキップ

            finishers.append({
                "rank": rank,
                "waku": waku,
                "umaban": umaban,
                "horse_name": horse_name,
                "jockey": jockey,
                "finish_time": finish_time,
                "chakusa": chakusa,
                "agari_3f": agari_3f,
                "pre_race_ninki": pre_race_ninki,
                "win_odds": win_odds,
                "body_weight": body_weight,
            })

    payouts = {}
    for tr in soup.select("table.Payout_Detail_Table tr"):
        bet_class = next((c for c in tr.get("class", []) if c in BET_TYPE_CLASS_TO_NAME), None)
        if not bet_class:
            continue
        bet_name = BET_TYPE_CLASS_TO_NAME[bet_class]

        payout_spans = tr.select("td.Payout span")
        ninki_spans = tr.select("td.Ninki span")
        payout_amounts = []
        for sp in payout_spans:
            # 複数行は<br/>区切りなので個別のテキストに分解
            html = sp.decode_contents()
            parts = re.split(r"<br\s*/?>", html)
            for p in parts:
                p_text = BeautifulSoup(p, "html.parser").get_text(strip=True)
                if p_text:
                    m = re.search(r"([\d,]+)円", p_text)
                    payout_amounts.append(int(m.group(1).replace(",", "")) if m else None)

        ninki_list = []
        for sp in ninki_spans:
            html = sp.decode_contents()
            parts = re.split(r"<br\s*/?>", html)
            for p in parts:
                p_text = BeautifulSoup(p, "html.parser").get_text(strip=True)
                if p_text:
                    ninki_list.append(p_text)

        # 組み合わせ: 単勝/複勝は<div><span>N</span></div>の並び(1頭ずつ独立)
        # 馬連/ワイド/馬単/3連複/3連単は<ul><li><span>N</span></li>...</ul>が1組
        combos = []
        uls = tr.select("td.Result ul")
        if uls:
            for ul in uls:
                nums = [_text(li.select_one("span")) for li in ul.select("li")]
                nums = [n for n in nums if n]
                if nums:
                    combos.append(nums)
        else:
            divs = tr.select("td.Result div")
            nums = [_text(d.select_one("span")) for d in divs]
            nums = [n for n in nums if n]
            if bet_name == "複勝":
                combos = [[n] for n in nums]
            elif nums:
                combos = [[n] for n in nums]

        entries = []
        for i, combo in enumerate(combos):
            entries.append({
                "combo_umaban": combo,
                "payout_yen": payout_amounts[i] if i < len(payout_amounts) else None,
                "ninki": ninki_list[i] if i < len(ninki_list) else None,
            })
        payouts[bet_name] = entries

    return {
        "race_id": race_id,
        "race_name": race_name,
        "race_data": race_data,
        "is_finalized": bool(finishers),
        "finishers": finishers,
        "payouts": payouts,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: python3 netkeiba_result.py <race_id> [output.json]", file=sys.stderr)
        sys.exit(1)
    result = fetch_result(sys.argv[1])
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as f:
            f.write(text)
    else:
        sys.stdout.buffer.write(text.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
