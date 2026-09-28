# -*- coding: utf-8 -*-
"""生成新版 2.2.0.27 的汉化表：优先复用旧版汉化(1.3.0.2)译文。

输出:
  zh_all.json          {窗体: {路径: 中文}}   可直接修改后重复执行
  remain.txt           仍未翻译的条目(按窗体分组)，供人工/模型补译
"""
import json
import re
from collections import OrderedDict

new = json.load(open("all_new.json", encoding="utf-8"))
old = json.load(open("all_old.json", encoding="utf-8"))
CJK = re.compile("[一-鿿]")

# 人工补充/覆盖: 全局按"英文原文"匹配优先级最低，按"路径"匹配最高
MANUAL_PATH = json.load(open("manual_path.json", encoding="utf-8")) \
    if __import__("os").path.exists("manual_path.json") else {}
MANUAL_EN = json.load(open("manual_en.json", encoding="utf-8")) \
    if __import__("os").path.exists("manual_en.json") else {}

zh, src = {}, {}
en2zh = {}

# 第一轮: 同路径复用
for form, items in new.items():
    zh[form] = {}
    o = old.get(form, {})
    for k, v in items.items():
        if k in o and CJK.search(o[k]):
            zh[form][k] = o[k]
            src[form + "::" + k] = "path"
            en2zh.setdefault(v, o[k])

# 第一轮b: 字体字符集沿用旧版汉化(GB2312_CHARSET)，保证中文正常显示
for form, items in new.items():
    o = old.get(form, {})
    for k, v in items.items():
        if v == "#DEFAULT_CHARSET" and o.get(k) == "#GB2312_CHARSET":
            zh[form][k] = "#GB2312_CHARSET"
            src[form + "::" + k] = "charset"

# 第二轮: 同英文原文复用(来自第一轮建立的词典)
for form, items in new.items():
    for k, v in items.items():
        if zh[form].get(k):
            continue
        if v in en2zh:
            zh[form][k] = en2zh[v]
            src[form + "::" + k] = "value"

# 第三轮: 人工补充(路径)
for form, items in new.items():
    for k, v in MANUAL_PATH.get(form, {}).items():
        if k in items:
            zh[form][k] = v
            src[form + "::" + k] = "manual"

# 第四轮: 人工补充(英文原文)
for form, items in new.items():
    for k, v in items.items():
        if zh[form].get(k):
            continue
        if v in MANUAL_EN:
            zh[form][k] = MANUAL_EN[v]
            src[form + "::" + k] = "manual-en"

json.dump(zh, open("zh_all.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

lines = []
stat = {}
for form, items in new.items():
    done = sum(1 for k in items if zh[form].get(k))
    stat[form] = (done, len(items))
    lines.append("\n===== %s  (%d/%d) =====" % (form, done, len(items)))
    for k, v in items.items():
        if zh[form].get(k):
            continue
        if v.startswith("#") or len(v) == 0 or not re.search("[A-Za-z]", v):
            continue  # 常量/字体名/字符集等，不翻译
        lines.append("%s\t%s" % (k, v))
open("remain.txt", "w", encoding="utf-8").write("\n".join(lines))

tot = sum(a for a, b in stat.values())
ok = sum(b for a, b in stat.values())
print("已翻译 %d / %d" % (tot, ok))
for f, (a, b) in stat.items():
    print("  %-12s %3d / %-3d" % (f, a, b))
