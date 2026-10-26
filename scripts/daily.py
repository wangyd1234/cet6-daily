# -*- coding: utf-8 -*-
"""每日推送主程序：按日期取当天词包 -> 渲染 Markdown -> 归档 -> 微信推送。

用法：
  python scripts/daily.py                 # 按今天（北京时间）推送
  python scripts/daily.py --dry-run       # 只渲染，不发
  python scripts/daily.py --day 1         # 强制推第 1 天
  python scripts/daily.py --date 2026-11-01
  python scripts/daily.py --force         # 忽略“今天已推过”的检查
"""
import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import push  # noqa: E402

CST = timezone(timedelta(hours=8))
WEEK = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def load_content() -> dict:
    p = ROOT / "data" / "content.json"
    if not p.exists():
        raise SystemExit("缺少 data/content.json，请先运行 python scripts/build_content.py")
    return load_json(p)


def resolve(cfg: dict, content: dict, on_date: date):
    start = date.fromisoformat(cfg["start_date"])
    days = content["days"]
    total = len(days)
    idx = (on_date - start).days + 1
    if idx < 1:
        return None
    cycle = 1
    if idx > total:
        cycle = (idx - 1) // total + 1
        idx = (idx - 1) % total + 1
    essays = content.get("essays") or []
    essay = essays[(idx - 1) % len(essays)] if essays else None
    return {"day": days[idx - 1], "essay": essay, "no": idx, "cycle": cycle, "total": total}


def render(cfg: dict, content: dict, r: dict, on_date: date) -> tuple:
    day, essay, no, cycle, total = r["day"], r["essay"], r["no"], r["cycle"], r["total"]
    meta = content.get("meta", {})
    total_words = meta.get("total_words", 0)
    done_words = sum(1 for d in content["days"][:no] for w in d["words"] if not w.get("review"))
    prefix = cfg.get("title_prefix", "六级词汇")
    round_tag = "" if cycle == 1 else f"（第{cycle}轮复习）"
    title = f"{prefix} Day{no} · {len(day['words'])}词+好句{round_tag}"
    if len(title) > 32:
        title = title[:32]

    L = []
    L.append(f"# {prefix} · Day {no}{round_tag}")
    L.append(
        f"*{on_date.isoformat()} {WEEK[on_date.weekday()]} ｜ "
        f"今日 {len(day['words'])} 词 ｜ 累计 {done_words}/{total_words} 词 ｜ 共 {total} 天*"
    )
    if day.get("review_day"):
        new_cnt = sum(1 for w in day["words"] if not w.get("review"))
        L.append(f"\n> 🔁 **复习日**：{new_cnt} 个新词 + {len(day['words']) - new_cnt} 个回顾词，"
                 f"考纲 2345 词全部学完，今天把尾巴收掉。\n")
    L.append("")
    for i, w in enumerate(day["words"], 1):
        tag = " 🔁" if w.get("review") else ""
        head = f"**{i}. {w['word']}**{tag}"
        ipa = w.get("uk") or ""
        ipa_us = w.get("us") or ""
        if ipa and ipa_us and ipa_us != ipa:
            phone = f" 英{ipa} 美{ipa_us} "
        else:
            phone = f" {ipa} " if ipa else " "
        pos = f"*{w['pos']}* " if w.get("pos") else ""
        L.append(f"{head}{phone}{pos}{w['cn']}  ")
        phr = " ｜ ".join(f"{x['en']}（{x['zh']}）" for x in w["phr"])
        L.append(f"**搭配** {phr}  ")
        ex = w["ex"][0]
        L.append(f"**例句** {ex['en']}（{ex['zh']}）  ")
        if w.get("note"):
            L.append(f"**提示** {w['note']}  ")
        L.append("")

    if essay:
        L.append("---")
        L.append("## ✍️ 今日作文好句")
        L.append(f"> {essay['en']}")
        L.append("")
        L.append(f"**译文** {essay['zh']}  ")
        if essay.get("usage"):
            L.append(f"**用法** {essay['usage']}  ")
        if essay.get("topic"):
            L.append(f"**适用** {essay['topic']}  ")

    L.append("")
    L.append("---")
    L.append(f"*词库：六级考纲 {total_words} 词 · 每天 09:00 自动推送 · "
             f"归档 out/{on_date.isoformat()}.md*")
    return title, "\n".join(L)


def already_sent(on_date: date) -> bool:
    log = ROOT / "out" / "push_log.jsonl"
    if not log.exists():
        return False
    for line in log.read_text(encoding="utf-8").splitlines():
        try:
            if json.loads(line).get("date") == on_date.isoformat():
                return True
        except Exception:
            pass
    return False


def log_push(on_date: date, no: int, results: list) -> None:
    out = ROOT / "out"
    out.mkdir(exist_ok=True)
    rec = {"at": datetime.now(CST).isoformat(timespec="seconds"),
           "date": on_date.isoformat(), "day": no,
           "results": [{"channel": c, "ok": bool(ok), "detail": str(d)} for c, ok, d in results]}
    with (out / "push_log.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="按指定日期（北京时间 YYYY-MM-DD）")
    ap.add_argument("--day", type=int, help="强制第 N 天")
    ap.add_argument("--dry-run", action="store_true", help="只渲染不发送")
    ap.add_argument("--force", action="store_true", help="忽略已推送检查")
    ap.add_argument("--no-archive", action="store_true")
    args = ap.parse_args()

    cfg = push.load_config()
    content = load_content()
    on_date = date.fromisoformat(args.date) if args.date else datetime.now(CST).date()

    if args.day:
        total = len(content["days"])
        idx = args.day
        cycle = 1
        if idx > total:
            cycle = (idx - 1) // total + 1
            idx = (idx - 1) % total + 1
        essays = content.get("essays") or []
        r = {"day": content["days"][idx - 1],
             "essay": essays[(idx - 1) % len(essays)] if essays else None,
             "no": idx, "cycle": cycle, "total": total}
    else:
        r = resolve(cfg, content, on_date)
        if r is None:
            print(f"[skip] {on_date} 早于开学日 {cfg['start_date']}，不推送。")
            return 0

    title, md = render(cfg, content, r, on_date)

    archive = ROOT / cfg.get("archive_dir", "out")
    archive.mkdir(exist_ok=True)
    if not args.no_archive:
        (archive / f"{on_date.isoformat()}.md").write_text(f"# {title}\n\n{md}\n", encoding="utf-8")

    if args.dry_run:
        print(md)
        return 0

    if not args.force and already_sent(on_date):
        print(f"[skip] {on_date} 已推送过（--force 可重推）。")
        return 0

    results = push.send(title, md, cfg)
    log_push(on_date, r["no"], results)
    ok = any(ok for _, ok, _ in results)
    for ch, ch_ok, detail in results:
        print(("OK  " if ch_ok else "FAIL"), ch, detail)
    print(f"title={title} chars={len(md)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
