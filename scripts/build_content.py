# -*- coding: utf-8 -*-
"""把词库 + 撰写好的词卡 + 作文好句 合并成运行时使用的 data/content.json，并做质量校验。"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DAYS_DIR = ROOT / "data" / "days"
AUTH_DIR = ROOT / "data" / "authored"
WORDS = ROOT / "data" / "words.json"
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
    problems = []
    missing = []
    warnings = []
    out_days = []
    for src in days_src:
        day = json.loads(src.read_text(encoding="utf-8"))
        p = AUTH_DIR / src.name
        if not p.exists():
            missing.append(src.name)
            continue
        auth = json.loads(p.read_text(encoding="utf-8"))
        cards = auth.get("words") or []
        if len(cards) != len(day["words"]):
            problems.append(f"{src.name}: 词数不一致 {len(cards)} != {len(day['words'])}")
            continue
        merged = []
        for base, card in zip(day["words"], cards):
            w = base["word"]
            if (card.get("word") or "").lower() != w.lower():
                problems.append(f"{src.name}: 顺序错位 {w} -> {card.get('word')}")
                merged = None
                break
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
            out_days.append({"day": day["day"], "words": merged})

    essays = json.loads(ESSAYS.read_text(encoding="utf-8")) if ESSAYS.exists() else []
    content = {
        "meta": {
            "title": "六级考纲词汇 79 天计划",
            "total_words": sum(len(d["words"]) for d in out_days),
            "days": len(out_days),
            "essays": len(essays),
        },
        "days": out_days,
        "essays": essays,
    }
    OUT.write_text(json.dumps(content, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"days={len(out_days)}/{len(days_src)} words={content['meta']['total_words']} essays={len(essays)}")
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
