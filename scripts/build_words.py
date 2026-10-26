# -*- coding: utf-8 -*-
"""把 CET6_T.json 原始词库清洗成 words.json（每日排程的基础数据）。"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "CET6.json"
OUT = ROOT / "data" / "words.json"
DAYS = ROOT / "data" / "days"
PER_DAY = 30

POS_MAP = {
    "n.": "n.", "v.": "v.", "vt.": "vt.", "vi.": "vi.", "adj.": "adj.",
    "adv.": "adv.", "prep.": "prep.", "conj.": "conj.", "pron.": "pron.",
    "num.": "num.", "art.": "art.", "int.": "int.", "aux.": "aux.",
    "a.": "adj.", "ad.": "adv.",
}

# 原始词库里没标词性的 39 个词，人工补齐
POS_OVERRIDE = {
    "reproach": "vt.,n.", "reform": "v.,n.", "tow": "vt.,n.", "crawl": "vi.,n.",
    "gleam": "vi.,n.", "swap": "vt.,n.", "chase": "vt.,n.", "attack": "vt.,n.",
    "murmur": "v.,n.", "sacrifice": "vt.,n.", "boycott": "vt.,n.", "mutter": "v.,n.",
    "howl": "vi.,n.", "stab": "vt.,n.", "shrug": "v.,n.", "auction": "n.,vt.",
    "disgust": "vt.,n.", "nurture": "vt.,n.", "command": "vt.,n.", "blush": "vi.,n.",
    "consent": "n.,vi.", "exchange": "vt.,n.", "release": "vt.,n.", "defeat": "vt.,n.",
    "yell": "vi.,n.", "endeavor": "n.,vi.", "collapse": "vi.,n.", "debate": "n.,v.",
    "display": "vt.,n.", "jog": "vi.,n.", "neglect": "vt.,n.", "rape": "vt.,n.",
    "plunge": "vi.,n.", "stroll": "vi.,n.", "slaughter": "vt.,n.", "cycle": "n.,vi.",
    "veto": "vt.,n.", "gaze": "vi.,n.", "retort": "v.,n.",
}


def tidy_ipa(s: str) -> str:
    if not s:
        return ""
    s = s.strip()
    s = s.replace("'", "ˈ").replace("ˌ", "ˌ")
    s = s.replace("’", "ˈ")
    s = s.strip("/[] ")
    s = re.sub(r"\s+", "", s)
    return f"/{s}/" if s else ""


def tidy_cn(trans_list):
    """把 ['取消， 撤销， 删去 (vt.)'] 拆成 (词性, '取消；撤销；删去')"""
    pos_set, senses = [], []
    for t in trans_list or []:
        t = (t or "").strip()
        if not t:
            continue
        for m in re.findall(r"\(([a-zA-Z.\s]+)\)", t):
            for p in re.split(r"[/,、\s]+", m):
                p = p.strip().lower()
                p = POS_MAP.get(p, p)
                if p and p not in pos_set:
                    pos_set.append(p)
        body = re.sub(r"\([^)]*\)", "", t)
        body = re.sub(r"[，,]\s*", "；", body)
        body = re.sub(r"；+", "；", body)
        body = re.sub(r"；\s+", "；", body).strip("； ")
        body = body.replace("  ", " ")
        if body:
            senses.append(body)
    cn = "；".join(dict.fromkeys(senses))
    return ",".join(pos_set), cn


def main():
    raw = json.loads(RAW.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("wordList", [])
    words, seen = [], set()
    for item in raw:
        name = (item.get("name") or "").strip()
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        uk = tidy_ipa(item.get("ukphone") or item.get("usphone") or "")
        us = tidy_ipa(item.get("usphone") or "")
        pos, cn = tidy_cn(item.get("trans"))
        if not cn:
            continue
        if not pos and key in POS_OVERRIDE:
            pos = POS_OVERRIDE[key]
        seen.add(key)
        words.append({
            "id": len(words) + 1,
            "word": name,
            "uk": uk,
            "us": us if us != uk else "",
            "pos": pos,
            "cn": cn,
        })

    OUT.write_text(json.dumps(words, ensure_ascii=False, indent=1), encoding="utf-8")

    DAYS.mkdir(parents=True, exist_ok=True)
    for f in DAYS.glob("day_*.json"):
        f.unlink()
    total_days = (len(words) + PER_DAY - 1) // PER_DAY
    for d in range(total_days):
        chunk = words[d * PER_DAY:(d + 1) * PER_DAY]
        pack = {"day": d + 1, "date": None, "words": chunk}
        (DAYS / f"day_{d+1:03d}.json").write_text(
            json.dumps(pack, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"words={len(words)} days={total_days} per_day={PER_DAY}")
    print("sample:", json.dumps(words[:3], ensure_ascii=False))


if __name__ == "__main__":
    main()
