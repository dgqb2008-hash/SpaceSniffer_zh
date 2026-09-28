# -*- coding: utf-8 -*-
"""批量导出 / 合并两个版本的窗体字符串。"""
import json
import os
import ss_dfm as D

FORMS = ["TFRMABOUT", "TFRMCONFIG", "TFRMCONSOLE", "TFRMEXPORT",
         "TFRMHELP", "TFRMMAIN", "TFRMSTART", "TFRMVIEW"]

CJK = "一-鿿"


def dump_side(side):
    out = {}
    for f in FORMS:
        p = os.path.join(side, f + ".bin")
        if not os.path.exists(p):
            continue
        root = D.parse(open(p, "rb").read())
        items = []
        D.walk(root, [], items)
        d = {}
        for path, v in items:
            key = "/".join(path)
            if v[0] == "str":
                d[key] = D.dec(v[1])
            elif v[0] == "utf8":
                d[key] = v[1].decode("utf-8", "replace")
            elif v[0] == "wstr":
                d[key] = v[1].decode("utf-16-le", "replace")
            elif v[0] == "ident":
                d[key] = "#" + D.dec(v[1])
        out[f] = d
    return out


if __name__ == "__main__":
    new = dump_side("res_new")
    old = dump_side("res_old")
    json.dump(new, open("all_new.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(old, open("all_old.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import re
    cjk = re.compile("[一-鿿]")
    tot = hit = 0
    for f in FORMS:
        n = new.get(f, {})
        o = old.get(f, {})
        h = sum(1 for k in n if k in o and cjk.search(o[k]))
        tot += len(n)
        hit += h
        print("%-12s 新=%-4d 可直接沿用旧版=%-4d" % (f, len(n), h))
    print("合计 %d 条，其中 %d 条可从旧版汉化直接复用" % (tot, hit))
