import json, sys, os, re

BASE = os.path.dirname(os.path.abspath(__file__))

def forms(w):
    w = w.lower()
    out = {w, w + "s", w + "es", w + "ed", w + "d", w + "ing", w + "er", w + "n"}
    if w.endswith("y"):
        out |= {w[:-1] + "ies", w[:-1] + "ied"}
    if w.endswith("e"):
        out |= {w[:-1] + "ing", w[:-1] + "ed", w[:-1] + "es"}
    if w.endswith("f"):
        out |= {w[:-1] + "ves"}
    stem = w[:-1] if len(w) > 3 and w.endswith("e") else w
    for tok in []:
        pass
    return out, stem

def has_word(text, word):
    t = text.lower()
    out, stem = forms(word)
    if any(f in t for f in out):
        return True
    # tolerate inflections like deny->denied, vary->varies via prefix match on tokens
    for tok in re.findall(r"[a-z]+", t):
        if tok.startswith(stem) and len(tok) - len(stem) <= 4:
            return True
    return False

def check_day(day):
    src_p = os.path.join(BASE, "data", "days", f"day_{day}.json")
    out_p = os.path.join(BASE, "data", "authored", f"day_{day}.json")
    errs = []
    with open(src_p, encoding="utf-8") as f:
        src = json.load(f)
    with open(out_p, encoding="utf-8") as f:
        out = json.load(f)
    if out.get("day") != src.get("day") or out.get("day") != int(day):
        errs.append(f"day mismatch: {out.get('day')} vs {src.get('day')}")
    sw, ow = src["words"], out.get("words", [])
    if len(sw) != 30:
        errs.append(f"source words {len(sw)} != 30")
    if len(ow) != 30:
        errs.append(f"output words {len(ow)} != 30")
    seen_ex = set()
    for i in range(min(len(sw), len(ow))):
        s, o = sw[i], ow[i]
        tag = f"#{i+1} {s['word']}"
        if o.get("word") != s["word"]:
            errs.append(f"{tag}: word mismatch/order -> {o.get('word')}")
            continue
        phr = o.get("phr")
        if not isinstance(phr, list) or len(phr) != 2:
            errs.append(f"{tag}: phr count != 2")
            phr = phr if isinstance(phr, list) else []
        for j, p in enumerate(phr):
            if not isinstance(p, dict) or not p.get("en") or not p.get("zh"):
                errs.append(f"{tag}: phr[{j}] missing en/zh")
                continue
            if not has_word(p["en"], s["word"]):
                errs.append(f"{tag}: phr[{j}] '{p['en']}' lacks word")
            if len(p["zh"]) > 14:
                errs.append(f"{tag}: phr[{j}] zh too long ({len(p['zh'])})")
        if len(phr) == 2 and phr[0].get("en", "").strip().lower() == phr[1].get("en", "").strip().lower():
            errs.append(f"{tag}: duplicate phr")
        ex = o.get("ex")
        if not isinstance(ex, list) or len(ex) != 1:
            errs.append(f"{tag}: ex count != 1")
        else:
            e = ex[0]
            en, zh = e.get("en", ""), e.get("zh", "")
            n = len(re.findall(r"[A-Za-z][A-Za-z'\-]*", en))
            if not (8 <= n <= 20):
                errs.append(f"{tag}: ex word count {n}")
            if not has_word(en, s["word"]):
                errs.append(f"{tag}: ex lacks word -> {en}")
            if len(zh) > 30:
                errs.append(f"{tag}: ex zh too long ({len(zh)})")
            if not en.strip().endswith((".", "!", "?", '"')):
                errs.append(f"{tag}: ex not terminated")
            norm = re.sub(r"[^a-z]", "", en.lower())
            if norm in seen_ex:
                errs.append(f"{tag}: duplicate example in file")
            seen_ex.add(norm)
        note = o.get("note", "")
        if not note or not note.strip():
            errs.append(f"{tag}: note empty")
        elif len(note) > 45:
            errs.append(f"{tag}: note too long ({len(note)}): {note}")
        extra = set(o.keys()) - {"word", "phr", "ex", "note"}
        if extra:
            errs.append(f"{tag}: extra keys {extra}")
    if errs:
        print(f"FAIL day_{day}")
        for e in errs:
            print(" -", e)
        return False
    print(f"OK day_{day} words={len(ow)}")
    return True

if __name__ == "__main__":
    ok = True
    for d in sys.argv[1:]:
        ok = check_day(d) and ok
    sys.exit(0 if ok else 1)
