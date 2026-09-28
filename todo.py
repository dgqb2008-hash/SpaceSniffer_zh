# -*- coding: utf-8 -*-
"""列出仍待翻译的"唯一英文原文"，便于批量补译。"""
import json
import re
from collections import Counter

new = json.load(open("all_new.json", encoding="utf-8"))
zh = json.load(open("zh_all.json", encoding="utf-8"))

SKIP_PROP = {"Font.Name"}
c = Counter()
for form, items in new.items():
    for k, v in items.items():
        if zh.get(form, {}).get(k):
            continue
        if k.split("/")[-1] in SKIP_PROP:
            continue
        if not v or v.startswith("#"):
            continue
        if re.fullmatch(r"<%.+%>", v):
            continue
        if not re.search("[A-Za-z]{2}", v):
            continue
        c[v] += 1

lines = ["# 共 %d 条唯一待译文本（括号内为出现次数）" % len(c)]
for v, n in sorted(c.items(), key=lambda x: (-x[1], x[0])):
    lines.append("%d\t%s" % (n, v))
open("todo.txt", "w", encoding="utf-8").write("\n".join(lines))
print("唯一待译条目:", len(c))
print("\n".join(lines[:80]))
