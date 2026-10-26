# -*- coding: utf-8 -*-
"""把词库 + 撰写好的词卡 + 作文好句 合并成运行时使用的 data/content.json，并做质量校验。

词卡按「单词」归集，因此最后一天的复习词（复用前面出现过的词）也能自动拿到内容。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYS_DIR = ROOT / "data" / "days"
AUTH_DIR = ROOT / "data" / "authored"
ESSAYS = ROOT / "data" / "essays.json"
OUT = ROOT / "data" / "content.json"

MIN_PHR, MIN_EX = 2, 1


def stem_ok(word: str, text: str) -> bool:
    """例句/短语里是否包含该单词（放宽：允许 -s/-ed/-ing/-e 省略等变形）。"""
    w = re.sub(r"[^a-z]", "", word.lower())
    t = text.lower()
    if not w:
        return True
    if w in t:
        return True
    for n in range(len(w), 2, -1):
        if w[:n] in t:
            return True
    return False


def main() -> int:
    days_src = sorted(DAYS_DIR.glob("day_*.json"))
    problems, missing, warnings, out_days = [], [], [], []

    # 1) 所有词卡按单词归集
    card_map = {}
    for p in sorted(AUTH_DIR.glob("day_*.json")):
        auth = json.loads(p.read_text(encoding="utf-8"))
        for card in auth.get("words") or []:
            w = (card.get("word") or "").strip()
            if w:
                card_map[w.lower()] = card

    # 2) 逐天拼装 + 校验
    for src in days_src:
        day = json.loads(src.read_text(encoding="utf-8"))
        if not (AUTH_DIR / src.name).exists():
            missing.append(src.name)
            continue
        merged = []
        for base in day["words"]:
            w = base["word"]
            card = card_map.get(w.lower())
            if card is None:
                problems.append(f"{src.name}/{w}: 找不到词卡")
                continue
            phr = [x for x in (card.get("phr") or []) if x.get("en") and x.get("zh")][:3]
            ex = [x for x in (card.get("ex") or []) if x.get("en") and x.get("zh")][:2]
            note = (card.get("note") or "").strip()
            if len(phr) < MIN_PHR:
                problems.append(f"{src.name}/{w}: 短语不足 {len(phr)}")
            if len(ex) < MIN_EX:
                problems.append(f"{src.name}/{w}: 例句不足 {len(ex)}")
            if not note:
                problems.append(f"{src.name}/{w}: note 为空")
            if not stem_ok(w, " ".join(x["en"] for x in ex)):
                warnings.append(f"{src.name}/{w}: 例句里没找到原词，请人工扫一眼")
            merged.append({**base, "phr": phr, "ex": ex, "note": note})
        if merged:
            item = {"day": day["day"], "words": merged}
            if day.get("review_day"):
                item["review_day"] = True
            out_days.append(item)

    essays = json.loads(ESSAYS.read_text(encoding="utf-8")) if ESSAYS.exists() else []
    total_words = sum(1 for d in out_days for w in d["words"] if not w.get("review"))
    content = {
        "meta": {
            "title": "六级考纲词汇 79 天计划",
            "total_words": total_words,
            "days": len(out_days),
            "essays": len(essays),
        },
        "days": out_days,
        "essays": essays,
    }
    OUT.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"days={len(out_days)}/{len(days_src)} 新词={total_words} essays={len(essays)}")
    print(f"content.json = {OUT.stat().st_size / 1024:.0f} KB")
    if missing:
        print(f"未撰写 {len(missing)} 天：{', '.join(missing[:8])}{' ...' if len(missing) > 8 else ''}")
    if warnings:
        print(f"提示 {len(warnings)} 条（不影响使用）：")
        for x in warnings[:10]:
            print("  -", x)
    if problems:
        print(f"发现 {len(problems)} 个问题（前 25 条）：")
        for x in problems[:25]:
            print("  -", x)
        return 1
    print("校验通过 ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
