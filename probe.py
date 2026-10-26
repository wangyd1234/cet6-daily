import json, urllib.request
base="https://cdn.jsdelivr.net/gh/Kaiyiwing/qwerty-learner@master/public/dicts/"
files=["hongbaoshu-2026.json","xinghuoqiaoji_6.json","CET4_T.json","DanCiDeJianFa_6.json","926.json"]
for f in files:
    try:
        d=json.loads(urllib.request.urlopen(base+f,timeout=60).read().decode("utf-8"))
        if isinstance(d,dict): d=d.get("wordList",d)
        keys=set()
        n=0
        for w in d[:50]:
            if isinstance(w,dict): keys|=set(w.keys())
        ex=[w for w in d if isinstance(w,dict) and (w.get("sentences") or w.get("examples"))][:1]
        print(f, "count=",len(d), "keys=",sorted(keys))
        if ex: print("   sample:", json.dumps(ex[0],ensure_ascii=False)[:400])
    except Exception as e:
        print(f,"ERR",e)
