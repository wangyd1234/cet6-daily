import json, re, sys, os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load(day):
    src = os.path.join(BASE, "data", "days", "day_%03d.json" % day)
    out = os.path.join(BASE, "data", "authored", "day_%03d.json" % day)
    with open(src, encoding="utf-8") as f:
        s = json.load(f)
    with open(out, encoding="utf-8") as f:
        a = json.load(f)
    return s, a

def check(day):
    errs = []
    src, out = load(day)
    if out.get("day") != day:
        errs.append("day mismatch: %r" % out.get("day"))
    sw = src["words"]
    ow = out.get("words")
    if not isinstance(ow, list):
        errs.append("words not a list")
        return errs
    if len(ow) != 30 or len(ow) != len(sw):
        errs.append("word count %d (input %d)" % (len(ow), len(sw)))
    for i, (s, o) in enumerate(zip(sw, ow)):
        tag = "#%d %s" % (i + 1, s["word"])
        if o.get("word") != s["word"]:
            errs.append("%s: order mismatch -> %r" % (tag, o.get("word")))
        phr = o.get("phr")
        if not isinstance(phr, list) or len(phr) != 2:
            errs.append("%s: phr count %r" % (tag, len(phr) if isinstance(phr, list) else phr))
            phr = phr if isinstance(phr, list) else []
        seen = set()
        for p in phr:
            if not isinstance(p, dict) or not p.get("en") or not p.get("zh"):
                errs.append("%s: bad phr entry %r" % (tag, p))
                continue
            stem = s["word"].lower()
            if stem not in p["en"].lower() and p["en"].lower() not in ("",):
                # allow common inflections: strip trailing e / y
                alt = stem[:-1] if stem.endswith("e") else None
                ok = stem in p["en"].lower() or (alt and alt in p["en"].lower())
                if not ok:
                    errs.append("%s: phr missing word: %r" % (tag, p["en"]))
            if p["en"].lower() in seen:
                errs.append("%s: duplicate phr %r" % (tag, p["en"]))
            seen.add(p["en"].lower())
            if len(p["zh"]) > 14:
                errs.append("%s: phr zh too long (%d): %r" % (tag, len(p["zh"]), p["zh"]))
            words = re.findall(r"[A-Za-z']+", p["en"])
            if len(words) < 2:
                errs.append("%s: phr too short: %r" % (tag, p["en"]))
            if words and words[0].lower() in ("the", "a", "an") and len(words) <= 2:
                errs.append("%s: phr is just article+word: %r" % (tag, p["en"]))
        ex = o.get("ex")
        if not isinstance(ex, list) or len(ex) != 1:
            errs.append("%s: ex count %r" % (tag, len(ex) if isinstance(ex, list) else ex))
            ex = ex if isinstance(ex, list) else []
        for e in ex:
            if not isinstance(e, dict) or not e.get("en") or not e.get("zh"):
                errs.append("%s: bad ex entry %r" % (tag, e))
                continue
            if s["word"].lower() not in e["en"].lower():
                # tolerate inflections where the stem keeps its full spelling
                errs.append("%s: example missing word: %r" % (tag, e["en"]))
            n = len(re.findall(r"[A-Za-z']+", e["en"]))
            if not (8 <= n <= 20):
                errs.append("%s: example word count %d: %r" % (tag, n, e["en"]))
            if len(e["zh"]) > 30:
                errs.append("%s: ex zh too long (%d): %r" % (tag, len(e["zh"]), e["zh"]))
        note = o.get("note")
        if not isinstance(note, str) or not note.strip():
            errs.append("%s: note missing" % tag)
        elif len(note) > 45:
            errs.append("%s: note too long (%d): %r" % (tag, len(note), note))
        extra = set(o.keys()) - {"word", "phr", "ex", "note"}
        if extra:
            errs.append("%s: extra keys %r" % (tag, sorted(extra)))
    # duplicate examples within file
    exs = [w["ex"][0]["en"].lower() for w in ow if isinstance(w.get("ex"), list) and w.get("ex")]
    if len(exs) != len(set(exs)):
        errs.append("duplicate example sentences in file")
    return errs

if __name__ == "__main__":
    days = [int(x) for x in sys.argv[1:]] or [6, 7, 8]
    bad = False
    for d in days:
        try:
            errs = check(d)
        except Exception as exc:
            print("day_%03d LOAD ERROR: %s" % (d, exc))
            bad = True
            continue
        if errs:
            bad = True
            print("day_%03d FAIL (%d issues)" % (d, len(errs)))
            for e in errs:
                print("  -", e)
        else:
            print("day_%03d OK words=30 phr=2 ex=1 note=1" % d)
    sys.exit(1 if bad else 0)
